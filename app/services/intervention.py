"""Intervention message lookup with fallback."""

from app.models.decision import Intervention


def get_intervention(stage_name: str) -> Intervention | None:
    if stage_name == "warn":
        return Intervention(code="warn_generic", message="Please verify recipient and request details")
    if stage_name == "block":
        return Intervention(code="block_generic", message="Transaction blocked due to high scam risk")
    return None
