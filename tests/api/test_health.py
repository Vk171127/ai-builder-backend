from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_healthz() -> None:
    response = client.get("/v1/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_readyz() -> None:
    response = client.get("/v1/readyz")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
