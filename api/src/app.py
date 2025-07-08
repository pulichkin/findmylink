from litestar import Litestar, get, post
from litestar.response import Template, Response, Redirect, File
from litestar.config.cors import CORSConfig
from litestar.exceptions import HTTPException
from litestar.logging import LoggingConfig
from litestar.connection import Request
from pydantic import BaseModel
import logging
import os
import msgspec
from urllib.parse import urlencode
from typing import Any

# SQLAlchemy imports
from sqlalchemy.ext.asyncio import AsyncSession
from litestar.plugins.sqlalchemy import SQLAlchemyAsyncConfig, SQLAlchemyPlugin

# Импортируем конфигурацию и утилиты
from src.configs.config import config
from src.models.models import (
    Base,
    SubscriptionResponse,
    PromoApplyResponse,
    ProfileResponse,
)
from src.utils.database import db_manager, provide_transaction
from src.utils.redis_manager import redis_manager
from src.utils.subscription import (
    activate_subscription,
    get_subscription,
    get_purchases,
    renew_subscription,
)
from src.utils.promo import apply_promo
from src.utils.auth import authenticate_telegram_user
from src.utils.decorators import require_auth
from src.utils.rate_limit import check_rate_limit
from litestar.template.config import TemplateConfig
from litestar.contrib.jinja import JinjaTemplateEngine

# Настройка логирования
print("LOG FILE PATH:", config.logging.file)
print("FROM CONFIG TELEGRAM_BOT_USERNAME:", config.telegram.bot_username)
print("FROM ENV TELEGRAM_BOT_USERNAME:", os.getenv("TELEGRAM_BOT_USERNAME"))
if not os.path.exists("logs"):
    os.makedirs("logs")

logging_config = LoggingConfig(
    root={"level": config.logging.level, "handlers": ["queue_listener"]},
    formatters={"standard": {"format": config.logging.format}},
    log_exceptions="always",
)

logging.basicConfig(
    level=getattr(logging, config.logging.level),
    format=config.logging.format,
    handlers=[logging.FileHandler(config.logging.file), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# SQLAlchemy конфигурация
db_config = SQLAlchemyAsyncConfig(
    connection_string=config.database.get_connection_string(async_mode=True),
    metadata=Base.metadata,
    create_all=True,
    before_send_handler="autocommit",
)

# CORS конфигурация
cors_config = CORSConfig(
    allow_origins=config.cors.allow_origins,
    allow_methods=config.cors.allow_methods,
    allow_headers=config.cors.allow_headers,
)


class PromoRequest(BaseModel):
    promo_code: str


@get("/")
async def index_page() -> Template:
    return Template(
        template_name="index.html",
        context={
            "chrome_url": config.extension_links.chrome_url,
            "firefox_url": config.extension_links.firefox_url,
            "edge_url": config.extension_links.edge_url,
        },
    )


@get("/api/v1/subscription")
@require_auth
async def get_user_subscription(
    request: Request, transaction: AsyncSession, **kwargs: Any
) -> dict:
    try:
        user_id = kwargs.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        subscription = await get_subscription(user_id, transaction)
        if not subscription:
            resp = SubscriptionResponse(
                user_id=user_id,
                end_date=None,
                active=False,
                trial_used=config.database.default_trial_used,
                auto_renewal=config.database.default_auto_renewal,
                lang=config.database.default_lang,
            )
            return msgspec.structs.asdict(resp)

        resp = SubscriptionResponse(**subscription)
        logger.info(f"Subscription retrieved for user {user_id}")
        return msgspec.structs.asdict(resp)

    except Exception as e:
        logger.error(f"Error getting subscription for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@get("/api/v1/purchases")
@require_auth
async def get_user_purchases(
    request: Request, transaction: AsyncSession, **kwargs: Any
) -> dict:
    try:
        user_id = kwargs.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        purchases = await get_purchases(user_id, transaction)
        logger.info(f"Retrieved {len(purchases)} purchases for user {user_id}")
        return {"purchases": purchases}

    except Exception as e:
        logger.error(f"Error getting purchases for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@post("/api/v1/subscription/activate")
@require_auth
async def activate_user_subscription(
    request: Request, transaction: AsyncSession, **kwargs: Any
) -> dict:
    try:
        user_id = kwargs.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        data = await request.json()
        subscription_type = data.get("subscription_type")
        if not subscription_type:
            raise HTTPException(status_code=400, detail="subscription_type is required")

        success = await activate_subscription(user_id, subscription_type, transaction)
        if not success:
            raise HTTPException(
                status_code=400, detail="Failed to activate subscription"
            )

        logger.info(f"Subscription {subscription_type} activated for user {user_id}")
        return {"message": "Subscription activated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating subscription for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@post("/api/v1/subscription/renew")
@require_auth
async def renew_user_subscription(
    request: Request, transaction: AsyncSession, **kwargs: Any
) -> dict:
    try:
        user_id = kwargs.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        data = await request.json()
        subscription_type = data.get("subscription_type")
        if not subscription_type:
            raise HTTPException(status_code=400, detail="subscription_type is required")

        success = await renew_subscription(user_id, subscription_type, transaction)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to renew subscription")

        logger.info(f"Subscription {subscription_type} renewed for user {user_id}")
        return {"message": "Subscription renewed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error renewing subscription for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@post("/api/v1/apply_promo")
@require_auth
async def apply_promo_code(
    request: Request, data: PromoRequest, transaction: AsyncSession, **kwargs: Any
) -> dict:
    try:
        user_id = kwargs.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        if not await check_rate_limit(f"promo_{user_id}"):
            logger.warning(f"Rate limit exceeded for promo attempts by user {user_id}")
            raise HTTPException(status_code=429, detail="Too many requests")

        result = await apply_promo(user_id, data.promo_code, transaction)
        if not result:
            raise HTTPException(status_code=400, detail="Failed to apply promo code")

        logger.info(
            f"Promo code {data.promo_code} applied successfully for user {user_id}"
        )
        resp = PromoApplyResponse(**result)
        return msgspec.structs.asdict(resp)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying promo code for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@post("/api/v1/auth/telegram")
async def telegram_auth(request: Request, transaction: AsyncSession) -> dict:
    try:
        auth_data = await request.json()
        result = await authenticate_telegram_user(auth_data, transaction)
        if not result:
            raise HTTPException(status_code=401, detail="Authentication failed")

        logger.info(f"User {result['user_id']} authenticated via Telegram")
        return result

    except Exception as e:
        logger.error(f"Error during Telegram authentication: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@get("/api/v1/telegram-callback")
async def telegram_callback(ext: str, **params) -> Response:
    query = urlencode(params)
    redirect_url = f"{ext}?{query}"
    logger.info(f"Redirecting Telegram callback to extension: {redirect_url}")
    return Redirect(redirect_url)


@get("/api/v1/telegram-login")
async def telegram_login(callback: str | None = None) -> Response:
    if callback:
        server_callback = (
            f"{config.telegram.api_base_url}/telegram-callback?ext={callback}"
        )
    else:
        server_callback = None

    auth_url = f"{config.telegram.oauth_url}?bot_id={config.telegram.bot_id}&origin={config.telegram.base_url}"
    if server_callback:
        auth_url += f"&return_to={server_callback}"

    logger.info(f"Generated Telegram auth URL: {auth_url}")
    return Redirect(auth_url)


@get("/api/v1/profile")
@require_auth
async def get_profile(
    request: Request, transaction: AsyncSession, **kwargs: Any
) -> dict:
    try:
        user_id = kwargs.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_info = await redis_manager.get_user_info(user_id)
        subscription = await db_manager.get_subscription(user_id, transaction)

        resp = ProfileResponse(
            user_id=user_id,
            first_name=user_info.get("first_name", ""),
            last_name=user_info.get("last_name", ""),
            username=user_info.get("username", ""),
            photo_url=user_info.get("photo_url", ""),
            subscription=SubscriptionResponse(**subscription) if subscription else None,
        )
        logger.info(f"Profile retrieved for user {user_id}")
        return msgspec.structs.asdict(resp)

    except Exception as e:
        logger.error(f"Error getting profile for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@get("/extension-auth")
async def extension_auth_page(request: Request) -> Template:
    # Пробрасываем все query параметры в шаблон
    params = dict(request.query_params)
    return Template(
        template_name="auth_page_template.html",
        context={
            "widget_url": config.telegram.widget_url,
            "bot_username": config.telegram.bot_username,
            **params,  # все query параметры будут доступны в шаблоне
        },
    )


@get("/favicon.ico")
async def favicon() -> File:
    return File(path="src/static/favicon.ico")


@get("/site.webmanifest")
async def web_manifest() -> File:
    return File(path="src/static/site.webmanifest")


app = Litestar(
    route_handlers=[
        index_page,
        get_user_subscription,
        get_user_purchases,
        activate_user_subscription,
        renew_user_subscription,
        apply_promo_code,
        telegram_login,
        telegram_auth,
        get_profile,
        extension_auth_page,
        favicon,
        web_manifest,
    ],
    cors_config=cors_config,
    dependencies={"transaction": provide_transaction},
    plugins=[SQLAlchemyPlugin(db_config)],
    logging_config=logging_config,
    template_config=TemplateConfig(
        directory="src/templates",
        engine=JinjaTemplateEngine,
    ),
)
