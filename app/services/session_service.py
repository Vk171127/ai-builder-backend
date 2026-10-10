"""Session window persistence abstraction."""

from app.models.signal import SignalEvent


class SessionService:
    """Load and write session windows.

    Redis-backed implementation can be introduced behind this interface.
    """

    async def load(self, session_id: str) -> list[SignalEvent]:
        _ = session_id
        return []

    async def write(self, session_id: str, events: list[SignalEvent]) -> None:
        _ = (session_id, events)
