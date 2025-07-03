from config_lib.base import BaseConfig
from msgspec import Struct, field


# Типизированные структуры для вложенных секций
class TelegramConfig(Struct):
    bot_token: str | None = None
    bot_id: int | None = None
    bot_username: str | None = None
    bot_name: str | None = None
    oauth_url: str | None = None
    widget_url: str | None = None
    webapp_data: str | None = None
    base_url: str | None = None
    api_base_url: str | None = None
    admin_ids: tuple | None = None


class JWTConfig(Struct):
    secret: str | None = None
    algorithm: str | None = None
    expiry_days: int | None = None


class DatabaseConfig(Struct):
    path: str | None = None
    default_lang: str | None = None
    default_trial_used: bool | None = None
    default_auto_renewal: bool | None = None

    def get_connection_string(self, async_mode: bool = True) -> str:
        """Получить connection string для базы данных

        Args:
            async_mode: True для async (aiosqlite), False для sync (sqlite)
        """
        if async_mode:
            return f"sqlite+aiosqlite:///{self.path}"
        else:
            return f"sqlite:///{self.path}"


class RedisConfig(Struct):
    url: str | None = None
    decode_responses: bool | None = None
    default_ttl: int | None = None


class RateLimitConfig(Struct):
    window: int | None = None
    max_requests: int | None = None


class CORSConfig(Struct):
    allow_origins: tuple | None = None
    allow_methods: tuple | None = None
    allow_headers: tuple | None = None


class LoggingConfig(Struct):
    level: str | None = None
    format: str | None = "%(asctime)s %(levelname)s %(name)s %(message)s"
    file: str | None = None


class SecurityConfig(Struct):
    hash_algorithm: str | None = None
    hmac_digest: str | None = None


class ExtensionLinksConfig(Struct):
    chrome_url: str | None = None
    firefox_url: str | None = None
    edge_url: str | None = None


class APIConfig(BaseConfig):
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    jwt: JWTConfig = field(default_factory=JWTConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    cors: CORSConfig = field(default_factory=CORSConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    extension_links: ExtensionLinksConfig = field(default_factory=ExtensionLinksConfig)


# Загружаем конфиг из YAML/ENV/CLI (см. config-lib-msgspec)
config = APIConfig.load()
print(config)
