import logging
from functools import wraps
from typing import Any, Callable
from litestar.exceptions import HTTPException
from litestar.connection import Request
from .auth import verify_token

logger = logging.getLogger(__name__)


def require_auth(func: Callable) -> Callable:
    """
    Декоратор для проверки аутентификации пользователя.
    Проверяет наличие и валидность JWT токена в заголовке Authorization.
    В случае успеха добавляет user_id в kwargs.
    """

    @wraps(func)
    async def wrapper(request: Request, *args: Any, **kwargs: Any) -> Any:
        # Получаем токен из заголовка
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning("Missing or invalid Authorization header")
            raise HTTPException(
                status_code=401, detail="Missing or invalid Authorization header"
            )

        token = auth_header.split(" ")[1]

        # Проверяем токен
        is_valid, user_id = await verify_token(token)
        if not is_valid or user_id is None:
            logger.warning(f"Invalid token: {token[:10]}...")
            raise HTTPException(status_code=401, detail="Invalid token")

        # Добавляем user_id в kwargs
        kwargs["user_id"] = user_id

        return await func(request, *args, **kwargs)

    return wrapper
