"""Item model (example)."""

from typing import Optional


class Item:
    """Example item model - replace with actual database model."""

    def __init__(self, id: str, name: str, description: Optional[str] = None):
        self.id = id
        self.name = name
        self.description = description
