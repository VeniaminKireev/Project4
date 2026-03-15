from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Общие настройки
    app_name: str = "URL Shortener API"
    debug: bool = True
    # Настройки постгри
    database_host: str = "db"
    database_port: int = 5432
    database_name: str = "shortener"
    database_user: str = "postgres"
    database_password: str = "postgres"
    # Настройки редиса
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    # Настройки JWT
    secret_key: str = "change_me_in_production"
    access_token_expire_minutes: int = 60 * 24
    jwt_algorithm: str = "HS256"
    # Настройки короткой ссылки
    short_code_length: int = 8
    redirect_cache_ttl_seconds: int = 60 * 60
    stats_cache_ttl_seconds: int = 60
    search_cache_ttl_seconds: int = 60
    inactive_link_days: int = 30
    # Для Pydantic
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    # Асинхронный URL для SQLAlchemy
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )
    # Синхронный URL для Alembic
    @property
    def sync_database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )
    # URL для Redis
    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

# Кэш для того, чтобы при вызове get_settings() объект настроек создался один раз
@lru_cache
def get_settings() -> Settings:
    return Settings()
