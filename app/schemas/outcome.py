"""Outcome schema definitions."""

from pydantic import BaseModel, model_validator


class Outcome(BaseModel):
    decision_id: str
    session_id: str
    label: str
    source: str
    ts: int

    @model_validator(mode="before")
    @classmethod
    def _legacy_compat(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        if "label" not in value:
            confirmed = value.get("confirmed_scam")
            if confirmed is True:
                value["label"] = "scam"
            elif confirmed is False:
                value["label"] = "benign"
            else:
                value["label"] = "unknown"
        value.setdefault("session_id", "unknown")
        value.setdefault("source", "api")
        value.setdefault("ts", 0)
        return value
