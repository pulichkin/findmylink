from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from .database import db_manager

logger = logging.getLogger(__name__)


async def apply_promo(
    user_id: int, promo_code: str, session: AsyncSession
) -> Optional[Dict[str, Any]]:
    """Применить промокод к подписке пользователя"""
    try:
        # Проверяем существование промокода
        promo = await db_manager.get_promo_code(promo_code, session)
        if not promo:
            logger.warning(f"Promo code {promo_code} not found for user {user_id}")
            return None

        # Проверяем срок действия промокода
        if promo["expiration_date"]:
            expiration_date = datetime.fromisoformat(promo["expiration_date"])
            if expiration_date < datetime.now():
                logger.warning(f"Promo code {promo_code} expired for user {user_id}")
                return None

        # Проверяем, использовал ли пользователь этот промокод ранее
        if await db_manager.has_user_used_promo(user_id, promo_code, session):
            logger.warning(f"User {user_id} already used promo code {promo_code}")
            return None

        # Получаем текущую подписку
        subscription = await db_manager.get_subscription(user_id, session)
        if not subscription:
            logger.warning(f"No subscription found for user {user_id}")
            return None

        # Вычисляем новую дату окончания подписки
        current_end_date = (
            datetime.fromisoformat(subscription["end_date"])
            if subscription["end_date"]
            else datetime.now()
        )
        extension_days = promo[
            "discount"
        ]  # В данном случае discount используется как количество дней
        new_end_date = current_end_date + timedelta(days=extension_days)

        # Обновляем подписку
        success = await db_manager.update_subscription(
            user_id, session, end_date=new_end_date, active=True
        )
        if not success:
            logger.error(f"Failed to update subscription for user {user_id}")
            return None

        # Фиксируем использование промокода
        await db_manager.add_promo_attempt(user_id, promo_code, session)
        await session.commit()

        logger.info(f"Promo code {promo_code} applied successfully for user {user_id}")
        return {
            "message": f"Promo code applied! Subscription extended by {extension_days} days",
            "days_added": extension_days,
            "new_end_date": new_end_date.isoformat(),
        }

    except Exception as e:
        logger.error(f"Error applying promo code for user {user_id}: {e}")
        return None


async def create_promo(
    code: str,
    discount: int,
    session: AsyncSession,
    expiration_date: Optional[datetime] = None,
) -> bool:
    """Создать новый промокод"""
    try:
        success = await db_manager.create_promo_code(
            code, discount, expiration_date, session
        )
        if success:
            await session.commit()
            logger.info(f"Promo code {code} created with {discount}% discount")
        return success
    except Exception as e:
        logger.error(f"Error creating promo code {code}: {e}")
        return False


async def get_promo_info(code: str, session: AsyncSession) -> Optional[Dict[str, Any]]:
    """Получить информацию о промокоде"""
    try:
        promo = await db_manager.get_promo_code(code, session)
        if promo:
            logger.info(f"Retrieved info for promo code {code}")
            return promo
        return None
    except Exception as e:
        logger.error(f"Error getting promo code info for {code}: {e}")
        return None
