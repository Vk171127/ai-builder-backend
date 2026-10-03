"""Item service for business logic."""

import uuid
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemUpdate


class ItemService:
    """Service for managing items."""

    def __init__(self) -> None:
        """Initialize with in-memory storage (replace with database)."""
        self._items: dict[str, Item] = {}

    async def create_item(self, item_data: ItemCreate) -> Item:
        """Create a new item."""
        item_id = str(uuid.uuid4())
        item = Item(
            id=item_id, name=item_data.name, description=item_data.description
        )
        self._items[item_id] = item
        return item

    async def get_item(self, item_id: str) -> Item | None:
        """Get item by ID."""
        return self._items.get(item_id)

    async def get_items(self, skip: int = 0, limit: int = 100) -> list[Item]:
        """Get list of items with pagination."""
        items = list(self._items.values())
        return items[skip : skip + limit]

    async def update_item(
        self, item_id: str, item_data: ItemUpdate
    ) -> Item | None:
        """Update an existing item."""
        item = self._items.get(item_id)
        if not item:
            return None

        if item_data.name is not None:
            item.name = item_data.name
        if item_data.description is not None:
            item.description = item_data.description

        return item

    async def delete_item(self, item_id: str) -> bool:
        """Delete an item."""
        if item_id in self._items:
            del self._items[item_id]
            return True
        return False

    async def count_items(self) -> int:
        """Get total count of items."""
        return len(self._items)


# Singleton instance
item_service = ItemService()
