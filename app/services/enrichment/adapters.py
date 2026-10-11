"""External enrichment lookups backed by GCP services.

web_risk uses the Web Risk API. The other lookups read BigQuery tables in
`BIGQUERY_DATASET`:

- mule_scores(account_id, score)
- account_reports(account_id, in_graph, distance)
- customer_profiles(customer_id, avg_payment_minor, usual_hour, known_payee)
- domain_registrations(domain, age_days)
"""

from __future__ import annotations

import asyncio
from typing import Protocol

from google.cloud import bigquery, webrisk_v1

from app.core.config import settings


class LookupAdapter(Protocol):
    async def lookup(self, key: str) -> dict[str, object]: ...


class WebRiskAdapter:
    def __init__(self) -> None:
        self._client = webrisk_v1.WebRiskServiceClient()

    def _search(self, uri: str) -> dict[str, object]:
        response = self._client.search_uris(
            request={
                "uri": uri,
                "threat_types": [
                    webrisk_v1.ThreatType.MALWARE,
                    webrisk_v1.ThreatType.SOCIAL_ENGINEERING,
                    webrisk_v1.ThreatType.UNWANTED_SOFTWARE,
                ],
            }
        )
        return {"flagged": bool(response.threat.threat_types)}

    async def lookup(self, key: str) -> dict[str, object]:
        return await asyncio.to_thread(self._search, key)


class BigQueryLookupAdapter:
    """Single-row lookup by key against a BigQuery table."""

    def __init__(self, table: str, key_column: str, columns: tuple[str, ...]) -> None:
        self._client = bigquery.Client(project=settings.gcp_project or None)
        self._table = f"{self._client.project}.{settings.bigquery_dataset}.{table}"
        self._key_column = key_column
        self._columns = columns

    def _query(self, key: str) -> dict[str, object]:
        job = self._client.query(
            f"SELECT {', '.join(self._columns)} FROM `{self._table}` WHERE {self._key_column} = @key LIMIT 1",
            job_config=bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("key", "STRING", key)]
            ),
        )
        rows = list(job.result())
        return dict(rows[0].items()) if rows else {}

    async def lookup(self, key: str) -> dict[str, object]:
        return await asyncio.to_thread(self._query, key)


def build_adapters() -> dict[str, LookupAdapter]:
    return {
        "web_risk": WebRiskAdapter(),
        "mule_score": BigQueryLookupAdapter("mule_scores", "account_id", ("score",)),
        "recent_reports": BigQueryLookupAdapter("account_reports", "account_id", ("in_graph", "distance")),
        "customer_profile": BigQueryLookupAdapter(
            "customer_profiles", "customer_id", ("avg_payment_minor", "usual_hour", "known_payee")
        ),
        "domain_age": BigQueryLookupAdapter("domain_registrations", "domain", ("age_days",)),
    }
