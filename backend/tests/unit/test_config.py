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
