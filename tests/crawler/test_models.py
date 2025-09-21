"""
Unit tests for Pydantic models.
Tests data validation, serialization, and edge cases.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from pydantic import ValidationError

from crawler.models import BookData, CrawlState, CrawlResult, BookAvailability, BookRating, CrawlStatus


class TestBookData:
    """Test cases for BookData model."""
    
    def test_valid_book_data(self):
        """Test creating valid book data."""
        book = BookData(
            name="Test Book",
            description="A test book description",
            category="Fiction",
            price_including_tax=Decimal("19.99"),
            price_excluding_tax=Decimal("16.66"),
            availability=BookAvailability.IN_STOCK,
            number_of_reviews=5,
            image_url="https://example.com/image.jpg",
            rating=BookRating.FOUR,
            source_url="https://example.com/book/1"
        )
        
        assert book.name == "Test Book"
        assert book.availability == BookAvailability.IN_STOCK
        assert book.rating == BookRating.FOUR
        assert book.crawl_timestamp is not None
        assert book.status == CrawlStatus.COMPLETED
    
    def test_invalid_negative_reviews(self):
        """Test validation of negative review count."""
        with pytest.raises(ValidationError) as exc_info:
            BookData(
                name="Test Book",
                description="A test book description",
                category="Fiction",
                price_including_tax=Decimal("19.99"),
                price_excluding_tax=Decimal("16.66"),
                availability=BookAvailability.IN_STOCK,
                number_of_reviews=-1,  # Invalid negative value
                image_url="https://example.com/image.jpg",
                source_url="https://example.com/book/1"
            )
        
        assert "Input should be greater than or equal to 0" in str(exc_info.value)
    
    def test_invalid_negative_price(self):
        """Test validation of negative prices."""
        with pytest.raises(ValidationError) as exc_info:
            BookData(
                name="Test Book",
                description="A test book description",
                category="Fiction",
                price_including_tax=Decimal("-19.99"),  # Invalid negative price
                price_excluding_tax=Decimal("16.66"),
                availability=BookAvailability.IN_STOCK,
                number_of_reviews=5,
                image_url="https://example.com/image.jpg",
                source_url="https://example.com/book/1"
            )
        
        assert "Price must be positive" in str(exc_info.value)
    
    def test_optional_rating(self):
        """Test that rating is optional."""
        book = BookData(
            name="Test Book",
            description="A test book description",
            category="Fiction",
            price_including_tax=Decimal("19.99"),
            price_excluding_tax=Decimal("16.66"),
            availability=BookAvailability.IN_STOCK,
            number_of_reviews=5,
            image_url="https://example.com/image.jpg",
            source_url="https://example.com/book/1"
            # rating is not provided
        )
        
        assert book.rating is None
    
    def test_json_serialization(self):
        """Test JSON serialization of book data."""
        book = BookData(
            name="Test Book",
            description="A test book description",
            category="Fiction",
            price_including_tax=Decimal("19.99"),
            price_excluding_tax=Decimal("16.66"),
            availability=BookAvailability.IN_STOCK,
            number_of_reviews=5,
            image_url="https://example.com/image.jpg",
            rating=BookRating.FOUR,
            source_url="https://example.com/book/1"
        )
        
        json_data = book.json()
        assert "Test Book" in json_data
        assert "19.99" in json_data
        assert "In stock" in json_data


class TestCrawlState:
    """Test cases for CrawlState model."""
    
    def test_default_crawl_state(self):
        """Test creating default crawl state."""
        state = CrawlState()
        
        assert state.last_processed_page == 1
        assert state.total_pages is None
        assert state.books_processed == 0
        assert state.last_processed_url is None
        assert state.crawl_start_time is not None
        assert state.last_update_time is not None
        assert state.errors == []
    
    def test_crawl_state_with_data(self):
        """Test creating crawl state with specific data."""
        start_time = datetime.utcnow()
        state = CrawlState(
            last_processed_page=5,
            total_pages=10,
            books_processed=50,
            last_processed_url="https://example.com/book/50",
            crawl_start_time=start_time,
            errors=["Test error"]
        )
        
        assert state.last_processed_page == 5
        assert state.total_pages == 10
        assert state.books_processed == 50
        assert state.last_processed_url == "https://example.com/book/50"
        assert state.crawl_start_time == start_time
        assert len(state.errors) == 1


class TestCrawlResult:
    """Test cases for CrawlResult model."""
    
    def test_successful_crawl_result(self):
        """Test creating successful crawl result."""
        start_time = datetime.utcnow()
        end_time = datetime.utcnow()
        
        result = CrawlResult(
            success=True,
            books_crawled=100,
            duration_seconds=300.5,
            start_time=start_time,
            end_time=end_time
        )
        
        assert result.success is True
        assert result.books_crawled == 100
        assert result.duration_seconds == 300.5
        assert result.errors == []
        assert result.start_time == start_time
        assert result.end_time == end_time
    
    def test_failed_crawl_result(self):
        """Test creating failed crawl result with errors."""
        start_time = datetime.utcnow()
        end_time = datetime.utcnow()
        
        result = CrawlResult(
            success=False,
            books_crawled=50,
            errors=["Connection failed", "Timeout error"],
            duration_seconds=150.0,
            start_time=start_time,
            end_time=end_time
        )
        
        assert result.success is False
        assert result.books_crawled == 50
        assert len(result.errors) == 2
        assert "Connection failed" in result.errors
        assert "Timeout error" in result.errors


class TestEnums:
    """Test cases for enum classes."""
    
    def test_book_availability_enum(self):
        """Test BookAvailability enum values."""
        assert BookAvailability.IN_STOCK == "In stock"
        assert BookAvailability.OUT_OF_STOCK == "Out of stock"
    
    def test_book_rating_enum(self):
        """Test BookRating enum values."""
        assert BookRating.ONE == 1
        assert BookRating.TWO == 2
        assert BookRating.THREE == 3
        assert BookRating.FOUR == 4
        assert BookRating.FIVE == 5
    
    def test_crawl_status_enum(self):
        """Test CrawlStatus enum values."""
        assert CrawlStatus.PENDING == "pending"
        assert CrawlStatus.IN_PROGRESS == "in_progress"
        assert CrawlStatus.COMPLETED == "completed"
        assert CrawlStatus.FAILED == "failed"
