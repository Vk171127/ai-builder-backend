"""BigQuery adapter for decision and outcome storage."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from functools import lru_cache

from google.cloud import bigquery

from app.core.config import settings


DECISION_JSON_COLUMNS = ("top_signals", "rule_hits", "classifier_probs")


def _iso(ts_ms: int | None = None) -> str:
    when = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc) if ts_ms else datetime.now(timezone.utc)
    return when.isoformat()


def decision_row(payload: dict[str, object]) -> dict[str, object]:
    """Shape a decision payload to the `decisions` table schema (JSON columns as strings)."""
    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    reasoner = decision.get("reasoner") or {}
    confidence = reasoner.get("confidence_x100")
    row: dict[str, object] = {
        "decision_id": payload["decision_id"],
        "session_id": payload["session_id"],
        "action": payload.get("action"),
        "risk": payload.get("risk"),
        "scam_type": payload.get("scam_type"),
        "stage": payload.get("stage"),
        "confidence": confidence / 100 if isinstance(confidence, (int, float)) else None,
        "novelty_score": payload.get("novelty_score"),
        "latency_ms": payload.get("latency_ms"),
        "policy_version": payload.get("policy_version"),
        "created_ts": _iso(),
    }
    for col in DECISION_JSON_COLUMNS:
        value = payload.get(col)
        row[col] = json.dumps(value) if value is not None else None
    return row


def outcome_row(outcome: dict[str, object]) -> dict[str, object]:
    ts = outcome.get("ts")
    return {
        "decision_id": outcome["decision_id"],
        "session_id": outcome.get("session_id"),
        "label": outcome.get("label"),
        "source": outcome.get("source"),
        "ts": _iso(ts if isinstance(ts, int) and ts > 0 else None),
    }


class BigQueryAdapter:
    def __init__(self) -> None:
        self._client = bigquery.Client(project=settings.gcp_project or None)

    def _table(self, name: str) -> str:
        return f"{self._client.project}.{settings.bigquery_dataset}.{name}"

    def _insert(self, table: str, row: dict[str, object]) -> None:
        errors = self._client.insert_rows_json(self._table(table), [row])
        if errors:
            raise RuntimeError(f"bigquery insert into {table} failed: {errors}")

    def _query_decision(self, decision_id: str) -> dict[str, object] | None:
        job = self._client.query(
            f"SELECT * FROM `{self._table('decisions')}` "
            "WHERE decision_id = @decision_id ORDER BY latency_ms DESC LIMIT 1",
            job_config=bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("decision_id", "STRING", decision_id)]
            ),
        )
        rows = list(job.result())
        if not rows:
            return None
        row = dict(rows[0].items())
        for col in DECISION_JSON_COLUMNS:
            if isinstance(row.get(col), str):
                row[col] = json.loads(row[col])
        return row

    async def write_decision(self, payload: dict[str, object]) -> None:
        await asyncio.to_thread(self._insert, "decisions", decision_row(payload))

    async def write_outcome(self, outcome: dict[str, object]) -> None:
        await asyncio.to_thread(self._insert, "outcomes", outcome_row(outcome))

    async def get_decision(self, decision_id: str) -> dict[str, object] | None:
        return await asyncio.to_thread(self._query_decision, decision_id)


@lru_cache(maxsize=1)
def get_bigquery_adapter() -> BigQueryAdapter:
    return BigQueryAdapter()
