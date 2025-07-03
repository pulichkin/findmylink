import logging
from src.configs.config import config
from src.utils.redis_manager import redis_manager

logger = logging.getLogger(__name__)


async def check_rate_limit(identifier: str) -> bool:
    """
    Проверка rate limit для указанного идентификатора

    Args:
        identifier: Уникальный идентификатор для проверки (например, IP адрес или user_id)

    Returns:
        bool: True если лимит не превышен, False если превышен
    """
    current = await redis_manager.get_rate_limit(identifier)

    if current >= config.rate_limit.max_requests:
        logger.warning(f"Rate limit exceeded for {identifier}")
        return False

    await redis_manager.increment_rate_limit(identifier)
    return True
