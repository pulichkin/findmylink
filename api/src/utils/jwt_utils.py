import jwt
import logging
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any
from src.configs.config import config
import hmac
import hashlib
import time


logger = logging.getLogger(__name__)


class JWTManager:
    """Менеджер для работы с JWT токенами"""

    def __init__(
        self, secret: str = None, algorithm: str = None, expiry_days: int = None
    ):
        self.secret = secret or config.jwt.secret
        self.algorithm = algorithm or config.jwt.algorithm
        self.expiry_days = expiry_days or config.jwt.expiry_days

    def encode_token(self, payload: Dict[str, Any], expiry_days: int = None) -> str:
        """Закодировать JWT токен"""
        try:
            # Добавляем время истечения
            expiry = expiry_days or self.expiry_days
            payload_with_exp = {
                **payload,
                "exp": datetime.now(UTC) + timedelta(days=expiry),
                "iat": datetime.now(UTC),
            }

            token = jwt.encode(payload_with_exp, self.secret, algorithm=self.algorithm)

            logger.debug(f"JWT token encoded for user_id: {payload.get('user_id')}")
            return token

        except Exception as e:
            logger.error(f"Error encoding JWT token: {e}")
            raise

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Декодировать JWT токен"""
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])

            logger.debug(f"JWT token decoded for user_id: {payload.get('user_id')}")
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error decoding JWT token: {e}")
            return None

    def create_user_token(
        self, user_id: int, additional_payload: Dict[str, Any] = None
    ) -> str:
        """Создать токен для пользователя"""
        payload = {"user_id": user_id, "type": "user_token"}

        if additional_payload:
            payload.update(additional_payload)

        return self.encode_token(payload)

    def get_user_id_from_token(self, token: str) -> Optional[int]:
        """Получить user_id из токена"""
        payload = self.decode_token(token)
        if payload and "user_id" in payload:
            return payload["user_id"]
        return None

    def is_token_valid(self, token: str) -> bool:
        """Проверить валидность токена"""
        return self.decode_token(token) is not None

    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """Получить время истечения токена"""
        payload = self.decode_token(token)
        if payload and "exp" in payload:
            return datetime.fromtimestamp(payload["exp"])
        return None

    def is_token_expired(self, token: str) -> bool:
        """Проверить, истек ли токен"""
        expiry = self.get_token_expiry(token)
        if expiry:
            return datetime.now(UTC) > expiry
        return True

    def refresh_token(self, token: str, new_expiry_days: int = None) -> Optional[str]:
        """Обновить токен"""
        payload = self.decode_token(token)
        if payload:
            # Удаляем служебные поля
            payload.pop("exp", None)
            payload.pop("iat", None)

            # Создаем новый токен
            return self.encode_token(payload, new_expiry_days)
        return None


# Создаем глобальный экземпляр менеджера JWT
jwt_manager = JWTManager()


# Функции для обратной совместимости
def encode_jwt_token(payload: Dict[str, Any]) -> str:
    """Закодировать JWT токен (для обратной совместимости)"""
    return jwt_manager.encode_token(payload)


def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Декодировать JWT токен (для обратной совместимости)"""
    return jwt_manager.decode_token(token)


def verify_telegram_signature(
    auth_data: dict, bot_token: str, webapp_data: str
) -> bool:
    logger.info("=== TELEGRAM SIGNATURE VERIFICATION ===")
    logger.info("BOT_TOKEN: %s", bot_token)
    logger.info("WEBAPP_DATA: %s", webapp_data)
    logger.info(
        "AUTH_DATA TYPES: %s", {k: type(v).__name__ for k, v in auth_data.items()}
    )
    logger.info("AUTH_DATA VALUES: %s", auth_data)

    data_check_string = "\n".join(
        [f"{k}={v}" for k, v in sorted(auth_data.items()) if k != "hash"]
    )
    logger.info("DATA_CHECK_STRING: %s", repr(data_check_string))

    # Исправленный алгоритм: SHA256(bot_token) как секретный ключ
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    logger.info("SECRET_KEY (hex): %s", secret_key.hex())

    expected_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    logger.info("EXPECTED_HASH: %s", expected_hash)
    logger.info("RECEIVED_HASH: %s", auth_data["hash"])
    logger.info("MATCH: %s", auth_data["hash"] == expected_hash)
    logger.info("=== END VERIFICATION ===")

    return auth_data["hash"] == expected_hash


def verify_telegram_auth_time(auth_date: int, max_age: int = 86400) -> bool:
    current_time = int(time.time())
    return (current_time - auth_date) <= max_age
