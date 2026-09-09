from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Connection, text
from sqlalchemy.exc import SQLAlchemyError

from scholarroute.config import Settings, get_settings
from scholarroute.entrypoints.api.schemas import HealthResponse
from scholarroute.infrastructure.db.session import get_engine

router = APIRouter(tags=["infrastructure"])
SettingsDependency = Annotated[Settings, Depends(get_settings)]


@router.get("/health", response_model=HealthResponse)
def liveness(settings: SettingsDependency) -> HealthResponse:
    return HealthResponse(
        service=settings.application_name,
        environment=settings.environment.value,
    )


@router.get(
    "/api/v1/health",
    response_model=HealthResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Database unavailable"}},
)
def readiness(settings: SettingsDependency) -> HealthResponse:
    try:
        connection: Connection
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DATABASE_UNAVAILABLE", "message": "Database is unavailable"},
        ) from exc

    return HealthResponse(
        service=settings.application_name,
        environment=settings.environment.value,
        database="ok",
    )
