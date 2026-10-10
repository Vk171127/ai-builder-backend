from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_analyse_endpoint() -> None:
    response = client.post("/v1/analyse", json={"session_id": "s1", "events": []})
    assert response.status_code == 200
    body = response.json()
    assert "decision" in body
    assert body["decision"]["session_id"] == "s1"
