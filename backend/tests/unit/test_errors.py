from fastapi import APIRouter
from fastapi.testclient import TestClient

from scholarroute.entrypoints.api.app import create_app
from scholarroute.errors import ApplicationError


def test_application_errors_use_consistent_envelope() -> None:
    app = create_app()
    router = APIRouter()

    @router.get("/test-error")
    def raise_error() -> None:
        raise ApplicationError(code="TEST_ERROR", message="Expected failure", status_code=409)

    app.include_router(router)
    with TestClient(app) as client:
        response = client.get("/test-error", headers={"X-Request-ID": "error-request"})

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "TEST_ERROR",
            "message": "Expected failure",
            "fields": [],
            "request_id": "error-request",
        }
    }
