import logging
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from .database import db_manager
from .jwt_utils import jwt_manager, verify_telegram_signature, verify_telegram_auth_time
from src.configs.config import config


logger = logging.getLogger(__name__)


async def authenticate_telegram_user(
    auth_data: Dict[str, Any], session: AsyncSession
) -> Optional[Dict[str, Any]]:
    """Аутентифицировать пользователя через Telegram"""
    try:
        # Проверяем подпись
        if not verify_telegram_signature(
            auth_data, config.telegram.bot_token, config.telegram.webapp_data
        ):
            logger.warning("Invalid Telegram signature")
            return None

        # Проверяем время аутентификации
        if not verify_telegram_auth_time(auth_data["auth_date"]):
            logger.warning("Telegram auth data expired")
            return None

        user_id = int(auth_data["id"])

        # Создаем или обновляем пользователя
        user_data = {
            "username": auth_data.get("username"),
            "photo_url": auth_data.get("photo_url"),
            "lang": auth_data.get("language_code", "ru"),
        }

        # Используем get_or_create_user вместо update_user
        user = await db_manager.get_or_create_user(
            user_id,
            auth_data.get("first_name", ""),
            auth_data.get("last_name"),
            auth_data.get("username"),
            auth_data.get("photo_url"),
            session,
        )

        if not user:
            logger.error(f"Failed to create/update user {user_id}")
            return None

        # Создаем JWT токен
        token = jwt_manager.create_user_token(user_id)

        await session.commit()
        logger.info(f"User {user_id} authenticated successfully")

        return {"token": token, "user_id": user_id, **user_data}

    except Exception as e:
        logger.error(f"Error during Telegram authentication: {e}")
        return None


async def verify_token(token: str) -> Tuple[bool, Optional[int]]:
    """Проверить JWT токен"""
    try:
        payload = jwt_manager.decode_token(token)
        if payload and "user_id" in payload:
            return True, payload["user_id"]
        return False, None
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return False, None
