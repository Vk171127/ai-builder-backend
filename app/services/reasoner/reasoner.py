"""Async reasoner client stub (Gemini off hot path)."""

from app.models.decision import ReasonerResult


async def run_reasoner(summary: str) -> ReasonerResult:
    _ = summary
    return ReasonerResult(explanation="Reasoner disabled on hot path", confidence_x100=50)
