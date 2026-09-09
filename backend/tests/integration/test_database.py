from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from scholarroute.entrypoints.api.app import create_app
from scholarroute.infrastructure.db.base import Base
from scholarroute.infrastructure.db.models import State
from scholarroute.infrastructure.db.session import get_engine, session_scope

pytestmark = pytest.mark.integration


def test_migration_schema_matches_model_metadata(migrated_database: str) -> None:
    del migrated_database
    actual = set(inspect(get_engine()).get_table_names())
    expected = set(Base.metadata.tables)

    assert actual == expected | {"alembic_version"}


def test_session_scope_commits_and_rolls_back(migrated_database: str) -> None:
    del migrated_database
    committed_code = f"TEST-{uuid4()}"
    rolled_back_code = f"TEST-{uuid4()}"

    with session_scope() as session:
        session.add(State(code=committed_code, name="Committed test state"))

    with session_scope() as session:
        assert session.scalar(select(State).where(State.code == committed_code)) is not None

    with pytest.raises(RuntimeError, match="force rollback"), session_scope() as session:
        session.add(State(code=rolled_back_code, name="Rolled back test state"))
        raise RuntimeError("force rollback")

    with session_scope() as session:
        assert session.scalar(select(State).where(State.code == rolled_back_code)) is None
        committed = session.scalar(select(State).where(State.code == committed_code))
        assert committed is not None
        session.delete(committed)


def test_readiness_health_checks_postgresql(migrated_database: str) -> None:
    del migrated_database
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["database"] == "ok"
