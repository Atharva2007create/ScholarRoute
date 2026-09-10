from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr
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
    gemini_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "SCHOLARROUTE_GEMINI_API_KEY"),
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        validation_alias=AliasChoices("GEMINI_MODEL", "SCHOLARROUTE_GEMINI_MODEL"),
    )
    ai_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("AI_ENABLED", "SCHOLARROUTE_AI_ENABLED"),
    )
    ai_timeout_seconds: int = Field(
        default=15,
        ge=1,
        le=60,
        validation_alias=AliasChoices("AI_TIMEOUT_SECONDS", "SCHOLARROUTE_AI_TIMEOUT_SECONDS"),
    )
    ai_max_retries: int = Field(
        default=1,
        ge=0,
        le=3,
        validation_alias=AliasChoices("AI_MAX_RETRIES", "SCHOLARROUTE_AI_MAX_RETRIES"),
    )
    ai_max_output_tokens: int = Field(
        default=500,
        ge=100,
        le=2000,
        validation_alias=AliasChoices("AI_MAX_OUTPUT_TOKENS", "SCHOLARROUTE_AI_MAX_OUTPUT_TOKENS"),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
