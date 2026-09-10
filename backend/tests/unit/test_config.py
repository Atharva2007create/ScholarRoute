import pytest
from pydantic import ValidationError

from scholarroute.config import Environment, Settings


def test_settings_load_explicit_values_without_env_file() -> None:
    settings = Settings(
        _env_file=None,
        environment=Environment.TESTING,
        database_url="postgresql+psycopg://user:pass@localhost/db_test",
        database_pool_size=3,
    )

    assert settings.environment is Environment.TESTING
    assert settings.database_pool_size == 3
    assert settings.database_url.endswith("/db_test")


def test_settings_reject_invalid_pool_size() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_pool_size=0)


def test_phase8_settings_support_safe_unprefixed_environment_names() -> None:
    settings = Settings(
        _env_file=None,
        GEMINI_API_KEY="server-only-test-value",
        GEMINI_MODEL="gemini-2.5-flash",
        AI_ENABLED=True,
        AI_TIMEOUT_SECONDS=12,
        AI_MAX_RETRIES=1,
    )

    assert settings.ai_enabled is True
    assert settings.gemini_model == "gemini-2.5-flash"
    assert settings.ai_timeout_seconds == 12
    assert settings.gemini_api_key is not None
    assert str(settings.gemini_api_key) == "**********"
