"""Patterns endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["Patterns"])


@router.get("/patterns")
async def get_patterns() -> dict[str, list[str]]:
    """List currently known scam pattern families."""
    return {
        "patterns": [
            "impersonation",
            "investment",
            "romance",
            "invoice_fraud",
        ]
    }
