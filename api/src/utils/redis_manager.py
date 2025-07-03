import redis.asyncio as redis
import logging
from typing import Optional, Dict, Any
from src.configs.config import config


logger = logging.getLogger(__name__)


class RedisManager:
    """Менеджер для работы с Redis"""

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or config.redis.url
        self.client = None
        self._connected = False
        self._init_client()

    def _init_client(self):
        """Инициализация клиента Redis"""
        try:
            self.client = redis.Redis(
                host="localhost",
                port=6379,
                db=0,
                decode_responses=config.redis.decode_responses,
            )
            self._connected = True
            logger.info(f"Redis client initialized with URL: {self.redis_url}")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis client: {e}")
            self._connected = False

    async def _ensure_connection(self):
        """Проверка и восстановление соединения с Redis"""
        if not self._connected or not self.client:
            self._init_client()

        if self.client:
            try:
                await self.client.ping()
                return True
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self._connected = False
                return False
        return False

    async def get_user_token(self, user_id: int) -> Optional[str]:
        """Получить токен пользователя"""
        try:
            if not await self._ensure_connection():
                logger.warning("Redis not available, returning None for user token")
                return None

            key = f"user:{user_id}:token"
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Error getting user token for {user_id}: {e}")
            return None

    async def set_user_token(self, user_id: int, token: str, ttl: int = None) -> bool:
        """Установить токен пользователя"""
        try:
            if not await self._ensure_connection():
                logger.warning("Redis not available, skipping token storage")
                return False

            key = f"user:{user_id}:token"
            ttl = ttl or config.redis.default_ttl
            await self.client.set(key, token, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Error setting user token for {user_id}: {e}")
            return False

    async def get_token_user(self, token: str) -> Optional[int]:
        """Получить пользователя по токену"""
        try:
            if not await self._ensure_connection():
                logger.warning("Redis not available, returning None for token user")
                return None

            key = f"token:{token}"
            user_id = await self.client.get(key)
            return int(user_id) if user_id else None
        except Exception as e:
            logger.error(f"Error getting user by token: {e}")
            return None

    async def set_token_user(self, token: str, user_id: int, ttl: int = None) -> bool:
        """Установить связь токен-пользователь"""
        try:
            if not await self._ensure_connection():
                logger.warning("Redis not available, skipping token-user mapping")
                return False

            key = f"token:{token}"
            ttl = ttl or config.redis.default_ttl
            await self.client.set(key, user_id, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Error setting token-user mapping: {e}")
            return False

    async def get_user_info(self, user_id: int) -> Dict[str, Any]:
        """Получить информацию о пользователе"""
        try:
            if not await self._ensure_connection():
                logger.warning("Redis not available, returning empty user info")
                return {}

            key = f"user:{user_id}:info"
            info = await self.client.hgetall(key)
            return info or {}
        except Exception as e:
            logger.error(f"Error getting user info for {user_id}: {e}")
            return {}

    async def set_user_info(self, user_id: int, info: Dict[str, Any]) -> bool:
        """Установить информацию о пользователе"""
        try:
            if not await self._ensure_connection():
                logger.warning("Redis not available, skipping user info storage")
                return False

            key = f"user:{user_id}:info"
            await self.client.hset(key, mapping=info)
            return True
        except Exception as e:
            logger.error(f"Error setting user info for {user_id}: {e}")
            return False

    async def get_user_info_field(self, user_id: int, field: str) -> Optional[str]:
        """Получить конкретное поле информации о пользователе"""
        try:
            key = f"user:{user_id}:info"
            return await self.client.hget(key, field)
        except Exception as e:
            logger.error(f"Error getting user info field {field} for {user_id}: {e}")
            return None

    async def set_user_info_field(self, user_id: int, field: str, value: str) -> bool:
        """Установить конкретное поле информации о пользователе"""
        try:
            key = f"user:{user_id}:info"
            await self.client.hset(key, field, value)
            return True
        except Exception as e:
            logger.error(f"Error setting user info field {field} for {user_id}: {e}")
            return False

    async def get_rate_limit(self, identifier: str) -> int:
        """Получить текущий счетчик rate limit"""
        try:
            key = f"rate_limit:{identifier}"
            count = await self.client.get(key)
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Error getting rate limit for {identifier}: {e}")
            return 0

    async def increment_rate_limit(self, identifier: str) -> int:
        """Увеличить счетчик rate limit"""
        try:
            key = f"rate_limit:{identifier}"
            pipe = self.client.pipeline()
            pipe.incr(key)
            pipe.expire(key, config.rate_limit.window)
            results = await pipe.execute()
            return results[0]
        except Exception as e:
            logger.error(f"Error incrementing rate limit for {identifier}: {e}")
            return 0

    async def get_promo_attempts(self, user_id: int) -> int:
        """Получить количество попыток использования промокода"""
        try:
            key = f"promo_attempts:{user_id}"
            count = await self.client.get(key)
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Error getting promo attempts for {user_id}: {e}")
            return 0

    async def increment_promo_attempts(self, user_id: int) -> int:
        """Увеличить счетчик попыток использования промокода"""
        try:
            key = f"promo_attempts:{user_id}"
            pipe = self.client.pipeline()
            pipe.incr(key)
            pipe.expire(key, 3600)  # 1 час
            results = await pipe.execute()
            return results[0]
        except Exception as e:
            logger.error(f"Error incrementing promo attempts for {user_id}: {e}")
            return 0

    async def delete_user_data(self, user_id: int) -> bool:
        """Удалить все данные пользователя из Redis"""
        try:
            keys_to_delete = [
                f"user:{user_id}:token",
                f"user:{user_id}:info",
                f"promo_attempts:{user_id}",
            ]
            await self.client.delete(*keys_to_delete)
            return True
        except Exception as e:
            logger.error(f"Error deleting user data for {user_id}: {e}")
            return False

    async def get_ttl(self, key: str) -> int:
        """Получить TTL ключа"""
        try:
            return await self.client.ttl(key)
        except Exception as e:
            logger.error(f"Error getting TTL for key {key}: {e}")
            return -1

    async def close(self):
        """Закрыть соединение с Redis"""
        try:
            await self.client.close()
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")


# Создаем глобальный экземпляр менеджера Redis
redis_manager = RedisManager()
