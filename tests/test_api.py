"""
Tests for the FastAPI application.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_db_service():
    """Mock database service."""
    with patch('api.main.db_service') as mock:
        yield mock


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "version" in data
    assert "database_status" in data


def test_books_endpoint_requires_auth(client):
    """Test that books endpoint requires authentication."""
    response = client.get("/books")
    assert response.status_code == 401


def test_books_endpoint_with_auth(client, mock_db_service):
    """Test books endpoint with authentication."""
    # Mock the database service
    mock_db_service.get_books.return_value = {
        "books": [],
        "total": 0,
        "page": 1,
        "per_page": 20,
        "total_pages": 0,
        "has_next": False,
        "has_prev": False
    }
    
    # Mock API key validation
    with patch('api.auth.verify_api_key', return_value="test_api_key"):
        response = client.get("/books", headers={"Authorization": "Bearer test_api_key"})
        assert response.status_code == 200


def test_books_endpoint_with_query_params(client, mock_db_service):
    """Test books endpoint with query parameters."""
    mock_db_service.get_books.return_value = {
        "books": [],
        "total": 0,
        "page": 1,
        "per_page": 10,
        "total_pages": 0,
        "has_next": False,
        "has_prev": False
    }
    
    with patch('api.auth.verify_api_key', return_value="test_api_key"):
        response = client.get(
            "/books?category=Fiction&min_price=10&max_price=50&rating=4&page=1&per_page=10",
            headers={"Authorization": "Bearer test_api_key"}
        )
        assert response.status_code == 200


def test_book_by_id_endpoint(client, mock_db_service):
    """Test get book by ID endpoint."""
    mock_book = {
        "id": "test_id",
        "name": "Test Book",
        "description": "Test Description",
        "category": "Fiction",
        "price_including_tax": 19.99,
        "price_excluding_tax": 18.99,
        "availability": "In stock",
        "rating": 4,
        "number_of_reviews": 100,
        "image_url": "https://example.com/image.jpg",
        "source_url": "https://example.com/book",
        "created_at": "2025-09-21T10:00:00Z",
        "updated_at": "2025-09-21T10:00:00Z"
    }
    
    mock_db_service.get_book_by_id.return_value = mock_book
    
    with patch('api.auth.verify_api_key', return_value="test_api_key"):
        response = client.get(
            "/books/test_id",
            headers={"Authorization": "Bearer test_api_key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Book"


def test_book_not_found(client, mock_db_service):
    """Test book not found scenario."""
    mock_db_service.get_book_by_id.return_value = None
    
    with patch('api.auth.verify_api_key', return_value="test_api_key"):
        response = client.get(
            "/books/nonexistent_id",
            headers={"Authorization": "Bearer test_api_key"}
        )
        assert response.status_code == 404


def test_changes_endpoint(client, mock_db_service):
    """Test changes endpoint."""
    mock_db_service.get_changes.return_value = {
        "changes": [],
        "total": 0,
        "page": 1,
        "per_page": 20,
        "total_pages": 0,
        "has_next": False,
        "has_prev": False
    }
    
    with patch('api.auth.verify_api_key', return_value="test_api_key"):
        response = client.get(
            "/changes",
            headers={"Authorization": "Bearer test_api_key"}
        )
        assert response.status_code == 200


def test_categories_endpoint(client, mock_db_service):
    """Test categories endpoint."""
    mock_db_service.get_categories.return_value = ["Fiction", "Non-Fiction", "Science"]
    
    with patch('api.auth.verify_api_key', return_value="test_api_key"):
        response = client.get(
            "/books/categories",
            headers={"Authorization": "Bearer test_api_key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) == 3


def test_stats_endpoint(client, mock_db_service):
    """Test stats endpoint."""
    mock_stats = {
        "total_books": 1000,
        "total_changes": 500,
        "recent_changes_24h": 50,
        "total_categories": 10,
        "categories": ["Fiction", "Non-Fiction"]
    }
    
    mock_db_service.get_stats.return_value = mock_stats
    
    with patch('api.auth.verify_api_key', return_value="test_api_key"):
        response = client.get(
            "/stats",
            headers={"Authorization": "Bearer test_api_key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_books"] == 1000


def test_rate_limit_headers(client, mock_db_service):
    """Test that rate limit headers are included in responses."""
    mock_db_service.get_books.return_value = {
        "books": [],
        "total": 0,
        "page": 1,
        "per_page": 20,
        "total_pages": 0,
        "has_next": False,
        "has_prev": False
    }
    
    with patch('api.auth.verify_api_key', return_value="test_api_key"):
        with patch('api.auth.get_rate_limit_headers', return_value={
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Remaining": "99",
            "X-RateLimit-Reset": "1234567890"
        }):
            response = client.get(
                "/books",
                headers={"Authorization": "Bearer test_api_key"}
            )
            assert response.status_code == 200
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers
