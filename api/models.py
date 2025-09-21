"""
API models and schemas for the FastAPI application.
"""

from datetime import datetime
from typing import List, Optional
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, validator
from pydantic.types import PositiveInt


class BookRating(int, Enum):
    """Book rating enumeration."""
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5


class SortBy(str, Enum):
    """Sort options for book listings."""
    RATING = "rating"
    PRICE = "price"
    REVIEWS = "reviews"
    NAME = "name"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class SortOrder(str, Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"


class BookResponse(BaseModel):
    """Book response model for API."""
    id: str = Field(..., description="Unique book identifier")
    name: str = Field(..., description="Book title")
    description: str = Field(..., description="Book description")
    category: str = Field(..., description="Book category")
    price_including_tax: float = Field(..., description="Price including tax")
    price_excluding_tax: float = Field(..., description="Price excluding tax")
    availability: str = Field(..., description="Availability status")
    rating: BookRating = Field(..., description="Book rating (1-5)")
    number_of_reviews: int = Field(..., description="Number of reviews")
    image_url: str = Field(..., description="Book cover image URL")
    source_url: str = Field(..., description="Original source URL")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    crawl_timestamp: Optional[str] = Field(None, description="Crawl timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: str
        }


class BookListResponse(BaseModel):
    """Response model for book list with pagination."""
    books: List[BookResponse] = Field(..., description="List of books")
    total: int = Field(..., description="Total number of books")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of books per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class BookQueryParams(BaseModel):
    """Query parameters for book listing."""
    category: Optional[str] = Field(None, description="Filter by category")
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price filter")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price filter")
    rating: Optional[BookRating] = Field(None, description="Filter by rating")
    sort_by: SortBy = Field(SortBy.NAME, description="Sort field")
    sort_order: SortOrder = Field(SortOrder.ASC, description="Sort order")
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")

    @validator('max_price')
    def validate_price_range(cls, v, values):
        """Validate that max_price is greater than min_price."""
        if v is not None and 'min_price' in values and values['min_price'] is not None:
            if v < values['min_price']:
                raise ValueError('max_price must be greater than min_price')
        return v


class ChangeType(str, Enum):
    """Change type enumeration."""
    PRICE_CHANGE = "price_change"
    AVAILABILITY_CHANGE = "availability_change"
    RATING_CHANGE = "rating_change"
    REVIEWS_CHANGE = "reviews_change"
    NEW_BOOK = "new_book"
    BOOK_REMOVED = "book_removed"
    DESCRIPTION_CHANGE = "description_change"
    CATEGORY_CHANGE = "category_change"


class ChangeSeverity(str, Enum):
    """Change severity enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChangeResponse(BaseModel):
    """Change response model for API."""
    change_id: str = Field(..., description="Unique change identifier")
    book_id: str = Field(..., description="Book identifier")
    book_name: str = Field(..., description="Book name")
    change_type: ChangeType = Field(..., description="Type of change")
    severity: ChangeSeverity = Field(..., description="Change severity")
    field_name: str = Field(..., description="Field that changed")
    old_value: Optional[str] = Field(None, description="Previous value")
    new_value: Optional[str] = Field(None, description="New value")
    change_summary: str = Field(..., description="Human-readable change summary")
    detected_at: str = Field(..., description="When the change was detected")
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence in the change detection")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ChangeListResponse(BaseModel):
    """Response model for change list with pagination."""
    changes: List[ChangeResponse] = Field(..., description="List of changes")
    total: int = Field(..., description="Total number of changes")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of changes per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class ChangeQueryParams(BaseModel):
    """Query parameters for change listing."""
    book_id: Optional[str] = Field(None, description="Filter by book ID")
    change_type: Optional[ChangeType] = Field(None, description="Filter by change type")
    severity: Optional[ChangeSeverity] = Field(None, description="Filter by severity")
    since: Optional[datetime] = Field(None, description="Changes since this date")
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")


class APIKeyResponse(BaseModel):
    """API key response model."""
    api_key: str = Field(..., description="Generated API key")
    expires_at: Optional[datetime] = Field(None, description="API key expiration time")
    rate_limit: int = Field(100, description="Requests per hour limit")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")
    status_code: int = Field(..., description="HTTP status code")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Current timestamp")
    version: str = Field(..., description="API version")
    database_status: str = Field(..., description="Database connection status")
