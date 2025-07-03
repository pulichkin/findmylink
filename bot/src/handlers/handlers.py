import json
import logging
import aiohttp
import os
from telegram import Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, PreCheckoutQueryHandler, MessageHandler, filters, ContextTypes
from src.utils.subscription import (
    activate_trial, create_promo, get_promo_discount, get_users_with_expiring_tokens,
    can_use_promo, set_promo_cooldown, create_subscription_type, get_subscription_types, get_subscription_price,
    get_active_subscriptions, delete_subscription_type, get_user_subscription, disable_auto_renewal,
)
from src.configs.config import config
from src.utils.backup import backup_manager
import aiosqlite
from datetime import datetime, timedelta
import redis.asyncio as redis

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
redis_client = redis.Redis(
        host=config.redis.host,
        port=config.redis.port,
        db=config.redis.db,
        decode_responses=config.redis.decode_responses
    )


def load_translations(lang: str) -> dict:
    try:
        with open(f"src/locales/{lang}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.warning(f"Failed to load translations for {lang}, falling back to English")
        return load_translations("en")

def get_translation(update: Update, key: str, **kwargs) -> str:
    lang = update.effective_user.language_code or "en"
    translations = load_translations("ru" if lang.startswith("ru") else "en")
    keys = key.split(".")
    value = translations
    for k in keys:
        if not isinstance(value, dict):
            logger.warning(f"Invalid translation key path: {key}")
            return key
        value = value.get(k)
        if value is None:
            logger.warning(f"Translation key not found: {key}")
            return key

    if isinstance(value, str):
        return value.format(**kwargs)

    logger.warning(f"Translation key '{key}' does not point to a string.")
    return key

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} started bot")

    # Показываем приветственное сообщение с помощью
    await help_command(update, context)

async def get_trial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested trial")

    # Проверяем, есть ли у пользователя какая-либо запись о подписке или триале
    subscription = await get_user_subscription(user_id)

    if subscription and subscription.get('active'):
        # Если есть активная подписка, просто выводим токен
        await update.message.reply_text(
            get_translation(update, "start.already_subscribed", token=subscription['token']),
            parse_mode="Markdown"
        )
    elif subscription and subscription.get('trial_used'):
        # Если триал уже был использован и подписка неактивна
        await update.message.reply_text(
            get_translation(update, "trial.already_used"),
            parse_mode="Markdown"
        )
    else:
        # Если записей нет или триал не использован - выдаем триал
        token = await activate_trial(user_id, update.effective_chat.id)
        if token:
            logger.info(f"Trial activated for user {user_id}")
            await update.message.reply_text(
                get_translation(update, "trial.activated", token=token),
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                get_translation(update, "trial.already_used"),
                parse_mode="Markdown"
            )

async def _send_subscription_invoice(
    bot,
    chat_id: int,
    user_id: int,
    sub_type: str,
    promo_code: str | None,
    update_for_translation: Update,
):
    """Core logic to create and send a subscription invoice."""
    price = await get_subscription_price(sub_type)
    if price is None:
        logger.warning(f"Invalid subscription type {sub_type} for user {user_id}")
        await bot.send_message(
            chat_id, get_translation(update_for_translation, "buy.invalid_type")
        )
        return

    discount = 0
    if promo_code:
        if not await can_use_promo(user_id):
            logger.warning(f"Promo cooldown for user {user_id}")
            await bot.send_message(
                chat_id, get_translation(update_for_translation, "buy.cooldown")
            )
            return
        discount = await get_promo_discount(promo_code) or 0
        await set_promo_cooldown(user_id)
        if discount:
            logger.info(f"Promo applied for user {user_id}, code: {promo_code}")
        else:
            logger.warning(f"Invalid promo code {promo_code} for user {user_id}")
            await bot.send_message(
                chat_id, get_translation(update_for_translation, "buy.invalid_promo")
            )
            return

    final_price = price * (100 - discount) // 100
    user_sub = await get_user_subscription(user_id)
    is_renewal = user_sub and user_sub.get('active', False) and user_sub.get('auto_renewal', True)

    invoice_title = get_translation(
        update_for_translation,
        "renew.invoice_title" if is_renewal else "buy.invoice_title",
    )
    invoice_description = get_translation(
        update_for_translation,
        "renew.invoice_description" if is_renewal else "buy.invoice_description",
    )
    payload = f"findmylink_pro_{sub_type}_{'renew' if is_renewal else 'new'}"

    await bot.send_invoice(
        chat_id=chat_id,
        title=invoice_title,
        description=invoice_description,
        payload=payload,
        provider_token=config.telegram.payment_provider_token,
        currency="XTR",
        prices=[LabeledPrice(invoice_title, final_price)],
    )
    logger.info(f"Invoice sent to user {user_id} for {sub_type}")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    args = context.args
    logger.info(f"User {user_id} initiated subscription with args: {args}")
    if not args:
        await update.message.reply_text(get_translation(update, "buy.select_type"))
        return

    sub_type = args[0].lower()
    promo_code = args[1] if len(args) > 1 else None

    await _send_subscription_invoice(
        bot=context.bot,
        chat_id=chat_id,
        user_id=user_id,
        sub_type=sub_type,
        promo_code=promo_code,
        update_for_translation=update,
    )

async def pre_checkout_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Pre-checkout query for user {update.pre_checkout_query.from_user.id}")
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    payload = update.message.successful_payment.invoice_payload
    sub_type = payload.split("_")[2]
    is_renewal = payload.endswith("_renew")
    price = update.message.successful_payment.total_amount
    logger.info(f"Successful payment by user {user_id} for {sub_type} (renewal: {is_renewal}, price: {price})")

    try:
        # Активируем подписку через API
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{config.api.url}/api/v1/subscription/activate",
                json={
                    "subscription_type": sub_type,
                    "price": price,
                    "is_renewal": is_renewal
                },
                headers={"Authorization": f"Bearer {context.bot_data.get('api_token')}"}
            ) as response:
                if not response.ok:
                    error_text = await response.text()
                    logger.error(f"Failed to activate subscription: {error_text}")
                    await update.message.reply_text(
                        get_translation(update, "payment.error"),
                        parse_mode="Markdown"
                    )
                    return

                data = await response.json()
                logger.info(f"Subscription activated: {data}")

                # Отправляем сообщение пользователю
                message_key = "buy.renew_success" if is_renewal else "payment_success"
                await update.message.reply_text(
                    get_translation(update, message_key),
                    parse_mode="Markdown"
                )

    except Exception as e:
        logger.error(f"Error processing payment for user {user_id}: {e}")
        await update.message.reply_text(
            get_translation(update, "payment.error"),
            parse_mode="Markdown"
        )

async def apply_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    promo_code = context.args[0] if context.args else None
    logger.info(f"User {user_id} attempting to apply promo code: {promo_code}")

    # --- Защита от подбора промокода (Redis) ---
    try:
        key = f"promo_attempts:{user_id}"
        attempts = await redis_client.get(key)
        if attempts and int(attempts) >= config.rate_limit.max_attempts:
            await update.message.reply_text(
                f"Слишком много попыток. Попробуйте через {config.rate_limit.block_minutes} минут. / Too many attempts. Try again in {config.rate_limit.block_minutes} minutes."
            )
            return
        # Увеличиваем счетчик и ставим TTL
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, config.rate_limit.block_minutes * 60)
        await pipe.execute()
    except Exception as e:
        logger.warning(f"Redis unavailable or error: {e}. Falling back to SQLite for rate limit.")
        # --- Защита от подбора промокода (SQLite) ---
        import datetime
        now = datetime.datetime.now()
        async with aiosqlite.connect(config.database.path) as db:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS promo_attempts (user_id INTEGER, attempt_time DATETIME)"
            )
            await db.execute(
                "DELETE FROM promo_attempts WHERE attempt_time < ?",
                ((now - datetime.timedelta(minutes=config.rate_limit.block_minutes)).strftime('%Y-%m-%d %H:%M:%S'),)
            )
            await db.commit()
            async with db.execute(
                "SELECT COUNT(*) FROM promo_attempts WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                attempts = row[0] if row else 0
            if attempts >= config.rate_limit.max_attempts:
                await update.message.reply_text(
                    f"Слишком много попыток. Попробуйте через {config.rate_limit.block_minutes} минут. / Too many attempts. Try again in {config.rate_limit.block_minutes} minutes."
                )
                return
            await db.execute(
                "INSERT INTO promo_attempts (user_id, attempt_time) VALUES (?, ?)",
                (user_id, now.strftime('%Y-%m-%d %H:%M:%S'))
            )
            await db.commit()
    # --- Дальнейшая логика применения промокода (как была) ---
    if not promo_code:
        await update.message.reply_text("Укажите промокод: /promo <код>")
        return
    try:
        async with aiosqlite.connect(config.database.path) as db:
            async with db.execute("SELECT discount, expiration_date, used FROM promo_codes WHERE code = ?", (promo_code,)) as cursor:
                promo = await cursor.fetchone()
            if not promo:
                logger.warning(f"Promo code {promo_code} not found for user {user_id}")
                await update.message.reply_text("Промокод не найден")
                return
            discount, expiration_date_str, used = promo
            from datetime import datetime
            expiration_date = datetime.strptime(expiration_date_str, "%Y-%m-%d %H:%M:%S")
            if used:
                await update.message.reply_text("Этот промокод уже был использован")
                return
            if expiration_date < datetime.now():
                await update.message.reply_text("Срок действия промокода истёк")
                return
            await db.execute("UPDATE promo_codes SET used = 1 WHERE code = ?", (promo_code,))
            await db.commit()
            await update.message.reply_text(f"Промокод применён! Скидка {discount}%")
            logger.info(f"User {user_id} successfully applied promo code {promo_code} with discount {discount}%")
    except Exception as e:
        logger.error(f"Error applying promo code {promo_code} for user {user_id}: {e}")
        await update.message.reply_text("Произошла ошибка при применении промокода. Попробуйте позже.")

async def check_subscriptions(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Checking subscriptions for expiration")
    try:
        async with aiosqlite.connect(config.database.path) as db:
            async with db.execute("SELECT user_id, end_date FROM subscriptions WHERE active = ?", (True,)) as cursor:
                subs = await cursor.fetchall()

            for user_id, end_date in subs:
                end = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
                if end < datetime.now() + timedelta(days=3):
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="Ваша подписка скоро истекает! Оформите продление с помощью /subscribe",
                    )
                    logger.info(f"Sent expiration notification to user {user_id}")
    except Exception as e:
        logger.error(f"Error checking subscriptions: {e}")

async def create_promo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.telegram.admin_ids:
        logger.warning(f"Unauthorized access to /create_promo by user {update.effective_user.id}")
        await update.message.reply_text(get_translation(update, "create_promo.no_access"))
        return
    try:
        code, discount = context.args[0], int(context.args[1])
        await create_promo(code, discount)
        logger.info(f"Promo code {code} created by admin {update.effective_user.id}")
        await update.message.reply_text(
            get_translation(update, "create_promo.success", code=code, discount=discount),
            parse_mode="Markdown"
        )
    except Exception:
        logger.error(f"Invalid format for /create_promo by user {update.effective_user.id}")
        await update.message.reply_text(get_translation(update, "create_promo.invalid_format"))

async def create_subscription_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.telegram.admin_ids:
        logger.warning(f"Unauthorized access to /create_subscription by user {update.effective_user.id}")
        await update.message.reply_text(get_translation(update, "create_subscription.no_access"))
        return
    try:
        sub_type, duration_days, price = context.args[0].lower(), int(context.args[1]), int(context.args[2])
        await create_subscription_type(sub_type, duration_days, price)
        logger.info(f"Subscription type {sub_type} created by admin {update.effective_user.id}")
        await update.message.reply_text(
            get_translation(update, "create_subscription.success", type=sub_type, days=duration_days, price=price),
            parse_mode="Markdown"
        )
    except Exception:
        logger.error(f"Invalid format for /create_subscription by user {update.effective_user.id}")
        await update.message.reply_text(get_translation(update, "create_subscription.invalid_format"))

async def delete_subscription_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.telegram.admin_ids:
        logger.warning(f"Unauthorized access to /delete_subscription by user {update.effective_user.id}")
        await update.message.reply_text(get_translation(update, "delete_subscription.no_access"))
        return
    try:
        sub_type = context.args[0].lower()
        if await delete_subscription_type(sub_type):
            await update.message.reply_text(
                get_translation(update, "delete_subscription.success", type=sub_type),
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                get_translation(update, "delete_subscription.not_found", type=sub_type),
                parse_mode="Markdown"
            )
    except Exception:
        logger.error(f"Invalid format for /delete_subscription by user {update.effective_user.id}")
        await update.message.reply_text(get_translation(update, "delete_subscription.invalid_format"))

async def get_subscription_lists_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subs = await get_subscription_types(context)
    if not subs:
        await update.message.reply_text(get_translation(update, "list_subscriptions.active"))
        logger.info("No subscription types available")
        return
    message = get_translation(update, "subscriptions.header") + "\n"
    for sub in subs:
        message += get_translation(
            update,
            "subscriptions.item",
            type=sub["type"],
            days=sub["duration_days"],
            price=sub["price"]
        ) + "\n"
    await update.message.reply_text(message)
    logger.info(f"User {update.effective_user.id} viewed subscription types")

async def active_subscriptions_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.telegram.admin_ids:
        logger.warning(f"Unauthorized access to /active_subscriptions by user {update.effective_user.id}")
        await update.message.reply_text(get_translation(update, "active_subscriptions.no_access"))
        return
    subs = await get_active_subscriptions()
    if not subs:
        await update.message.reply_text(get_translation(update, "active_subscriptions.empty"))
        logger.info("No active subscriptions found")
        return
    message = get_translation(update, "active_subscriptions.header") + "\n"
    for sub in subs:
        message += get_translation(
            update,
            "active_subscriptions.item",
            user_id=sub["user_id"],
            type=sub["subscription_type"],
            days_left=sub["days_left"],
            token=sub["token"]
        ) + "\n"
    await update.message.reply_text(message, parse_mode="Markdown")
    logger.info(f"Admin {update.effective_user.id} viewed active subscriptions")

async def my_subscription_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sub = await get_user_subscription(user_id)
    if not sub:
        await update.message.reply_text(get_translation(update, "my_subscription.none"))
        logger.info(f"User {user_id} has no active subscription")
        return
    message = get_translation(update, "my_subscription.header") + "\n"
    message += get_translation(
        update,
        "my_subscription.item",
        type=sub["subscription_type"],
        days_left=sub["days_left"],
        token=sub["token"]
    )
    await update.message.reply_text(message, parse_mode="Markdown")
    logger.info(f"User {user_id} viewed their subscription")

async def notify_expiring_subscriptions(context: ContextTypes.DEFAULT_TYPE):
    users = await get_users_with_expiring_tokens()
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user["chat_id"],
                text=get_translation({"effective_user": {"language_code": "ru"}}, "subscription_expiring")
            )
            logger.info(f"Sent expiration notification to user {user['user_id']}")
        except Exception as e:
            logger.error(f"Failed to notify user {user['user_id']}: {str(e)}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sub = await get_user_subscription(user_id)
    if isinstance(sub, dict) and sub.get("error") == "db_unavailable":
        await update.message.reply_text("⚠️ Техническая ошибка: база данных недоступна. Попробуйте позже.")
        return
    if sub and sub.get('active'):
        end_date = sub.get('end_date')
        await update.message.reply_text(
            get_translation(update, "subscription.active", end_date=end_date)
        )
    else:
        await update.message.reply_text(get_translation(update, "subscription.inactive"))

async def delete_promo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.telegram.admin_ids:
        await update.message.reply_text("Эта команда доступна только администраторам. / This command is for admins only.")
        return

    promo_code = context.args[0] if context.args else None
    if not promo_code:
        await update.message.reply_text("Укажите промокод для удаления: /delete_promo <код>")
        return

    try:
        async with aiosqlite.connect(config.database.path) as db:
            cursor = await db.execute("DELETE FROM promo_codes WHERE code = ?", (promo_code,))
            await db.commit()
            if cursor.rowcount > 0:
                await update.message.reply_text(f"Промокод '{promo_code}' успешно удален.")
            else:
                await update.message.reply_text(f"Промокод '{promo_code}' не найден.")
    except Exception as e:
        logger.error(f"Error deleting promo code {promo_code}: {e}")
        await update.message.reply_text("Произошла ошибка при удалении промокода.")

async def create_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создает бэкап базы данных и отправляет его админам"""
    user_id = update.effective_user.id

    # Проверяем права администратора
    if user_id not in config.telegram.admin_ids:
        await update.message.reply_text("Эта команда доступна только администраторам. / This command is for admins only.")
        return

    try:
        # Создаем бэкап
        success, backup_path = backup_manager.create_backup(include_time=True)

        if not success:
            await update.message.reply_text("❌ Произошла ошибка при создании бэкапа / Error creating backup")
            return

        # Отправляем файл всем админам
        success_count = 0
        for admin_id in config.telegram.admin_ids:
            try:
                with open(backup_path, 'rb') as backup_file:
                    backup_filename = os.path.basename(backup_path)
                    await context.bot.send_document(
                        chat_id=admin_id,
                        document=backup_file,
                        caption=f"📦 Бэкап базы данных\n"
                                f"📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                                f"📁 Файл: {backup_filename}\n\n"
                                f"📦 Database backup\n"
                                f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                                f"📁 File: {backup_filename}"
                    )
                success_count += 1
                logger.info(f"Backup sent to admin {admin_id}")
            except Exception as e:
                logger.error(f"Failed to send backup to admin {admin_id}: {e}")

        # Отправляем подтверждение пользователю
        if success_count > 0:
            backup_filename = os.path.basename(backup_path)
            await update.message.reply_text(
                f"✅ Бэкап успешно создан и отправлен {success_count} администраторам\n"
                f"📁 Файл: {backup_filename}\n\n"
                f"✅ Backup successfully created and sent to {success_count} admins\n"
                f"📁 File: {backup_filename}"
            )
        else:
            await update.message.reply_text("❌ Ошибка при отправке бэкапа администраторам / Error sending backup to admins")

    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        await update.message.reply_text("❌ Произошла ошибка при создании бэкапа / Error creating backup")

async def send_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет последний бэкап админу по запросу"""
    user_id = update.effective_user.id

    # Проверяем права администратора
    if user_id not in config.telegram.admin_ids:
        await update.message.reply_text("Эта команда доступна только администраторам. / This command is for admins only.")
        return

    try:
        # Ищем последний бэкап
        latest_backup = backup_manager.get_latest_backup()

        if not latest_backup:
            await update.message.reply_text(
                "❌ Бэкапы не найдены. Создайте бэкап командой /backup\n\n"
                "❌ No backups found. Create a backup with /backup command"
            )
            return

        # Отправляем файл запросившему админу
        with open(latest_backup, 'rb') as backup_file:
            backup_filename = os.path.basename(latest_backup)
            await context.bot.send_document(
                chat_id=user_id,
                document=backup_file,
                caption=f"📦 Последний бэкап базы данных\n"
                        f"📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"📁 Файл: {backup_filename}\n\n"
                        f"📦 Latest database backup\n"
                        f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"📁 File: {backup_filename}"
            )

        logger.info(f"Latest backup sent to admin {user_id}")
        await update.message.reply_text(
            f"✅ Последний бэкап отправлен\n"
            f"📁 Файл: {backup_filename}\n\n"
            f"✅ Latest backup sent\n"
            f"📁 File: {backup_filename}"
        )

    except Exception as e:
        logger.error(f"Error sending backup to admin {user_id}: {e}")
        await update.message.reply_text("❌ Произошла ошибка при отправке бэкапа / Error sending backup")

async def scheduled_backup(context: ContextTypes.DEFAULT_TYPE):
    """Автоматическое создание бэкапа раз в сутки"""
    try:
        # Создаем бэкап (без времени в имени для ежедневных бэкапов)
        success, backup_path = backup_manager.create_backup(include_time=False)

        if not success:
            logger.error("Failed to create automatic backup")
            return

        # Отправляем файл всем админам
        success_count = 0
        for admin_id in config.telegram.admin_ids:
            try:
                with open(backup_path, 'rb') as backup_file:
                    backup_filename = os.path.basename(backup_path)
                    await context.bot.send_document(
                        chat_id=admin_id,
                        document=backup_file,
                        caption=f"📦 Автоматический бэкап базы данных\n"
                                f"📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                                f"📁 Файл: {backup_filename}\n\n"
                                f"📦 Automatic database backup\n"
                                f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                                f"📁 File: {backup_filename}"
                    )
                success_count += 1
                logger.info(f"Automatic backup sent to admin {admin_id}")
            except Exception as e:
                logger.error(f"Failed to send automatic backup to admin {admin_id}: {e}")

        logger.info(f"Automatic backup completed. Sent to {success_count} admins")

    except Exception as e:
        logger.error(f"Error creating automatic backup: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "FindMyLink — быстрый поиск по закладкам и вкладкам.\n\n"
        "/start — Запустить бота / Start the bot\n"
        "/get_trial — Получить 14-дневный пробный период / Get 14-day trial\n"
        "/subscribe — Оформить или продлить подписку / Subscribe or renew subscription\n"
        "/status — Проверить статус подписки / Check subscription status\n"
        "/subscriptions — Доступные подписки / Available plans\n"
        "/help — Получить справку по функциям / Help and usage info\n"
        "/promo — Активировать промокод / Activate promo code\n"
        "/unsubscribe — Отключить автопродление / Disable auto-renewal\n"
        "\nFindMyLink — fast search for bookmarks and tabs.\n"
        "All commands are available in English and Russian."
    )
    await update.message.reply_text(help_text)

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Проверяем текущую подписку пользователя
    subscription = await get_user_subscription(user_id)

    if not subscription:
        await update.message.reply_text(
            "У вас нет активной подписки для отмены. / You don't have an active subscription to cancel."
        )
        return

    if not subscription.get('active'):
        await update.message.reply_text(
            "Ваша подписка уже неактивна. / Your subscription is already inactive."
        )
        return

    if not subscription.get('auto_renewal'):
        await update.message.reply_text(
            "Автопродление уже отключено. / Auto-renewal is already disabled."
        )
        return

    # Отключаем автопродление
    success = await disable_auto_renewal(user_id)

    if success:
        end_date = subscription.get('end_date', 'неизвестно')
        await update.message.reply_text(
            f"✅ Автопродление отключено! / Auto-renewal disabled!\n\n"
            f"Ваша подписка будет активна до {end_date}. / Your subscription will remain active until {end_date}.\n\n"
            f"Чтобы снова включить автопродление, обратитесь к администратору. / To re-enable auto-renewal, contact the administrator."
        )
    else:
        await update.message.reply_text(
            "❌ Произошла ошибка при отключении автопродления. Попробуйте позже. / Error occurred while disabling auto-renewal. Please try again later."
        )

async def subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    types = await get_subscription_types()
    if not types:
        await update.message.reply_text("Нет доступных подписок / No available plans.")
        return
    lines = ["Доступные подписки / Available plans:"]
    keyboard = []
    for sub in types:
        ru = {
            'day': '1 день',
            'month': '1 месяц',
            'quarter': '3 месяца',
            'halfyear': '6 месяцев',
            'year': '1 год'
        }.get(sub['type'], f"{sub['duration_days']} дней")
        en = {
            'day': '1 day',
            'month': '1 month',
            'quarter': '3 months',
            'halfyear': '6 months',
            'year': '1 year'
        }.get(sub['type'], f"{sub['duration_days']} days")
        price = sub.get('price', 0)
        lines.append(f"• {ru} / {en} — {price} ⭐")
        keyboard.append([
            InlineKeyboardButton(
                f"Оформить / Subscribe ({ru}/{en})",
                callback_data=f"subscribe_{sub['type']}"
            )
        ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('\n'.join(lines), reply_markup=reply_markup)

async def subscriptions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("subscribe_"):
        sub_type = data.replace("subscribe_", "")
        await _send_subscription_invoice(
            bot=context.bot,
            chat_id=query.message.chat_id,
            user_id=query.from_user.id,
            sub_type=sub_type,
            promo_code=None,  # No promo code from inline buttons
            update_for_translation=update,
        )

def setup_handlers(app: Application):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("get_trial", get_trial))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("promo", apply_promo))
    app.add_handler(CommandHandler("create_promo", create_promo_cmd))
    app.add_handler(CommandHandler("create_subscription", create_subscription_cmd))
    app.add_handler(CommandHandler("delete_subscription", delete_subscription_cmd))
    app.add_handler(CommandHandler("list_subscriptions", get_subscription_lists_cmd))
    app.add_handler(CommandHandler("active_subscriptions", active_subscriptions_cmd))
    app.add_handler(CommandHandler("my_subscription", my_subscription_cmd))
    app.add_handler(CommandHandler("subscriptions", subscriptions))
    from telegram.ext import CallbackQueryHandler
    app.add_handler(CallbackQueryHandler(subscriptions_callback, pattern="^subscribe_"))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_query))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.job_queue.run_repeating(notify_expiring_subscriptions, interval=3600)
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CommandHandler("delete_promo", delete_promo_cmd))
    app.add_handler(CommandHandler("backup", create_backup))
    app.add_handler(CommandHandler("send_backup", send_backup))
    app.add_handler(CommandHandler("scheduled_backup", scheduled_backup))
    logger.info("Handlers set up for bot")
