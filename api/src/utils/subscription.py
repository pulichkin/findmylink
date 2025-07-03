from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from .database import db_manager

logger = logging.getLogger(__name__)


async def save_purchase(
    user_id: int, subscription_type: str, price: int, session: AsyncSession
) -> bool:
    """Сохранить информацию о покупке подписки"""
    try:
        success = await db_manager.add_purchase(
            user_id, subscription_type, price, session
        )
        if success:
            await session.commit()
            logger.info(
                f"Purchase saved for user {user_id}: {subscription_type} for {price} stars"
            )
        return success
    except Exception as e:
        logger.error(f"Error saving purchase for user {user_id}: {e}")
        return False


async def activate_subscription(
    user_id: int, subscription_type: str, session: AsyncSession
) -> bool:
    """Активировать подписку для пользователя"""
    try:
        # Получаем информацию о типе подписки
        price = await db_manager.get_subscription_price(subscription_type, session)
        if price is None:
            logger.error(f"Subscription type {subscription_type} not found")
            return False

        # Сохраняем информацию о покупке
        if not await save_purchase(user_id, subscription_type, price, session):
            logger.error(f"Failed to save purchase for user {user_id}")
            return False

        # Обновляем подписку пользователя
        success = await db_manager.update_subscription(
            user_id,
            session,
            active=True,
            end_date=datetime.now()
            + timedelta(days=30),  # TODO: получать duration из конфига
            subtype=subscription_type,
        )
        if success:
            await session.commit()
            logger.info(
                f"Subscription {subscription_type} activated for user {user_id}"
            )
        return success
    except Exception as e:
        logger.error(f"Error activating subscription for user {user_id}: {e}")
        return False


async def get_subscription(
    user_id: int, session: AsyncSession
) -> Optional[Dict[str, Any]]:
    """Получить информацию о подписке пользователя"""
    try:
        subscription = await db_manager.get_subscription(user_id, session)
        if subscription:
            logger.info(f"Subscription retrieved for user {user_id}")
            return subscription
        return None
    except Exception as e:
        logger.error(f"Error getting subscription for user {user_id}: {e}")
        return None


async def get_purchases(user_id: int, session: AsyncSession) -> List[Dict[str, Any]]:
    """Получить историю покупок пользователя"""
    try:
        purchases = await db_manager.get_user_purchases(user_id, session)
        logger.info(f"Retrieved {len(purchases)} purchases for user {user_id}")
        return purchases
    except Exception as e:
        logger.error(f"Error getting purchases for user {user_id}: {e}")
        return []


async def renew_subscription(
    user_id: int, subscription_type: str, session: AsyncSession
) -> bool:
    """Продлить подписку пользователя"""
    try:
        # Получаем текущую подписку
        current_sub = await get_subscription(user_id, session)
        if not current_sub or not current_sub.get("active"):
            logger.error(f"No active subscription found for user {user_id}")
            return False

        # Получаем информацию о типе подписки
        price = await db_manager.get_subscription_price(subscription_type, session)
        if price is None:
            logger.error(f"Subscription type {subscription_type} not found")
            return False

        # Сохраняем информацию о покупке
        if not await save_purchase(user_id, subscription_type, price, session):
            logger.error(f"Failed to save purchase for user {user_id}")
            return False

        # Обновляем дату окончания подписки
        current_end_date = (
            datetime.fromisoformat(current_sub["end_date"])
            if current_sub.get("end_date")
            else datetime.now()
        )
        new_end_date = current_end_date + timedelta(
            days=30
        )  # TODO: получать duration из конфига

        success = await db_manager.update_subscription(
            user_id,
            session,
            end_date=new_end_date,
            active=True,
            subtype=subscription_type,
        )
        if success:
            await session.commit()
            logger.info(f"Subscription renewed for user {user_id} until {new_end_date}")
        return success
    except Exception as e:
        logger.error(f"Error renewing subscription for user {user_id}: {e}")
        return False
