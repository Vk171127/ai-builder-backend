"""Warmup utilities for reasoner/interventions."""

from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.models.signal import ScamType
from app.services.reasoner.reasoner import get_llm_adapter
from db.state.store import StateStore

LOGGER = logging.getLogger(__name__)


def _canonical_prompt(scam_type: ScamType) -> str:
    return (
        f"Canonical safety prompt for {scam_type.value}. "
        "Generate concise user-safe warning copy and likely stage/evidence summary."
    )


async def warmup_warning_cache(state_store: StateStore) -> None:
    adapter = get_llm_adapter() if settings.reasoner_warmup_use_llm else None
    for scam_type in ScamType:
        if scam_type in {ScamType.benign, ScamType.unknown}:
            continue
        if adapter is None:
            state_store.set(
                f"warn_cache:{scam_type.value}",
                {
                    "title": f"{scam_type.value.replace('_', ' ').title()} risk",
                    "body": "Potential scam risk detected. Please pause and verify independently.",
                    "uncertainty": "high",
                },
                ex=3600,
            )
            LOGGER.info("warmup_static_cached scam_type=%s", scam_type.value)
            continue
        try:
            result = await asyncio.wait_for(
                adapter.complete(
                    prompt=_canonical_prompt(scam_type),
                    session_locale="en",
                    timeout_ms=settings.reasoner_warmup_timeout_ms,
                ),
                timeout=max(1.0, settings.reasoner_warmup_timeout_ms / 1000 + 0.5),
            )
            if result is None:
                LOGGER.warning("warmup_failed scam_type=%s reason=empty", scam_type.value)
                if not settings.reasoner_warmup_fail_open_static:
                    continue
                body = "Potential scam risk detected. Please pause and verify independently."
                uncertainty = "high"
            else:
                body = result.user_message
                uncertainty = result.uncertainty

            state_store.set(
                f"warn_cache:{scam_type.value}",
                {
                    "title": f"{scam_type.value.replace('_', ' ').title()} risk",
                    "body": body,
                    "uncertainty": uncertainty,
                },
                ex=3600,
            )
            LOGGER.info("warmup_success scam_type=%s", scam_type.value)
        except Exception as exc:
            LOGGER.warning(
                "warmup_failed scam_type=%s error_type=%s error=%r",
                scam_type.value,
                type(exc).__name__,
                exc,
            )
            if settings.reasoner_warmup_fail_open_static:
                try:
                    state_store.set(
                        f"warn_cache:{scam_type.value}",
                        {
                            "title": f"{scam_type.value.replace('_', ' ').title()} risk",
                            "body": "Potential scam risk detected. Please pause and verify independently.",
                            "uncertainty": "high",
                        },
                        ex=3600,
                    )
                    LOGGER.info("warmup_fallback_cached scam_type=%s", scam_type.value)
                except Exception as cache_exc:
                    LOGGER.warning(
                        "warmup_fallback_cache_failed scam_type=%s error_type=%s error=%r",
                        scam_type.value,
                        type(cache_exc).__name__,
                        cache_exc,
                    )


async def periodic_warmup_loop(state_store: StateStore) -> None:
    while True:
        await warmup_warning_cache(state_store=state_store)
        await asyncio.sleep(3600)
