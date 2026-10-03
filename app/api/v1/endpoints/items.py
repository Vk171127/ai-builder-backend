"""Item endpoints."""

from typing import List
from fastapi import APIRouter, HTTPException, status, Query
from app.schemas.item import (
    ItemCreate,
    ItemResponse,
    ItemUpdate,
    ItemListResponse,
)
from app.services.item_service import item_service

router = APIRouter()


@router.post(
    "/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Items"],
)
async def create_item(item_data: ItemCreate) -> ItemResponse:
    """
    Create a new item.

    Args:
        item_data: Item creation data

    Returns:
        Created item
    """
    item = await item_service.create_item(item_data)
    return ItemResponse(
        id=item.id, name=item.name, description=item.description
    )


@router.get("/items", response_model=ItemListResponse, tags=["Items"])
async def get_items(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of items to return"),
) -> ItemListResponse:
    """
    Get list of items with pagination.

    Args:
        skip: Number of items to skip
        limit: Maximum number of items to return

    Returns:
        List of items and total count
    """
    items = await item_service.get_items(skip=skip, limit=limit)
    total = await item_service.count_items()

    return ItemListResponse(
        items=[
            ItemResponse(id=item.id, name=item.name, description=item.description)
            for item in items
        ],
        total=total,
    )


@router.get("/items/{item_id}", response_model=ItemResponse, tags=["Items"])
async def get_item(item_id: str) -> ItemResponse:
    """
    Get item by ID.

    Args:
        item_id: Item identifier

    Returns:
        Item details

    Raises:
        HTTPException: If item not found
    """
    item = await item_service.get_item(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found",
        )

    return ItemResponse(
        id=item.id, name=item.name, description=item.description
    )


@router.put("/items/{item_id}", response_model=ItemResponse, tags=["Items"])
async def update_item(item_id: str, item_data: ItemUpdate) -> ItemResponse:
    """
    Update an existing item.

    Args:
        item_id: Item identifier
        item_data: Item update data

    Returns:
        Updated item

    Raises:
        HTTPException: If item not found
    """
    item = await item_service.update_item(item_id, item_data)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found",
        )

    return ItemResponse(
        id=item.id, name=item.name, description=item.description
    )


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Items"],
)
async def delete_item(item_id: str) -> None:
    """
    Delete an item.

    Args:
        item_id: Item identifier

    Raises:
        HTTPException: If item not found
    """
    deleted = await item_service.delete_item(item_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found",
        )
