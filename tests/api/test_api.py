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
    mock = AsyncMock()
    with patch('api.main.db_service', mock):
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
    assert response.status_code == 403  # Changed from 401 to 403 for missing auth header


def test_books_endpoint_with_auth(client, mock_db_service):
    """Test books endpoint with authentication."""
    from api.models import BookListResponse
    
    # Mock the database service to return a proper Pydantic model
    mock_response = BookListResponse(
        books=[],
        total=0,
        page=1,
        per_page=20,
        total_pages=0,
        has_next=False,
        has_prev=False
    )
    mock_db_service.get_books.return_value = mock_response
    
    # Use the real API key from environment
    with patch('api.auth.verify_api_key', return_value="fk_wSahdItxXh5e3oooff3AVn0mXS4hG3GKM5T8XdtNLMg"):
        response = client.get("/books", headers={"Authorization": "Bearer fk_wSahdItxXh5e3oooff3AVn0mXS4hG3GKM5T8XdtNLMg"})
        assert response.status_code == 200


def test_books_endpoint_with_query_params(client, mock_db_service):
    """Test books endpoint with query parameters."""
    from api.models import BookListResponse
    
    mock_response = BookListResponse(
        books=[],
        total=0,
        page=1,
        per_page=10,
        total_pages=0,
        has_next=False,
        has_prev=False
    )
    mock_db_service.get_books.return_value = mock_response
    
    with patch('api.auth.verify_api_key', return_value="fk_wSahdItxXh5e3oooff3AVn0mXS4hG3GKM5T8XdtNLMg"):
        response = client.get(
            "/books?category=Fiction&min_price=10&max_price=50&rating=4&page=1&per_page=10",
            headers={"Authorization": "Bearer fk_wSahdItxXh5e3oooff3AVn0mXS4hG3GKM5T8XdtNLMg"}
        )
        assert response.status_code == 200


def test_book_by_id_endpoint(client, mock_db_service):
    """Test get book by ID endpoint."""
    from api.models import BookResponse
    
    mock_book = BookResponse(
        id="test_id",
        name="Test Book",
        description="Test Description",
        category="Fiction",
        price_including_tax=19.99,
        price_excluding_tax=18.99,
        availability="In stock",
        rating=4,
        number_of_reviews=100,
        image_url="https://example.com/image.jpg",
        source_url="https://example.com/book",
        created_at="2025-09-21T10:00:00Z",
        updated_at="2025-09-21T10:00:00Z"
    )
    
    mock_db_service.get_book_by_id.return_value = mock_book
    
    with patch('api.auth.verify_api_key', return_value="fk_wSahdItxXh5e3oooff3AVn0mXS4hG3GKM5T8XdtNLMg"):
        response = client.get(
            "/books/test_id",
            headers={"Authorization": "Bearer fk_wSahdItxXh5e3oooff3AVn0mXS4hG3GKM5T8XdtNLMg"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Book"


def test_book_not_found(client, mock_db_service):
    """Test book not found scenario."""
    mock_db_service.get_book_by_id.return_value = None
    
    with patch('api.auth.verify_api_key', return_value="fk_wSahdItxXh5e3oooff3AVn0mXS4hG3GKM5T8XdtNLMg"):
        response = client.get(
            "/books/nonexistent_id",
            headers={"Authorization": "Bearer fk_wSahdItxXh5e3oooff3AVn0mXS4hG3GKM5T8XdtNLMg"}
        )
        assert response.status_code == 404


def test_changes_endpoint(client, mock_db_service):
    """Test changes endpoint."""
    from api.models import ChangeListResponse
    
    mock_response = ChangeListResponse(
        changes=[],
        total=0,
        page=1,
        per_page=20,
        total_pages=0,
        has_next=False,
        has_prev=False
    )
    mock_db_service.get_changes.return_value = mock_response
    
    with patch('api.auth.verify_api_key', return_value="fk_wSahdItxXh5e3oooff3AVn0mXS4hG3GKM5T8XdtNLMg"):
        response = client.get(
            "/changes",
            headers={"Authorization": "Bearer fk_wSahdItxXh5e3oooff3AVn0mXS4hG3GKM5T8XdtNLMg"}
        )
        assert response.status_code == 200




def test_rate_limit_headers(client, mock_db_service):
    """Test that rate limit headers are included in responses."""
    from api.models import BookListResponse
    
    mock_response = BookListResponse(
        books=[],
        total=0,
        page=1,
        per_page=20,
        total_pages=0,
        has_next=False,
        has_prev=False
    )
    mock_db_service.get_books.return_value = mock_response
    
    with patch('api.auth.verify_api_key', return_value="fk_wSahdItxXh5e3oooff3AVn0mXS4hG3GKM5T8XdtNLMg"):
        with patch('api.auth.get_rate_limit_headers', return_value={
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Remaining": "99",
            "X-RateLimit-Reset": "1234567890"
        }):
            response = client.get(
                "/books",
                headers={"Authorization": "Bearer fk_wSahdItxXh5e3oooff3AVn0mXS4hG3GKM5T8XdtNLMg"}
            )
            assert response.status_code == 200
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers
