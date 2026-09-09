from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from scholarroute.config import get_settings
from scholarroute.infrastructure.db.session import reset_database_state


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = os.getenv(
        "SCHOLARROUTE_TEST_DATABASE_URL",
        "postgresql+psycopg://scholarroute:scholarroute@localhost:5432/scholarroute_test",
    )
    database = make_url(url).database or ""
    if not database.endswith("_test"):
        pytest.fail("Integration tests refuse to use a database without an _test suffix")

    engine = create_engine(url, connect_args={"connect_timeout": 3})
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        pytest.skip(f"Isolated PostgreSQL test database is unavailable: {exc}")
    finally:
        engine.dispose()
    return url


@pytest.fixture(scope="session")
def migrated_database(test_database_url: str) -> Iterator[str]:
    old_url = os.environ.get("SCHOLARROUTE_DATABASE_URL")
    os.environ["SCHOLARROUTE_DATABASE_URL"] = test_database_url
    get_settings.cache_clear()
    reset_database_state()

    config = Config("alembic.ini")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield test_database_url
    command.downgrade(config, "base")

    if old_url is None:
        os.environ.pop("SCHOLARROUTE_DATABASE_URL", None)
    else:
        os.environ["SCHOLARROUTE_DATABASE_URL"] = old_url
    get_settings.cache_clear()
    reset_database_state()
