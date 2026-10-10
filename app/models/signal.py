"""Signal models for transactional behaviour streams."""

from enum import Enum

from pydantic import BaseModel


class Behaviour(str, Enum):
    normal = "normal"
    suspicious = "suspicious"
    malicious = "malicious"


class Stage(str, Enum):
    observe = "observe"
    warn = "warn"
    block = "block"


class SignalEvent(BaseModel):
    timestamp_ms: int
    signal_type: str
    value_x100: int | None = None
    behaviour: Behaviour | None = None
    metadata: dict[str, str | int | bool | None] = {}


class SignalBatch(BaseModel):
    session_id: str
    events: list[SignalEvent]
