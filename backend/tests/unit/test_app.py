from fastapi.testclient import TestClient

from scholarroute.entrypoints.api.app import create_app


def test_application_starts_and_exposes_openapi() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "ScholarRoute API"


def test_liveness_health_endpoint() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health", headers={"X-Request-ID": "test-request"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request"
    assert response.json() == {
        "status": "ok",
        "service": "ScholarRoute API",
        "environment": "development",
        "database": None,
    }
