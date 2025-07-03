from typing import List
from config_lib.base import BaseConfig
from msgspec import Struct, field

class TelegramConfig(Struct):
    bot_token: str | None = None
    payment_provider_token: str | None = None
    admin_ids: List[int] = 0,

class DatabaseConfig(Struct):
    path: str | None = None
    default_lang: str | None = None
    default_trial_used: bool = False
    default_auto_renewal: bool = True

class RedisConfig(Struct):
    host: str | None = None
    port: int | None = None
    db: int | None = None
    decode_responses: bool | None = None
    default_ttl: int | None = None

class RateLimitConfig(Struct):
    max_attempts: int | None = None
    block_minutes: int | None = None

class SubscriptionConfig(Struct):
    trial_days: int | None = None
    price: int | None = None

class LoggingConfig(Struct):
    level: str | None = None
    format: str | None = "%(asctime)s %(levelname)s %(name)s %(message)s"
    file: str | None = None

class BotConfig(BaseConfig):
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    subscription: SubscriptionConfig = field(default_factory=SubscriptionConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

# Загружаем конфиг из YAML/ENV/CLI
config = BotConfig.load()
