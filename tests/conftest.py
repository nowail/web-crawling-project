"""
Pytest configuration and shared fixtures.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock
from crawler.database import MongoDBManager


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_mongodb_manager():
    """Create a mock MongoDB manager for testing."""
    manager = AsyncMock(spec=MongoDBManager)
    manager.insert_book.return_value = True
    manager.insert_books_batch.return_value = {"success": 5, "failed": 0, "duplicates": 0}
    manager.get_book_by_url.return_value = None
    manager.get_books_count.return_value = 100
    manager.get_categories.return_value = ["Fiction", "Poetry", "Mystery"]
    return manager


@pytest.fixture
def sample_book_data():
    """Create sample book data for testing."""
    from crawler.models import BookData, BookAvailability, BookRating
    from decimal import Decimal
    
    return BookData(
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


@pytest.fixture
def sample_html_content():
    """Sample HTML content for testing."""
    return """
    <html>
        <head><title>Test Book</title></head>
        <body>
            <h1>A Light in the Attic</h1>
            <div id="product_description">
                <p>It's hard to imagine a world without A Light in the Attic...</p>
            </div>
            <ul class="breadcrumb">
                <li><a href="/">Home</a></li>
                <li><a href="/catalogue/category/books/poetry_23/index.html">Poetry</a></li>
            </ul>
            <p class="price_color">£51.77</p>
            <table class="table">
                <tr><td>Price (excl. tax)</td><td>£51.77</td></tr>
                <tr><td>Price (incl. tax)</td><td>£51.77</td></tr>
                <tr><td>Number of reviews</td><td>22</td></tr>
            </table>
            <p class="availability">In stock (22 available)</p>
            <div class="item active">
                <img src="../../media/cache/2c/da/2cdad67c44b002e7ead0cc35693c0e8.jpg">
            </div>
            <p class="star-rating Three"></p>
        </body>
    </html>
    """


@pytest.fixture
def sample_catalogue_page():
    """Sample catalogue page HTML for testing."""
    return """
    <html>
        <body>
            <div class="row">
                <article class="product_pod">
                    <div class="image_container">
                        <a href="catalogue/a-light-in-the-attic_1000/index.html">
                            <img src="media/cache/2c/da/2cdad67c44b002e7ead0cc35693c0e8.jpg">
                        </a>
                    </div>
                    <h3><a href="catalogue/a-light-in-the-attic_1000/index.html" title="A Light in the Attic">A Light in the Attic</a></h3>
                    <div class="product_price">
                        <p class="price_color">£51.77</p>
                    </div>
                </article>
            </div>
        </body>
    </html>
    """


# Scheduler-specific fixtures
@pytest.fixture
def scheduler_config():
    """Create scheduler configuration for testing."""
    from scheduler.models import SchedulerConfig
    return SchedulerConfig(
        schedule_hour=14,
        schedule_minute=30,
        timezone="UTC",
        enable_change_detection=True,
        generate_daily_reports=True,
        batch_size=100
    )


@pytest.fixture
def alert_config():
    """Create alert configuration for testing."""
    from scheduler.models import AlertConfig, ChangeSeverity
    return AlertConfig(
        enabled=True,
        log_enabled=True,
        min_severity_for_log=ChangeSeverity.LOW,
        max_alerts_per_hour=10,
        alert_cooldown_minutes=30
    )


@pytest.fixture
def sample_change_log():
    """Create sample change log for testing."""
    from scheduler.models import ChangeLog, ChangeType, ChangeSeverity
    from decimal import Decimal
    
    return ChangeLog(
        change_id="test-change-123",
        book_id="book_123",
        source_url="https://example.com/book/123",
        change_type=ChangeType.PRICE_CHANGE,
        severity=ChangeSeverity.HIGH,
        old_value=Decimal("19.99"),
        new_value=Decimal("24.99"),
        field_name="price_including_tax",
        change_summary="Price increased from $19.99 to $24.99",
        confidence_score=1.0
    )


@pytest.fixture
def sample_content_fingerprint():
    """Create sample content fingerprint for testing."""
    from scheduler.models import ContentFingerprint
    
    return ContentFingerprint(
        book_id="book_123",
        source_url="https://example.com/book/123",
        content_hash="a" * 64,  # SHA-256 length
        price_hash="b" * 64,
        availability_hash="c" * 64,
        metadata_hash="d" * 64
    )


@pytest.fixture
def sample_change_detection_result():
    """Create sample change detection result for testing."""
    from scheduler.models import ChangeDetectionResult, ChangeType, ChangeSeverity
    
    return ChangeDetectionResult(
        detection_id="detection-123",
        total_books_checked=1000,
        changes_detected=25,
        new_books=5,
        updated_books=15,
        removed_books=5,
        detection_duration_seconds=120.5,
        changes_by_type={
            ChangeType.PRICE_CHANGE: 10,
            ChangeType.NEW_BOOK: 5,
            ChangeType.AVAILABILITY_CHANGE: 10
        },
        changes_by_severity={
            ChangeSeverity.HIGH: 5,
            ChangeSeverity.MEDIUM: 15,
            ChangeSeverity.LOW: 5
        },
        success=True
    )


@pytest.fixture
def mock_scheduler_db_manager():
    """Create mock database manager for scheduler testing."""
    manager = AsyncMock(spec=MongoDBManager)
    manager.connect = AsyncMock()
    manager.collection = AsyncMock()
    manager.database = AsyncMock()
    manager.database.list_collection_names = AsyncMock(return_value=[])
    manager.database.create_collection = AsyncMock()
    manager.database.fingerprints = AsyncMock()
    manager.database.change_logs = AsyncMock()
    manager.database.detection_results = AsyncMock()
    manager.database.daily_reports = AsyncMock()
    return manager
