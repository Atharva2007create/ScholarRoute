from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SCHOLARROUTE_",
        case_sensitive=False,
        extra="ignore",
    )

    application_name: str = "ScholarRoute API"
    environment: Environment = Environment.DEVELOPMENT
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://scholarroute:scholarroute@localhost:5432/scholarroute"
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    database_pool_timeout_seconds: int = Field(default=30, ge=1, le=120)
    database_connect_timeout_seconds: int = Field(default=5, ge=1, le=60)
    cors_allowed_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )
    api_default_page_size: int = Field(default=20, ge=1, le=100)
    api_max_page_size: int = Field(default=100, ge=1, le=200)


@lru_cache
def get_settings() -> Settings:
    return Settings()
