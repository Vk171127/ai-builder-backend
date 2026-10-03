"""Tests for item endpoints."""

import pytest
from fastapi.testclient import TestClient


def test_create_item(client: TestClient) -> None:
    """Test creating a new item."""
    item_data = {"name": "Test Item", "description": "Test Description"}
    response = client.post("/api/v1/items", json=item_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == item_data["name"]
    assert data["description"] == item_data["description"]
    assert "id" in data


def test_create_item_without_description(client: TestClient) -> None:
    """Test creating an item without description."""
    item_data = {"name": "Test Item"}
    response = client.post("/api/v1/items", json=item_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == item_data["name"]
    assert data["description"] is None


def test_create_item_invalid_data(client: TestClient) -> None:
    """Test creating an item with invalid data."""
    item_data = {"name": ""}  # Empty name should fail
    response = client.post("/api/v1/items", json=item_data)
    assert response.status_code == 422


def test_get_items(client: TestClient) -> None:
    """Test getting list of items."""
    # Create some items first
    client.post("/api/v1/items", json={"name": "Item 1"})
    client.post("/api/v1/items", json={"name": "Item 2"})

    response = client.get("/api/v1/items")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) >= 2
    assert data["total"] >= 2


def test_get_items_with_pagination(client: TestClient) -> None:
    """Test getting items with pagination."""
    # Create items
    for i in range(5):
        client.post("/api/v1/items", json={"name": f"Item {i}"})

    # Test skip and limit
    response = client.get("/api/v1/items?skip=2&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2


def test_get_item_by_id(client: TestClient) -> None:
    """Test getting a specific item by ID."""
    # Create an item
    create_response = client.post(
        "/api/v1/items", json={"name": "Test Item", "description": "Test"}
    )
    item_id = create_response.json()["id"]

    # Get the item
    response = client.get(f"/api/v1/items/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == item_id
    assert data["name"] == "Test Item"


def test_get_item_not_found(client: TestClient) -> None:
    """Test getting a non-existent item."""
    response = client.get("/api/v1/items/nonexistent-id")
    assert response.status_code == 404


def test_update_item(client: TestClient) -> None:
    """Test updating an existing item."""
    # Create an item
    create_response = client.post(
        "/api/v1/items", json={"name": "Original Name"}
    )
    item_id = create_response.json()["id"]

    # Update the item
    update_data = {"name": "Updated Name", "description": "New Description"}
    response = client.put(f"/api/v1/items/{item_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "New Description"


def test_update_item_partial(client: TestClient) -> None:
    """Test partially updating an item."""
    # Create an item
    create_response = client.post(
        "/api/v1/items",
        json={"name": "Original Name", "description": "Original Description"},
    )
    item_id = create_response.json()["id"]

    # Update only the name
    response = client.put(f"/api/v1/items/{item_id}", json={"name": "New Name"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["description"] == "Original Description"


def test_update_item_not_found(client: TestClient) -> None:
    """Test updating a non-existent item."""
    response = client.put(
        "/api/v1/items/nonexistent-id", json={"name": "Updated"}
    )
    assert response.status_code == 404


def test_delete_item(client: TestClient) -> None:
    """Test deleting an item."""
    # Create an item
    create_response = client.post("/api/v1/items", json={"name": "To Delete"})
    item_id = create_response.json()["id"]

    # Delete the item
    response = client.delete(f"/api/v1/items/{item_id}")
    assert response.status_code == 204

    # Verify it's deleted
    get_response = client.get(f"/api/v1/items/{item_id}")
    assert get_response.status_code == 404


def test_delete_item_not_found(client: TestClient) -> None:
    """Test deleting a non-existent item."""
    response = client.delete("/api/v1/items/nonexistent-id")
    assert response.status_code == 404
