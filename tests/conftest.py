"""Pytest configuration. GCP services are replaced with test doubles; nothing here ships in the app."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services import pipeline_service
from app.services.reasoner import reasoner
from app.api.v1.endpoints import analyse, outcome


class StubLookup:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    async def lookup(self, key: str) -> dict[str, object]:
        return self._payload


class RecordingAnalyses:
    def __init__(self) -> None:
        self.documents: dict[tuple[str, str], dict] = {}

    def put_document(self, collection, doc_id, data):
        self.documents[(collection, doc_id)] = data


class RecordingBigQuery:
    def __init__(self) -> None:
        self.decisions: dict[str, dict[str, object]] = {}
        self.outcomes: list[dict[str, object]] = []

    async def write_decision(self, payload: dict[str, object]) -> None:
        self.decisions[str(payload["decision_id"])] = payload

    async def write_outcome(self, outcome: dict[str, object]) -> None:
        self.outcomes.append(outcome)

    async def get_decision(self, decision_id: str) -> dict[str, object] | None:
        return self.decisions.get(decision_id)


class RecordingPubSub:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def publish_decision(self, payload: dict[str, object]) -> None:
        self.messages.append(payload)

    async def publish_outcome(self, payload: dict[str, object]) -> None:
        self.messages.append(payload)


@pytest.fixture(autouse=True)
def gcp_doubles(monkeypatch):
    bq, pubsub = RecordingBigQuery(), RecordingPubSub()
    monkeypatch.setattr(
        pipeline_service,
        "build_adapters",
        lambda: {
            "web_risk": StubLookup({"flagged": False}),
            "mule_score": StubLookup({"score": 0.21}),
            "recent_reports": StubLookup({"in_graph": False, "distance": 3}),
            "customer_profile": StubLookup({"avg_payment_minor": 220000, "usual_hour": 13}),
            "domain_age": StubLookup({"age_days": 500}),
        },
    )
    monkeypatch.setattr(pipeline_service, "get_analysis_store", lambda **_: RecordingAnalyses())
    pipeline_service.get_pipeline_service.cache_clear()
    monkeypatch.setattr(analyse, "get_bigquery_adapter", lambda: bq)
    monkeypatch.setattr(analyse, "get_pubsub_adapter", lambda: pubsub)
    monkeypatch.setattr(outcome, "get_bigquery_adapter", lambda: bq)
    monkeypatch.setattr(outcome, "get_pubsub_adapter", lambda: pubsub)
    monkeypatch.setattr(reasoner, "get_llm_adapter", lambda: None)
    yield
    pipeline_service.get_pipeline_service.cache_clear()


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)
