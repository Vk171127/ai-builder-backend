"""Async enrichment execution runner."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.models.signal import Behaviour, SignalEvent, Source
from app.services.enrichment.router import decide_lookups
from db.state.store import StateStore, hash_key


@dataclass(slots=True)
class EnrichmentResult:
    values: dict[str, dict[str, object] | None]
    timeout_flags: dict[str, bool]
    synthetic_events: list[SignalEvent]


async def _run_one(
    name: str,
    key: str,
    adapter: object,
    timeout_ms: int,
) -> tuple[str, dict[str, object] | None, bool]:
    try:
        result = await asyncio.wait_for(adapter.lookup(key), timeout=timeout_ms / 1000)
        return name, result, False
    except Exception:
        return name, None, True


def _lookup_key(name: str, events: list[SignalEvent]) -> str:
    for event in events:
        metadata = event.metadata
        if name in {"mule_score", "recent_reports"} and isinstance(metadata.get("payee_account"), str):
            return str(metadata["payee_account"])
        if name in {"web_risk", "domain_age"} and isinstance(metadata.get("domain"), str):
            return str(metadata["domain"])
        if name == "web_risk" and isinstance(metadata.get("referrer_url"), str):
            return str(metadata["referrer_url"])
        if name == "customer_profile" and isinstance(metadata.get("customer_id"), str):
            return str(metadata["customer_id"])
    return "unknown"


async def run_enrichment(
    events: list[SignalEvent],
    state_store: StateStore | None,
    adapters: dict[str, object],
    timeout_ms: int = 80,
) -> EnrichmentResult:
    lookups = decide_lookups(events)
    tasks: list[asyncio.Task[tuple[str, dict[str, object] | None, bool]]] = []

    for lookup in lookups:
        adapter = adapters.get(lookup)
        if adapter is None:
            continue
        key = _lookup_key(lookup, events)
        tasks.append(asyncio.create_task(_run_one(lookup, key, adapter, timeout_ms)))

    values: dict[str, dict[str, object] | None] = {}
    timeout_flags: dict[str, bool] = {}

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=False)
        for lookup, payload, timed_out in results:
            values[lookup] = payload
            timeout_flags[lookup] = timed_out
            if state_store is not None:
                try:
                    lookup_key = _lookup_key(lookup, events)
                    cache_key = f"enrichment:{lookup}:{hash_key(lookup_key)}"
                    state_store.set(cache_key, payload, ex=120)
                except Exception:
                    pass

    synthetic: list[SignalEvent] = []
    base_ts = max((event.timestamp_ms for event in events), default=0)
    for index, (lookup, payload) in enumerate(values.items()):
        synthetic.append(
            SignalEvent(
                event_id=f"enrich-{lookup}-{index}",
                timestamp_ms=base_ts + index + 1,
                signal_type="server_enrichment",
                source=Source.server,
                trust=0.95,
                value_x100=95,
                behaviour=Behaviour.suspicious,
                metadata={"lookup": lookup, "timeout": timeout_flags.get(lookup, False), "present": payload is not None},
            )
        )

    return EnrichmentResult(values=values, timeout_flags=timeout_flags, synthetic_events=synthetic)
