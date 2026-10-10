from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_outcome_endpoint() -> None:
    response = client.post(
        "/v1/outcome",
        json={"decision_id": "d1", "confirmed_scam": True, "feedback": "blocked"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
