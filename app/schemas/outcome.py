"""Outcome schema definitions."""

from pydantic import BaseModel


class Outcome(BaseModel):
    decision_id: str
    confirmed_scam: bool | None = None
    feedback: str | None = None
