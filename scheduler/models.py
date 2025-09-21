"""
Models for scheduler and change detection functionality.

This module defines Pydantic models for:
- Change detection results
- Content fingerprints
- Change logs
- Alert configurations
- Report data structures
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, HttpUrl
from pydantic.networks import HttpUrl


class ChangeType(str, Enum):
    """Types of changes that can be detected."""
    NEW_BOOK = "new_book"
    PRICE_CHANGE = "price_change"
    AVAILABILITY_CHANGE = "availability_change"
    DESCRIPTION_CHANGE = "description_change"
    IMAGE_CHANGE = "image_change"
    RATING_CHANGE = "rating_change"
    REVIEWS_CHANGE = "reviews_change"
    CATEGORY_CHANGE = "category_change"
    BOOK_REMOVED = "book_removed"


class ChangeSeverity(str, Enum):
    """Severity levels for changes."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContentFingerprint(BaseModel):
    """Content fingerprint for change detection."""
    book_id: str = Field(..., description="Unique book identifier")
    source_url: HttpUrl = Field(..., description="Book source URL")
    content_hash: str = Field(..., description="SHA-256 hash of book content")
    price_hash: str = Field(..., description="Hash of price information")
    availability_hash: str = Field(..., description="Hash of availability information")
    metadata_hash: str = Field(..., description="Hash of metadata (description, category, etc.)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: lambda v: str(v)
        }


class ChangeLog(BaseModel):
    """Log entry for tracking changes."""
    change_id: str = Field(..., description="Unique change identifier")
    book_id: str = Field(..., description="Book identifier")
    source_url: HttpUrl = Field(..., description="Book source URL")
    change_type: ChangeType = Field(..., description="Type of change detected")
    severity: ChangeSeverity = Field(..., description="Change severity level")
    
    # Change details
    old_value: Optional[Any] = Field(default=None, description="Previous value")
    new_value: Optional[Any] = Field(default=None, description="New value")
    field_name: Optional[str] = Field(default=None, description="Field that changed")
    
    # Metadata
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = Field(default=None)
    processed: bool = Field(default=False)
    
    # Additional context
    change_summary: str = Field(..., description="Human-readable change summary")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in change detection")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: lambda v: str(v)
        }


class ChangeDetectionResult(BaseModel):
    """Result of change detection process."""
    detection_id: str = Field(..., description="Unique detection run identifier")
    run_timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_books_checked: int = Field(default=0)
    changes_detected: int = Field(default=0)
    new_books: int = Field(default=0)
    updated_books: int = Field(default=0)
    removed_books: int = Field(default=0)
    
    # Performance metrics
    detection_duration_seconds: float = Field(default=0.0)
    average_book_processing_time: float = Field(default=0.0)
    
    # Change breakdown
    changes_by_type: Dict[ChangeType, int] = Field(default_factory=dict)
    changes_by_severity: Dict[ChangeSeverity, int] = Field(default_factory=dict)
    
    # Status
    success: bool = Field(default=True)
    errors: List[str] = Field(default_factory=list)
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AlertConfig(BaseModel):
    """Configuration for alerting system (logging only)."""
    enabled: bool = Field(default=True)
    log_enabled: bool = Field(default=True)
    
    # Alert thresholds
    min_severity_for_log: ChangeSeverity = Field(default=ChangeSeverity.LOW)
    
    # Rate limiting
    max_alerts_per_hour: int = Field(default=10)
    alert_cooldown_minutes: int = Field(default=30)


class DailyReport(BaseModel):
    """Daily change report structure."""
    report_id: str = Field(..., description="Unique report identifier")
    report_date: datetime = Field(..., description="Date of the report")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Summary statistics
    total_books_in_system: int = Field(default=0)
    books_checked: int = Field(default=0)
    changes_detected: int = Field(default=0)
    new_books_added: int = Field(default=0)
    books_updated: int = Field(default=0)
    books_removed: int = Field(default=0)
    
    # Change breakdown
    changes_by_type: Dict[ChangeType, int] = Field(default_factory=dict)
    changes_by_severity: Dict[ChangeSeverity, int] = Field(default_factory=dict)
    
    # Performance metrics
    total_processing_time_seconds: float = Field(default=0.0)
    average_book_processing_time: float = Field(default=0.0)
    
    # Detailed changes
    significant_changes: List[ChangeLog] = Field(default_factory=list)
    new_books: List[Dict[str, Any]] = Field(default_factory=list)
    
    # System health
    errors_encountered: List[str] = Field(default_factory=list)
    system_health_score: float = Field(default=1.0, ge=0.0, le=1.0)
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SchedulerConfig(BaseModel):
    """Configuration for the scheduler system."""
    # Scheduling
    schedule_hour: int = Field(default=14, ge=0, le=23, description="Hour to run daily check (24h format)")
    schedule_minute: int = Field(default=30, ge=0, le=59, description="Minute to run daily check")
    timezone: str = Field(default="UTC", description="Timezone for scheduling")
    
    # Change detection
    enable_change_detection: bool = Field(default=True)
    enable_new_book_detection: bool = Field(default=True)
    enable_removed_book_detection: bool = Field(default=True)
    
    # Performance
    max_concurrent_books: int = Field(default=50, description="Max books to check concurrently")
    batch_size: int = Field(default=100, description="Batch size for processing")
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    
    # Fingerprinting
    enable_content_fingerprinting: bool = Field(default=True)
    fingerprint_fields: List[str] = Field(
        default=["name", "description", "category", "price_including_tax", "availability", "rating"],
        description="Fields to include in fingerprint"
    )
    
    # Reporting
    generate_daily_reports: bool = Field(default=True)
    report_format: str = Field(default="json", description="Report format (json/csv)")
    report_retention_days: int = Field(default=30, description="Days to keep reports")
    
    # Alerting
    alert_config: AlertConfig = Field(default_factory=AlertConfig)
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

