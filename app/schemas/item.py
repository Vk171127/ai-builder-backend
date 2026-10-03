"""Item schemas for API request/response validation."""

from typing import Optional
from pydantic import BaseModel, Field


class ItemBase(BaseModel):
    """Base item schema with common attributes."""

    name: str = Field(..., min_length=1, max_length=100, description="Item name")
    description: Optional[str] = Field(
        None, max_length=500, description="Item description"
    )


class ItemCreate(ItemBase):
    """Schema for creating a new item."""

    pass


class ItemUpdate(BaseModel):
    """Schema for updating an existing item."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class ItemResponse(ItemBase):
    """Schema for item response."""

    id: str = Field(..., description="Unique item identifier")

    model_config = {"from_attributes": True}


class ItemListResponse(BaseModel):
    """Schema for list of items response."""

    items: list[ItemResponse]
    total: int
