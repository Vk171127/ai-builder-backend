"""Outcome feedback endpoints."""

import asyncio
import logging

from fastapi import APIRouter

from app.schemas.outcome import Outcome
from app.services.bigquery_adapter import get_bigquery_adapter
from app.services.pubsub_adapter import get_pubsub_adapter

LOGGER = logging.getLogger(__name__)
router = APIRouter(tags=["Outcome"])


async def write_bigquery_outcome(payload: dict[str, object]) -> None:
    try:
        await get_bigquery_adapter().write_outcome(payload)
    except Exception:
        LOGGER.exception("gcp_write_failed")


async def publish_pubsub_outcomes(payload: dict[str, object]) -> None:
    try:
        await get_pubsub_adapter().publish_outcome(payload)
    except Exception:
        LOGGER.exception("gcp_write_failed")


@router.post("/outcome")
async def post_outcome(outcome: Outcome) -> dict[str, object]:
    """Accept user-reported outcome labels for future tuning."""
    payload = outcome.model_dump()
    asyncio.create_task(write_bigquery_outcome(payload))
    asyncio.create_task(publish_pubsub_outcomes(payload))
    return {"ok": True, "status": "accepted"}
