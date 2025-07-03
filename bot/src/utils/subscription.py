import uuid
from datetime import timedelta, datetime
import redis.asyncio as redis
import logging
import aiosqlite
from src.configs.config import config
import sqlite3

# Настройка логирования
logger = logging.getLogger(__name__)
r = redis.Redis(
        host=config.redis.host,
        port=config.redis.port,
        db=config.redis.db,
        decode_responses=config.redis.decode_responses
    )


async def user_has_used_trial(user_id: int) -> bool:
    """Проверяет в SQLite, использовал ли пользователь триал."""
    async with aiosqlite.connect(config.database.path) as db:
        async with db.execute("SELECT trial_used FROM subscriptions WHERE user_id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] == 1 if result else False

async def activate_trial(user_id: int, chat_id: int) -> str | None:
    """Активирует триал, если он еще не был использован."""
    if await user_has_used_trial(user_id):
        logger.info(f"User {user_id} has already used the trial. No new trial granted.")
        return None

    token = f"trial-{user_id}"
    trial_days = config.subscription.trial_days
    await r.set(f"user:{user_id}:token", token, ex=trial_days * 86400)
    await r.set(f"token:{token}", user_id, ex=trial_days * 86400)
    await r.hset(f"user:{user_id}:info", mapping={"chat_id": str(chat_id)})
    # Сохраняем в SQLite и выставляем флаг trial_used
    end_date = datetime.now() + timedelta(days=trial_days)
    await save_subscription_to_sqlite(user_id, end_date, True, trial_used=True)
    logger.info(f"Trial activated for user_id: {user_id}")
    return token

async def activate_subscription(user_id: int, chat_id: int, subscription_type: str) -> str:
    sub_info = await r.hgetall(f"subscription:{subscription_type}")
    if not sub_info:
        logger.error(f"Subscription type {subscription_type} not found")
        raise ValueError(f"Subscription type {subscription_type} not found")
    duration_days = int(sub_info["duration_days"])
    token = str(uuid.uuid4())
    await r.set(f"user:{user_id}:token", token, ex=duration_days * 86400)
    await r.set(f"token:{token}", user_id, ex=duration_days * 86400)
    await r.hset(f"user:{user_id}:info", mapping={"chat_id": str(chat_id), "subscription_type": subscription_type})
    # Сохраняем в SQLite
    end_date = datetime.now() + timedelta(days=duration_days)
    await save_subscription_to_sqlite(user_id, end_date, True, trial_used=await user_has_used_trial(user_id), auto_renewal=True)
    logger.info(f"Subscription {subscription_type} activated for user_id: {user_id}")
    return token

async def renew_subscription(user_id: int, chat_id: int, subscription_type: str) -> str:
    sub_info = await r.hgetall(f"subscription:{subscription_type}")
    if not sub_info:
        logger.error(f"Subscription type {subscription_type} not found")
        raise ValueError(f"Subscription type {subscription_type} not found")

    duration_days = int(sub_info["duration_days"])
    token = await r.get(f"user:{user_id}:token")
    if not token:
        # Если токена нет, но пользователь пытается продлить, возможно, это покупка после истечения.
        # В этом случае, ведем себя как при активации новой подписки.
        return await activate_subscription(user_id, chat_id, subscription_type)

    # Получаем текущую дату окончания подписки
    current_sub = await get_user_subscription(user_id)
    # Если по какой-то причине подписки нет в БД, считаем от сегодня
    current_end_date = datetime.now()
    if current_sub and current_sub.get('end_date'):
        current_end_date = datetime.strptime(current_sub.get('end_date'), "%Y-%m-%d")

    # База для расчета - дата окончания текущей подписки или сегодня, если она уже истекла
    base_date = max(datetime.now(), current_end_date)
    new_end_date = base_date + timedelta(days=duration_days)

    # Обновляем TTL в Redis
    new_ttl_seconds = (new_end_date - datetime.now()).total_seconds()

    await r.set(f"user:{user_id}:token", token, ex=int(new_ttl_seconds))
    await r.set(f"token:{token}", user_id, ex=int(new_ttl_seconds))
    await r.hset(f"user:{user_id}:info", mapping={"chat_id": str(chat_id), "subscription_type": subscription_type})

    # Сохраняем новую дату в SQLite
    await save_subscription_to_sqlite(user_id, new_end_date, True, trial_used=True, auto_renewal=True)

    logger.info(f"Subscription {subscription_type} renewed for user_id: {user_id}. New end date: {new_end_date.strftime('%Y-%m-%d')}")
    return token

async def get_token(user_id: int) -> str | None:
    token = await r.get(f"user:{user_id}:token")
    logger.debug(f"Retrieved token for user_id: {user_id}")
    return token

async def is_token_valid(token: str) -> bool:
    exists = await r.exists(f"token:{token}") == 1
    logger.debug(f"Token {token} validity check: {exists}")
    return exists

async def create_promo(code: str, discount: int, days: int = 30):
    await r.set(f"promo:{code}", discount, ex=days * 86400)
    logger.info(f"Promo code {code} created with {discount}% discount")

async def get_promo_discount(code: str) -> int | None:
    value = await r.get(f"promo:{code}")
    logger.debug(f"Promo code {code} discount: {value}")
    return int(value) if value else None

async def get_users_with_expiring_tokens() -> list[dict]:
    users = []
    cursor = "0"
    while cursor != 0:
        cursor, keys = await r.scan(cursor=cursor, match="user:*:token")
        for key in keys:
            ttl = await r.ttl(key)
            if 0 < ttl <= 86400:
                user_id = key.split(":")[1]
                chat_id = await r.hget(f"user:{user_id}:info", "chat_id")
                if chat_id:
                    users.append({"user_id": user_id, "chat_id": int(chat_id)})
    logger.info(f"Found {len(users)} users with expiring tokens")
    return users

async def can_use_promo(user_id: int) -> bool:
    last_used = await r.get(f"promo_cooldown:{user_id}")
    if last_used:
        last_used_time = float(last_used)
        if (await r.time())[0] - last_used_time < 300:
            logger.debug(f"Promo cooldown active for user_id: {user_id}")
            return False
    return True

async def set_promo_cooldown(user_id: int):
    current_time = (await r.time())[0]
    await r.set(f"promo_cooldown:{user_id}", current_time, ex=300)
    logger.debug(f"Promo cooldown set for user_id: {user_id}")

async def create_subscription_type(sub_type: str, duration_days: int, price: int):
    await r.hset(f"subscription:{sub_type}", mapping={
        "duration_days": str(duration_days),
        "price": str(price)
    })
    logger.info(f"Subscription type {sub_type} created: {duration_days} days, {price} ⭐")

async def delete_subscription_type(sub_type: str) -> bool:
    deleted = await r.delete(f"subscription:{sub_type}") == 1
    logger.info(f"Subscription type {sub_type} deleted: {deleted}")
    return deleted

async def get_subscription_types() -> list[dict]:
    cursor = "0"
    subs = []
    while cursor != 0:
        cursor, keys = await r.scan(cursor=cursor, match="subscription:*")
        for key in keys:
            sub_info = await r.hgetall(key)
            subs.append({
                "type": key.split(":")[1],
                "duration_days": int(sub_info["duration_days"]),
                "price": int(sub_info["price"])
            })
    logger.debug(f"Retrieved {len(subs)} subscription types")
    return subs

async def get_subscription_price(sub_type: str) -> int | None:
    price = await r.hget(f"subscription:{sub_type}", "price")
    logger.debug(f"Subscription {sub_type} price: {price}")
    return int(price) if price else None

async def get_active_subscriptions() -> list[dict]:
    cursor = "0"
    active_subs = []
    while cursor != 0:
        cursor, keys = await r.scan(cursor=cursor, match="user:*:token")
        for key in keys:
            user_id = key.split(":")[1]
            token = await r.get(key)
            ttl = await r.ttl(key)
            sub_type = await r.hget(f"user:{user_id}:info", "subscription_type") or "trial"
            sub_info = await r.hgetall(f"subscription:{sub_type}") if sub_type != "trial" else {"duration_days": 14}
            active_subs.append({
                "user_id": user_id,
                "token": token,
                "subscription_type": sub_type,
                "days_left": ttl // 86400,
                "duration_days": int(sub_info["duration_days"])
            })
    logger.info(f"Retrieved {len(active_subs)} active subscriptions")
    return active_subs

async def get_user_subscription(user_id: int) -> dict | None:
    try:
        async with aiosqlite.connect(config.database.path) as db:
            async with db.execute("SELECT end_date, active, trial_used, auto_renewal, lang, subtype FROM subscriptions WHERE user_id = ?", (user_id,)) as cursor:
                sub_info = await cursor.fetchone()
    except (aiosqlite.OperationalError, Exception) as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        return {"error": "db_unavailable"}

    if not sub_info:
        logger.debug(f"No subscription record in SQLite for user_id: {user_id}")
        return None

    end_date_str, active, trial_used, auto_renewal, lang, subtype = sub_info
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S")

    # Если подписка неактивна и триал не использован, то это некорректное состояние,
    # но на всякий случай возвращаем None, чтобы /start мог сработать
    if not active and not trial_used:
         return None

    days_left = (end_date - datetime.now()).days

    token = await r.get(f"user:{user_id}:token")
    sub_type = await r.hget(f"user:{user_id}:info", "subscription_type") or "trial"

    logger.debug(f"Retrieved subscription for user_id: {user_id}")
    return {
        "token": token,
        "subscription_type": sub_type,
        "days_left": days_left,
        "end_date": end_date.strftime("%Y-%m-%d"),
        "active": active and end_date > datetime.now(),
        "trial_used": trial_used,
        "auto_renewal": auto_renewal,
        "lang": lang,
        "subtype": subtype
    }

async def disable_auto_renewal(user_id: int) -> bool:
    """Отключает автопродление подписки для пользователя."""
    try:
        async with aiosqlite.connect(config.database.path) as db:
            await db.execute(
                "UPDATE subscriptions SET auto_renewal = 0 WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()
            logger.info(f"Auto-renewal disabled for user_id: {user_id}")
            return True
    except Exception as e:
        logger.error(f"Failed to disable auto-renewal for user_id {user_id}: {e}")
        return False

async def save_subscription_to_sqlite(user_id: int, end_date: datetime, active: bool, trial_used: bool = False, auto_renewal: bool = True, lang: str = "ru", subtype: str = "trial"):
    async with aiosqlite.connect(config.database.path) as db:
        await db.execute(
            """
            INSERT INTO subscriptions (user_id, end_date, active, trial_used, auto_renewal, lang, subtype)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                end_date=excluded.end_date,
                active=excluded.active,
                trial_used=subscriptions.trial_used OR excluded.trial_used,
                auto_renewal=excluded.auto_renewal,
                lang=excluded.lang,
                subtype=excluded.subtype
            """,
            (user_id, end_date.strftime("%Y-%m-%d %H:%M:%S"), int(active), int(trial_used), int(auto_renewal), lang, subtype)
        )
        await db.commit()
