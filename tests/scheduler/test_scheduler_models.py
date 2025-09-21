"""
Test cases specifically for scheduler models and data structures.
Tests edge cases, validation, and serialization for scheduler-specific models.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from pydantic import ValidationError
from pydantic.networks import HttpUrl

from scheduler.models import (
    ChangeType, ChangeSeverity, ContentFingerprint, ChangeLog,
    ChangeDetectionResult, AlertConfig, SchedulerConfig, DailyReport
)


class TestChangeType:
    """Test cases for ChangeType enum."""
    
    def test_all_change_types(self):
        """Test all change type values."""
        assert ChangeType.NEW_BOOK == "new_book"
        assert ChangeType.PRICE_CHANGE == "price_change"
        assert ChangeType.AVAILABILITY_CHANGE == "availability_change"
        assert ChangeType.DESCRIPTION_CHANGE == "description_change"
        assert ChangeType.IMAGE_CHANGE == "image_change"
        assert ChangeType.RATING_CHANGE == "rating_change"
        assert ChangeType.REVIEWS_CHANGE == "reviews_change"
        assert ChangeType.CATEGORY_CHANGE == "category_change"
        assert ChangeType.BOOK_REMOVED == "book_removed"
    
    def test_change_type_validation(self):
        """Test change type validation."""
        # Valid change type
        assert ChangeType("new_book") == ChangeType.NEW_BOOK
        
        # Invalid change type should raise ValueError
        with pytest.raises(ValueError):
            ChangeType("invalid_type")


class TestChangeSeverity:
    """Test cases for ChangeSeverity enum."""
    
    def test_all_severity_levels(self):
        """Test all severity level values."""
        assert ChangeSeverity.LOW == "low"
        assert ChangeSeverity.MEDIUM == "medium"
        assert ChangeSeverity.HIGH == "high"
        assert ChangeSeverity.CRITICAL == "critical"
    
    def test_severity_ordering(self):
        """Test severity level ordering for filtering."""
        severities = [ChangeSeverity.LOW, ChangeSeverity.MEDIUM, ChangeSeverity.HIGH, ChangeSeverity.CRITICAL]
        
        # Test that they can be ordered (alphabetically by value)
        sorted_severities = sorted(severities, key=lambda x: x.value)
        expected_order = [ChangeSeverity.CRITICAL, ChangeSeverity.HIGH, ChangeSeverity.LOW, ChangeSeverity.MEDIUM]
        assert sorted_severities == expected_order


class TestContentFingerprint:
    """Test cases for ContentFingerprint model."""
    
    def test_valid_fingerprint_creation(self):
        """Test creating a valid content fingerprint."""
        fingerprint = ContentFingerprint(
            book_id="book_123",
            source_url="https://example.com/book/123",
            content_hash="a" * 64,  # SHA-256 length
            price_hash="b" * 64,
            availability_hash="c" * 64,
            metadata_hash="d" * 64
        )
        
        assert fingerprint.book_id == "book_123"
        assert str(fingerprint.source_url) == "https://example.com/book/123"
        assert len(fingerprint.content_hash) == 64
        assert fingerprint.created_at is not None
        assert fingerprint.updated_at is not None
    
    def test_fingerprint_with_custom_timestamps(self):
        """Test fingerprint with custom timestamps."""
        now = datetime.utcnow()
        fingerprint = ContentFingerprint(
            book_id="book_123",
            source_url="https://example.com/book/123",
            content_hash="a" * 64,
            price_hash="b" * 64,
            availability_hash="c" * 64,
            metadata_hash="d" * 64,
            created_at=now,
            updated_at=now
        )
        
        assert fingerprint.created_at == now
        assert fingerprint.updated_at == now
    
    def test_fingerprint_serialization(self):
        """Test fingerprint serialization to dict."""
        fingerprint = ContentFingerprint(
            book_id="book_123",
            source_url="https://example.com/book/123",
            content_hash="a" * 64,
            price_hash="b" * 64,
            availability_hash="c" * 64,
            metadata_hash="d" * 64
        )
        
        data = fingerprint.model_dump()
        
        assert data["book_id"] == "book_123"
        assert str(data["source_url"]) == "https://example.com/book/123"
        assert data["content_hash"] == "a" * 64
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_fingerprint_deserialization(self):
        """Test fingerprint deserialization from dict."""
        data = {
            "book_id": "book_123",
            "source_url": "https://example.com/book/123",
            "content_hash": "a" * 64,
            "price_hash": "b" * 64,
            "availability_hash": "c" * 64,
            "metadata_hash": "d" * 64,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        fingerprint = ContentFingerprint.model_validate(data)
        
        assert fingerprint.book_id == "book_123"
        assert str(fingerprint.source_url) == "https://example.com/book/123"


class TestChangeLog:
    """Test cases for ChangeLog model."""
    
    def test_valid_change_log_creation(self):
        """Test creating a valid change log."""
        change_log = ChangeLog(
            change_id="change_123",
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
        
        assert change_log.change_id == "change_123"
        assert change_log.book_id == "book_123"
        assert change_log.change_type == ChangeType.PRICE_CHANGE
        assert change_log.severity == ChangeSeverity.HIGH
        assert change_log.old_value == Decimal("19.99")
        assert change_log.new_value == Decimal("24.99")
        assert change_log.confidence_score == 1.0
        assert change_log.detected_at is not None
        assert change_log.processed is False
    
    def test_change_log_new_book(self):
        """Test change log for new book discovery."""
        change_log = ChangeLog(
            change_id="new_book_123",
            book_id="book_456",
            source_url="https://example.com/book/456",
            change_type=ChangeType.NEW_BOOK,
            severity=ChangeSeverity.MEDIUM,
            old_value=None,
            new_value="New Book Title",
            field_name="name",
            change_summary="New book discovered: New Book Title"
        )
        
        assert change_log.old_value is None
        assert change_log.new_value == "New Book Title"
        assert change_log.change_type == ChangeType.NEW_BOOK
    
    def test_change_log_book_removal(self):
        """Test change log for book removal."""
        change_log = ChangeLog(
            change_id="removed_book_123",
            book_id="book_789",
            source_url="https://example.com/book/789",
            change_type=ChangeType.BOOK_REMOVED,
            severity=ChangeSeverity.HIGH,
            old_value="Removed Book Title",
            new_value=None,
            field_name="name",
            change_summary="Book removed: Removed Book Title"
        )
        
        assert change_log.old_value == "Removed Book Title"
        assert change_log.new_value is None
        assert change_log.change_type == ChangeType.BOOK_REMOVED
    
    def test_change_log_confidence_score_validation(self):
        """Test confidence score validation."""
        # Valid confidence scores
        valid_scores = [0.0, 0.5, 1.0]
        for score in valid_scores:
            change_log = ChangeLog(
                change_id="test_123",
                book_id="book_123",
                source_url="https://example.com/book/123",
                change_type=ChangeType.PRICE_CHANGE,
                severity=ChangeSeverity.HIGH,
                change_summary="Test change",
                confidence_score=score
            )
            assert change_log.confidence_score == score
        
        # Invalid confidence scores
        invalid_scores = [-0.1, 1.1, 2.0]
        for score in invalid_scores:
            with pytest.raises(ValidationError):
                ChangeLog(
                    change_id="test_123",
                    book_id="book_123",
                    source_url="https://example.com/book/123",
                    change_type=ChangeType.PRICE_CHANGE,
                    severity=ChangeSeverity.HIGH,
                    change_summary="Test change",
                    confidence_score=score
                )
    
    def test_change_log_serialization_with_decimal(self):
        """Test change log serialization with Decimal values."""
        change_log = ChangeLog(
            change_id="test_123",
            book_id="book_123",
            source_url="https://example.com/book/123",
            change_type=ChangeType.PRICE_CHANGE,
            severity=ChangeSeverity.HIGH,
            old_value=Decimal("19.99"),
            new_value=Decimal("24.99"),
            field_name="price_including_tax",
            change_summary="Price change"
        )
        
        data = change_log.model_dump()
        
        # Decimal values should be serialized as Decimal objects in model_dump()
        assert data["old_value"] == Decimal("19.99")
        assert data["new_value"] == Decimal("24.99")
    
    def test_change_log_with_complex_data_types(self):
        """Test change log with complex data types."""
        change_log = ChangeLog(
            change_id="test_123",
            book_id="book_123",
            source_url="https://example.com/book/123",
            change_type=ChangeType.DESCRIPTION_CHANGE,
            severity=ChangeSeverity.MEDIUM,
            old_value={"short": "Old description"},
            new_value={"long": "New detailed description with more information"},
            field_name="description",
            change_summary="Description updated"
        )
        
        assert isinstance(change_log.old_value, dict)
        assert isinstance(change_log.new_value, dict)


class TestChangeDetectionResult:
    """Test cases for ChangeDetectionResult model."""
    
    def test_valid_detection_result(self):
        """Test creating a valid change detection result."""
        result = ChangeDetectionResult(
            detection_id="detection_123",
            total_books_checked=1000,
            changes_detected=25,
            new_books=5,
            updated_books=15,
            removed_books=5,
            detection_duration_seconds=120.5,
            average_book_processing_time=0.12,
            success=True
        )
        
        assert result.detection_id == "detection_123"
        assert result.total_books_checked == 1000
        assert result.changes_detected == 25
        assert result.new_books == 5
        assert result.updated_books == 15
        assert result.removed_books == 5
        assert result.detection_duration_seconds == 120.5
        assert result.success is True
    
    def test_detection_result_with_errors(self):
        """Test detection result with errors."""
        result = ChangeDetectionResult(
            detection_id="detection_456",
            total_books_checked=500,
            changes_detected=0,
            success=False,
            errors=["Network timeout", "Database connection failed", "Invalid book data"]
        )
        
        assert result.success is False
        assert len(result.errors) == 3
        assert "Network timeout" in result.errors
        assert "Database connection failed" in result.errors
        assert "Invalid book data" in result.errors
    
    def test_detection_result_with_change_breakdown(self):
        """Test detection result with change breakdown."""
        result = ChangeDetectionResult(
            detection_id="detection_789",
            total_books_checked=100,
            changes_detected=10,
            changes_by_type={
                ChangeType.PRICE_CHANGE: 3,
                ChangeType.AVAILABILITY_CHANGE: 2,
                ChangeType.NEW_BOOK: 5
            },
            changes_by_severity={
                ChangeSeverity.HIGH: 3,
                ChangeSeverity.MEDIUM: 5,
                ChangeSeverity.LOW: 2
            }
        )
        
        assert result.changes_by_type[ChangeType.PRICE_CHANGE] == 3
        assert result.changes_by_type[ChangeType.NEW_BOOK] == 5
        assert result.changes_by_severity[ChangeSeverity.HIGH] == 3
        assert result.changes_by_severity[ChangeSeverity.LOW] == 2
    
    def test_detection_result_defaults(self):
        """Test detection result with default values."""
        result = ChangeDetectionResult(detection_id="test_123")
        
        assert result.total_books_checked == 0
        assert result.changes_detected == 0
        assert result.new_books == 0
        assert result.updated_books == 0
        assert result.removed_books == 0
        assert result.detection_duration_seconds == 0.0
        assert result.success is True
        assert result.errors == []


class TestAlertConfig:
    """Test cases for AlertConfig model."""
    
    def test_valid_alert_config(self):
        """Test creating a valid alert configuration."""
        config = AlertConfig(
            enabled=True,
            log_enabled=True,
            min_severity_for_log=ChangeSeverity.MEDIUM,
            max_alerts_per_hour=20,
            alert_cooldown_minutes=15
        )
        
        assert config.enabled is True
        assert config.log_enabled is True
        assert config.min_severity_for_log == ChangeSeverity.MEDIUM
        assert config.max_alerts_per_hour == 20
        assert config.alert_cooldown_minutes == 15
    
    def test_alert_config_defaults(self):
        """Test alert configuration defaults."""
        config = AlertConfig()
        
        assert config.enabled is True
        assert config.log_enabled is True
        assert config.min_severity_for_log == ChangeSeverity.LOW
        assert config.max_alerts_per_hour == 10
        assert config.alert_cooldown_minutes == 30
    
    def test_alert_config_disabled(self):
        """Test disabled alert configuration."""
        config = AlertConfig(
            enabled=False,
            log_enabled=False
        )
        
        assert config.enabled is False
        assert config.log_enabled is False


class TestSchedulerConfig:
    """Test cases for SchedulerConfig model."""
    
    def test_valid_scheduler_config(self):
        """Test creating a valid scheduler configuration."""
        config = SchedulerConfig(
            schedule_hour=14,
            schedule_minute=30,
            timezone="America/New_York",
            enable_change_detection=True,
            enable_new_book_detection=True,
            enable_removed_book_detection=True,
            max_concurrent_books=25,
            batch_size=50,
            request_timeout=45,
            enable_content_fingerprinting=True,
            fingerprint_fields=["name", "price_including_tax", "availability"],
            generate_daily_reports=True,
            report_format="json",
            report_retention_days=60
        )
        
        assert config.schedule_hour == 14
        assert config.schedule_minute == 30
        assert config.timezone == "America/New_York"
        assert config.enable_change_detection is True
        assert config.max_concurrent_books == 25
        assert config.batch_size == 50
        assert config.request_timeout == 45
        assert config.enable_content_fingerprinting is True
        assert len(config.fingerprint_fields) == 3
        assert config.generate_daily_reports is True
        assert config.report_format == "json"
        assert config.report_retention_days == 60
    
    def test_scheduler_config_defaults(self):
        """Test scheduler configuration defaults."""
        config = SchedulerConfig()
        
        assert config.schedule_hour == 14
        assert config.schedule_minute == 30
        assert config.timezone == "UTC"
        assert config.enable_change_detection is True
        assert config.enable_new_book_detection is True
        assert config.enable_removed_book_detection is True
        assert config.max_concurrent_books == 50
        assert config.batch_size == 100
        assert config.request_timeout == 30
        assert config.enable_content_fingerprinting is True
        assert config.generate_daily_reports is True
        assert config.report_format == "json"
        assert config.report_retention_days == 30
    
    def test_scheduler_config_time_validation(self):
        """Test scheduler configuration time validation."""
        # Valid times
        valid_times = [
            (0, 0),   # Midnight
            (12, 30), # Noon
            (23, 59), # End of day
            (14, 0),  # 2 PM
        ]
        
        for hour, minute in valid_times:
            config = SchedulerConfig(schedule_hour=hour, schedule_minute=minute)
            assert config.schedule_hour == hour
            assert config.schedule_minute == minute
        
        # Invalid hours
        invalid_hours = [-1, 24, 25]
        for hour in invalid_hours:
            with pytest.raises(ValidationError):
                SchedulerConfig(schedule_hour=hour)
        
        # Invalid minutes
        invalid_minutes = [-1, 60, 61]
        for minute in invalid_minutes:
            with pytest.raises(ValidationError):
                SchedulerConfig(schedule_minute=minute)
    
    def test_scheduler_config_fingerprint_fields(self):
        """Test scheduler configuration fingerprint fields."""
        config = SchedulerConfig(
            fingerprint_fields=["name", "description", "price_including_tax"]
        )
        
        assert config.fingerprint_fields == ["name", "description", "price_including_tax"]
        
        # Test default fingerprint fields
        default_config = SchedulerConfig()
        expected_defaults = [
            "name", "description", "category", "price_including_tax", 
            "availability", "rating"
        ]
        assert default_config.fingerprint_fields == expected_defaults


class TestDailyReport:
    """Test cases for DailyReport model."""
    
    def test_valid_daily_report(self):
        """Test creating a valid daily report."""
        report_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        report = DailyReport(
            report_id="report_123",
            report_date=report_date,
            total_books_in_system=1000,
            books_checked=950,
            changes_detected=25,
            new_books_added=5,
            books_updated=15,
            books_removed=5,
            total_processing_time_seconds=300.5,
            average_book_processing_time=0.32,
            system_health_score=0.95
        )
        
        assert report.report_id == "report_123"
        assert report.report_date == report_date
        assert report.total_books_in_system == 1000
        assert report.books_checked == 950
        assert report.changes_detected == 25
        assert report.new_books_added == 5
        assert report.books_updated == 15
        assert report.books_removed == 5
        assert report.total_processing_time_seconds == 300.5
        assert report.average_book_processing_time == 0.32
        assert report.system_health_score == 0.95
        assert report.generated_at is not None
    
    def test_daily_report_with_change_breakdown(self):
        """Test daily report with change breakdown."""
        report_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        report = DailyReport(
            report_id="report_456",
            report_date=report_date,
            changes_by_type={
                ChangeType.PRICE_CHANGE: 10,
                ChangeType.AVAILABILITY_CHANGE: 5,
                ChangeType.NEW_BOOK: 8,
                ChangeType.BOOK_REMOVED: 2
            },
            changes_by_severity={
                ChangeSeverity.HIGH: 5,
                ChangeSeverity.MEDIUM: 12,
                ChangeSeverity.LOW: 8
            }
        )
        
        assert report.changes_by_type[ChangeType.PRICE_CHANGE] == 10
        assert report.changes_by_type[ChangeType.NEW_BOOK] == 8
        assert report.changes_by_severity[ChangeSeverity.HIGH] == 5
        assert report.changes_by_severity[ChangeSeverity.LOW] == 8
    
    def test_daily_report_with_errors(self):
        """Test daily report with errors."""
        report_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        report = DailyReport(
            report_id="report_789",
            report_date=report_date,
            errors_encountered=[
                "Network timeout for book 123",
                "Invalid data format for book 456",
                "Database connection lost"
            ],
            system_health_score=0.7
        )
        
        assert len(report.errors_encountered) == 3
        assert "Network timeout for book 123" in report.errors_encountered
        assert report.system_health_score == 0.7
    
    def test_daily_report_system_health_score_validation(self):
        """Test system health score validation."""
        report_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Valid health scores
        valid_scores = [0.0, 0.5, 1.0]
        for score in valid_scores:
            report = DailyReport(
                report_id="test_123",
                report_date=report_date,
                system_health_score=score
            )
            assert report.system_health_score == score
        
        # Invalid health scores
        invalid_scores = [-0.1, 1.1, 2.0]
        for score in invalid_scores:
            with pytest.raises(ValidationError):
                DailyReport(
                    report_id="test_123",
                    report_date=report_date,
                    system_health_score=score
                )
    
    def test_daily_report_defaults(self):
        """Test daily report defaults."""
        report_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        report = DailyReport(
            report_id="test_123",
            report_date=report_date
        )
        
        assert report.total_books_in_system == 0
        assert report.books_checked == 0
        assert report.changes_detected == 0
        assert report.new_books_added == 0
        assert report.books_updated == 0
        assert report.books_removed == 0
        assert report.total_processing_time_seconds == 0.0
        assert report.average_book_processing_time == 0.0
        assert report.changes_by_type == {}
        assert report.changes_by_severity == {}
        assert report.significant_changes == []
        assert report.new_books == []
        assert report.errors_encountered == []
        assert report.system_health_score == 1.0


class TestModelSerialization:
    """Test cases for model serialization and deserialization."""
    
    def test_change_log_json_serialization(self):
        """Test ChangeLog JSON serialization."""
        change_log = ChangeLog(
            change_id="test_123",
            book_id="book_123",
            source_url="https://example.com/book/123",
            change_type=ChangeType.PRICE_CHANGE,
            severity=ChangeSeverity.HIGH,
            old_value=Decimal("19.99"),
            new_value=Decimal("24.99"),
            field_name="price_including_tax",
            change_summary="Price increased"
        )
        
        json_data = change_log.model_dump_json()
        assert isinstance(json_data, str)
        assert "test_123" in json_data
        assert "price_change" in json_data
        assert "high" in json_data
    
    def test_change_log_json_deserialization(self):
        """Test ChangeLog JSON deserialization."""
        json_data = '''
        {
            "change_id": "test_123",
            "book_id": "book_123",
            "source_url": "https://example.com/book/123",
            "change_type": "price_change",
            "severity": "high",
            "old_value": "19.99",
            "new_value": "24.99",
            "field_name": "price_including_tax",
            "change_summary": "Price increased",
            "detected_at": "2023-01-01T12:00:00Z",
            "processed": false,
            "confidence_score": 1.0
        }
        '''
        
        change_log = ChangeLog.model_validate_json(json_data)
        
        assert change_log.change_id == "test_123"
        assert change_log.change_type == ChangeType.PRICE_CHANGE
        assert change_log.severity == ChangeSeverity.HIGH
        assert change_log.old_value == "19.99"  # JSON deserialization returns strings
        assert change_log.new_value == "24.99"
    
    def test_fingerprint_json_serialization(self):
        """Test ContentFingerprint JSON serialization."""
        fingerprint = ContentFingerprint(
            book_id="book_123",
            source_url="https://example.com/book/123",
            content_hash="a" * 64,
            price_hash="b" * 64,
            availability_hash="c" * 64,
            metadata_hash="d" * 64
        )
        
        json_data = fingerprint.model_dump_json()
        assert isinstance(json_data, str)
        assert "book_123" in json_data
        assert "a" * 64 in json_data
    
    def test_detection_result_json_serialization(self):
        """Test ChangeDetectionResult JSON serialization."""
        result = ChangeDetectionResult(
            detection_id="detection_123",
            total_books_checked=100,
            changes_detected=5,
            success=True
        )
        
        json_data = result.model_dump_json()
        assert isinstance(json_data, str)
        assert "detection_123" in json_data
        assert "100" in json_data
        assert "5" in json_data


class TestModelEdgeCases:
    """Test cases for edge case data scenarios in models."""
    
    def test_change_log_with_extreme_values(self):
        """Test change log with extreme values."""
        # Test with very large numbers
        change_log = ChangeLog(
            change_id="test_extreme_123",
            book_id="book_123",
            source_url="https://example.com/book/123",
            change_type=ChangeType.PRICE_CHANGE,
            severity=ChangeSeverity.HIGH,
            old_value=Decimal("999999.99"),
            new_value=Decimal("0.01"),
            field_name="price_including_tax",
            change_summary="Price changed from $999999.99 to $0.01"
        )
        
        assert change_log.old_value == Decimal("999999.99")
        assert change_log.new_value == Decimal("0.01")
    
    def test_change_log_with_unicode_characters(self):
        """Test change log with Unicode characters."""
        change_log = ChangeLog(
            change_id="test_unicode_123",
            book_id="book_123",
            source_url="https://example.com/book/123",
            change_type=ChangeType.DESCRIPTION_CHANGE,
            severity=ChangeSeverity.MEDIUM,
            old_value="Old description",
            new_value="Nueva descripción con acentos: café, año, corazón",
            field_name="description",
            change_summary="Description updated with Unicode characters"
        )
        
        assert "café" in change_log.new_value
        assert "año" in change_log.new_value
        assert "corazón" in change_log.new_value
    
    def test_change_log_with_html_entities(self):
        """Test change log with HTML entities."""
        change_log = ChangeLog(
            change_id="test_html_123",
            book_id="book_123",
            source_url="https://example.com/book/123",
            change_type=ChangeType.DESCRIPTION_CHANGE,
            severity=ChangeSeverity.LOW,
            old_value="Old description",
            new_value="New description with &amp; &lt; &gt; &quot; entities",
            field_name="description",
            change_summary="Description updated with HTML entities"
        )
        
        assert "&amp;" in change_log.new_value
        assert "&lt;" in change_log.new_value
        assert "&gt;" in change_log.new_value
        assert "&quot;" in change_log.new_value
    
    def test_change_log_with_empty_strings(self):
        """Test change log with empty strings."""
        change_log = ChangeLog(
            change_id="test_empty_123",
            book_id="book_123",
            source_url="https://example.com/book/123",
            change_type=ChangeType.DESCRIPTION_CHANGE,
            severity=ChangeSeverity.MEDIUM,
            old_value="Original description",
            new_value="",  # Empty string
            field_name="description",
            change_summary="Description cleared"
        )
        
        assert change_log.old_value == "Original description"
        assert change_log.new_value == ""
    
    def test_change_log_with_very_long_strings(self):
        """Test change log with very long strings."""
        long_string = "A" * 10000  # 10KB string
        
        change_log = ChangeLog(
            change_id="test_long_123",
            book_id="book_123",
            source_url="https://example.com/book/123",
            change_type=ChangeType.DESCRIPTION_CHANGE,
            severity=ChangeSeverity.LOW,
            old_value="Short description",
            new_value=long_string,
            field_name="description",
            change_summary="Description updated with very long content"
        )
        
        assert len(change_log.new_value) == 10000
        assert change_log.new_value == long_string


class TestModelBoundaryConditions:
    """Test boundary conditions for model validation."""
    
    def test_scheduler_config_boundary_times(self):
        """Test scheduler config with boundary time values."""
        # Test minimum values
        config_min = SchedulerConfig(
            schedule_hour=0,
            schedule_minute=0,
            timezone="UTC"
        )
        assert config_min.schedule_hour == 0
        assert config_min.schedule_minute == 0
        
        # Test maximum values
        config_max = SchedulerConfig(
            schedule_hour=23,
            schedule_minute=59,
            timezone="UTC"
        )
        assert config_max.schedule_hour == 23
        assert config_max.schedule_minute == 59
    
    def test_alert_config_boundary_values(self):
        """Test alert config with boundary values."""
        # Test minimum values
        config_min = AlertConfig(
            max_alerts_per_hour=1,
            alert_cooldown_minutes=1
        )
        assert config_min.max_alerts_per_hour == 1
        assert config_min.alert_cooldown_minutes == 1
        
        # Test with high values
        config_high = AlertConfig(
            max_alerts_per_hour=1000,
            alert_cooldown_minutes=1440  # 24 hours
        )
        assert config_high.max_alerts_per_hour == 1000
        assert config_high.alert_cooldown_minutes == 1440
    
    def test_change_detection_result_boundary_counts(self):
        """Test change detection result with boundary count values."""
        # Test with zero values
        result_zero = ChangeDetectionResult(
            detection_id="test_zero",
            total_books_checked=0,
            changes_detected=0,
            new_books=0,
            updated_books=0,
            removed_books=0,
            restored_books=0
        )
        assert result_zero.total_books_checked == 0
        assert result_zero.changes_detected == 0
        
        # Test with high values
        result_high = ChangeDetectionResult(
            detection_id="test_high",
            total_books_checked=100000,
            changes_detected=50000,
            new_books=10000,
            updated_books=20000,
            removed_books=5000,
            restored_books=15000
        )
        assert result_high.total_books_checked == 100000
        assert result_high.changes_detected == 50000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
