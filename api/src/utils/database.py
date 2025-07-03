from collections.abc import AsyncGenerator
import logging
from datetime import datetime, UTC
from typing import Optional, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from litestar.exceptions import ClientException
from litestar.status_codes import HTTP_409_CONFLICT

# Импортируем модели из отдельного файла
from src.models.models import (
    User,
    Subscription,
    PromoCode,
    PromoAttempt,
    SubscriptionType,
    Purchase,
)


logger = logging.getLogger(__name__)


def is_alembic_context() -> bool:
    """Определить, запущен ли код в контексте Alembic"""
    import os
    import sys

    # Проверяем переменные окружения
    if os.environ.get("ALEMBIC_CONTEXT"):
        return True

    # Проверяем имя процесса
    if "alembic" in sys.argv[0].lower():
        return True

    # Проверяем, есть ли alembic в аргументах командной строки
    if any("alembic" in arg.lower() for arg in sys.argv):
        return True

    # Проверяем, импортирован ли alembic в текущем контексте
    try:
        import alembic

        # Дополнительная проверка - если мы в процессе создания миграций
        if hasattr(alembic, "context") and alembic.context is not None:
            return True
    except ImportError:
        pass

    return False


async def provide_transaction(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncSession, None]:
    """Dependency для управления транзакциями базы данных"""
    try:
        async with db_session.begin():
            yield db_session
    except IntegrityError as exc:
        raise ClientException(
            status_code=HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


# Utility functions для работы с базой данных
async def get_user_by_id(user_id: int, session: AsyncSession) -> Optional[User]:
    """Получить пользователя по ID"""
    query = select(User).where(User.user_id == user_id)
    result = await session.execute(query)
    try:
        return result.scalar_one()
    except NoResultFound:
        return None


async def get_subscription_by_user_id(
    user_id: int, session: AsyncSession
) -> Optional[Subscription]:
    """Получить подписку пользователя"""
    query = select(Subscription).where(Subscription.user_id == user_id)
    result = await session.execute(query)
    try:
        return result.scalar_one()
    except NoResultFound:
        return None


async def get_promo_code_by_code(
    code: str, session: AsyncSession
) -> Optional[PromoCode]:
    """Получить промокод по коду"""
    query = select(PromoCode).where(PromoCode.code == code)
    result = await session.execute(query)
    try:
        return result.scalar_one()
    except NoResultFound:
        return None


async def get_promo_attempts_by_user_id(
    user_id: int, hours: int, session: AsyncSession
) -> List[PromoAttempt]:
    """Получить попытки использования промокода за последние часы"""
    cutoff_time = datetime.now(UTC).replace(hour=datetime.now(UTC).hour - hours)
    query = select(PromoAttempt).where(
        PromoAttempt.user_id == user_id, PromoAttempt.attempt_time > cutoff_time
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def has_user_used_promo(user_id: int, code: str, session: AsyncSession) -> bool:
    """Проверить, применял ли пользователь этот промокод"""
    query = select(PromoAttempt).where(
        PromoAttempt.user_id == user_id, PromoAttempt.code == code
    )
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None


async def add_promo_attempt(user_id: int, code: str, session: AsyncSession) -> bool:
    """Добавить попытку использования промокода с кодом"""
    try:
        attempt = PromoAttempt(user_id=user_id, code=code)
        session.add(attempt)
        await session.flush()
        return True
    except Exception as e:
        logger.error(f"Error adding promo attempt for user {user_id}, code {code}: {e}")
        return False


class DatabaseManager:
    """Менеджер для работы с базой данных через SQLAlchemy"""

    def __init__(self, db_path: str = None):
        # Условный импорт config
        try:
            from src.configs.config import config as app_config

            self.db_path = db_path or app_config.database.path
            self.config = app_config.database
        except ImportError:
            # Для alembic миграций используем дефолтный путь
            self.db_path = db_path or "./data/subscriptions.db"
            self.config = None

    def get_connection_string(self, async_mode: bool = None) -> str:
        """Получить connection string для базы данных

        Args:
            async_mode: True для async (aiosqlite), False для sync (sqlite)
                       Если None, автоматически определяется по контексту
        """
        if async_mode is None:
            # Автоматически определяем контекст
            async_mode = not is_alembic_context()

        if self.config:
            return self.config.get_connection_string(async_mode)
        else:
            # Fallback для случаев, когда config недоступен
            if async_mode:
                return f"sqlite+aiosqlite:///{self.db_path}"
            else:
                return f"sqlite:///{self.db_path}"

    async def get_subscription(
        self, user_id: int, session: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Получить подписку пользователя"""
        try:
            subscription = await get_subscription_by_user_id(user_id, session)

            if subscription:
                return {
                    "user_id": subscription.user_id,
                    "end_date": subscription.end_date.isoformat()
                    if subscription.end_date
                    else None,
                    "active": subscription.active,
                    "lang": subscription.lang,
                    "trial_used": subscription.trial_used,
                    "auto_renewal": subscription.auto_renewal,
                    "subtype": subscription.subtype.value
                    if isinstance(subscription.subtype, SubscriptionType)
                    else subscription.subtype,
                    "created_at": subscription.created_at.isoformat()
                    if subscription.created_at
                    else None,
                    "updated_at": subscription.updated_at.isoformat()
                    if subscription.updated_at
                    else None,
                }
            return None
        except Exception as e:
            logger.error(f"Error getting subscription for user {user_id}: {e}")
            return None

    async def update_subscription(
        self, user_id: int, session: AsyncSession, **kwargs
    ) -> bool:
        """Обновить подписку пользователя"""
        try:
            subscription = await get_subscription_by_user_id(user_id, session)

            if not subscription:
                subscription = Subscription(user_id=user_id)
                session.add(subscription)

            for key, value in kwargs.items():
                if key == "subtype" and isinstance(value, str):
                    value = SubscriptionType(value)
                if hasattr(subscription, key):
                    setattr(subscription, key, value)

            await session.flush()
            return True
        except Exception as e:
            logger.error(f"Error updating subscription for user {user_id}: {e}")
            return False

    async def get_promo_code(
        self, promo_code: str, session: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Получить промокод"""
        try:
            promo = await get_promo_code_by_code(promo_code, session)

            if promo:
                return {
                    "code": promo.code,
                    "discount": promo.discount,
                    "expiration_date": promo.expiration_date.isoformat()
                    if promo.expiration_date
                    else None,
                    "used": promo.used,
                }
            return None
        except Exception as e:
            logger.error(f"Error getting promo code {promo_code}: {e}")
            return None

    async def mark_promo_used(self, promo_code: str, session: AsyncSession) -> bool:
        """Отметить промокод как использованный"""
        try:
            promo = await get_promo_code_by_code(promo_code, session)
            if promo:
                promo.used = True
                await session.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Error marking promo code {promo_code} as used: {e}")
            return False

    async def get_promo_attempts_count(
        self, user_id: int, hours: int = 1, session: AsyncSession = None
    ) -> int:
        """Получить количество попыток использования промокода за последние часы"""
        try:
            attempts = await get_promo_attempts_by_user_id(user_id, hours, session)
            return len(attempts)
        except Exception as e:
            logger.error(f"Error getting promo attempts count for user {user_id}: {e}")
            return 0

    async def create_user(
        self,
        user_id: int,
        first_name: str,
        last_name: str = None,
        username: str = None,
        photo_url: str = None,
        session: AsyncSession = None,
    ) -> Optional[User]:
        """Создать нового пользователя"""
        try:
            user = User(
                user_id=user_id,
                first_name=first_name,
                last_name=last_name,
                username=username,
                photo_url=photo_url,
            )
            session.add(user)
            await session.flush()
            return user
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return None

    async def get_or_create_user(
        self,
        user_id: int,
        first_name: str,
        last_name: str = None,
        username: str = None,
        photo_url: str = None,
        session: AsyncSession = None,
    ) -> User:
        """Получить существующего пользователя или создать нового"""
        user = await get_user_by_id(user_id, session)
        if not user:
            user = await self.create_user(
                user_id, first_name, last_name, username, photo_url, session
            )
        return user

    async def has_user_used_promo(
        self, user_id: int, code: str, session: AsyncSession
    ) -> bool:
        return await has_user_used_promo(user_id, code, session)

    async def add_promo_attempt(
        self, user_id: int, code: str, session: AsyncSession
    ) -> bool:
        return await add_promo_attempt(user_id, code, session)

    async def add_purchase(
        self, user_id: int, subscription_type: str, price: int, session: AsyncSession
    ) -> bool:
        """Добавить запись о покупке подписки"""
        try:
            purchase = Purchase(
                user_id=user_id, subscription=subscription_type, price=price
            )
            session.add(purchase)
            await session.flush()
            return True
        except Exception as e:
            logger.error(f"Error adding purchase for user {user_id}: {e}")
            return False

    async def get_user_purchases(
        self, user_id: int, session: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Получить историю покупок пользователя"""
        try:
            result = await session.execute(
                select(Purchase)
                .where(Purchase.user_id == user_id)
                .order_by(Purchase.created_at.desc())
            )
            purchases = result.scalars().all()
            return [
                {
                    "id": p.id,
                    "subscription": p.subscription,
                    "price": p.price,
                    "created_at": p.created_at.isoformat(),
                }
                for p in purchases
            ]
        except Exception as e:
            logger.error(f"Error getting purchases for user {user_id}: {e}")
            return []

    async def get_subscription_price(
        self, subscription_type: str, session: AsyncSession
    ) -> Optional[int]:
        """Получить цену подписки"""
        try:
            result = await session.execute(
                select(SubscriptionType).where(
                    SubscriptionType.name == subscription_type
                )
            )
            subscription = result.scalar_one_or_none()
            return subscription.price if subscription else None
        except Exception as e:
            logger.error(
                f"Error getting price for subscription type {subscription_type}: {e}"
            )
            return None


# Создаем глобальный экземпляр менеджера базы данных
db_manager = DatabaseManager()
