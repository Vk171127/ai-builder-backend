"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.services.item_service import item_service


@pytest.fixture(autouse=True)
def reset_item_service():
    """Reset item service state before each test for isolation."""
    item_service._items.clear()
    yield
    item_service._items.clear()


@pytest.fixture
def app():
    """Create a FastAPI application instance for testing."""
    return create_app()


@pytest.fixture
def client(app):
    """Create a test client for making requests."""
    return TestClient(app)
