"""Outcome feedback endpoints."""

from fastapi import APIRouter

from app.schemas.outcome import Outcome

router = APIRouter(tags=["Outcome"])


@router.post("/outcome")
async def post_outcome(outcome: Outcome) -> dict[str, str]:
    """Accept user-reported outcome labels for future tuning."""
    _ = outcome
    return {"status": "accepted"}
