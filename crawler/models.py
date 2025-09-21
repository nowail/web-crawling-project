"""
Pydantic models for book data validation and serialization.
Implements the Book schema with all required fields and metadata.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl, validator


class BookAvailability(str, Enum):
    """Enum for book availability status."""
    IN_STOCK = "In stock"
    OUT_OF_STOCK = "Out of stock"


class BookRating(int, Enum):
    """Enum for book rating values (1-5 stars)."""
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5


class CrawlStatus(str, Enum):
    """Enum for crawl status tracking."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class BookData(BaseModel):
    """
    Main book data model with all required fields from Part 1 requirements.
    """
    # Core book information
    name: str = Field(..., description="Name of the book")
    description: str = Field(..., description="Description of the book")
    category: str = Field(..., description="Book category")
    
    # Pricing information
    price_including_tax: Decimal = Field(..., description="Price including taxes")
    price_excluding_tax: Decimal = Field(..., description="Price excluding taxes")
    
    # Availability and reviews
    availability: BookAvailability = Field(..., description="Book availability status")
    number_of_reviews: int = Field(..., ge=0, description="Number of reviews")
    
    # Media and rating
    image_url: HttpUrl = Field(..., description="URL of the book cover image")
    rating: Optional[BookRating] = Field(None, description="Rating of the book (1-5 stars)")
    
    # Metadata for crawling
    source_url: HttpUrl = Field(..., description="Source URL of the book page")
    crawl_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the book was crawled")
    status: CrawlStatus = Field(default=CrawlStatus.COMPLETED, description="Crawl status")
    
    # Raw HTML snapshot for fallback
    raw_html: Optional[str] = Field(None, description="Raw HTML snapshot of the book page")
    
    @validator('number_of_reviews')
    def validate_reviews(cls, v):
        """Ensure number of reviews is non-negative."""
        if v < 0:
            raise ValueError('Number of reviews cannot be negative')
        return v
    
    @validator('price_including_tax', 'price_excluding_tax')
    def validate_prices(cls, v):
        """Ensure prices are positive."""
        if v <= 0:
            raise ValueError('Price must be positive')
        return v
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v),
            HttpUrl: lambda v: str(v)
        }
        json_schema_extra = {
            "example": {
                "name": "A Light in the Attic",
                "description": "It's hard to imagine a world without A Light in the Attic...",
                "category": "Poetry",
                "price_including_tax": 51.77,
                "price_excluding_tax": 51.77,
                "availability": "In stock",
                "number_of_reviews": 22,
                "image_url": "https://books.toscrape.com/media/cache/2c/da/2cdad67c44b002e7ead0cc35693c0e8.jpg",
                "rating": 3,
                "source_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
                "crawl_timestamp": "2024-01-15T10:30:00Z",
                "status": "completed"
            }
        }


class CrawlState(BaseModel):
    """
    Model for tracking crawl state and resumability.
    """
    last_processed_page: int = Field(default=1, description="Last successfully processed page")
    total_pages: Optional[int] = Field(None, description="Total number of pages to crawl")
    books_processed: int = Field(default=0, description="Number of books successfully processed")
    last_processed_url: Optional[str] = Field(None, description="Last successfully processed book URL")
    crawl_start_time: datetime = Field(default_factory=datetime.utcnow, description="When the crawl started")
    last_update_time: datetime = Field(default_factory=datetime.utcnow, description="Last state update")
    errors: List[str] = Field(default_factory=list, description="List of errors encountered")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CrawlResult(BaseModel):
    """
    Model for crawl operation results.
    """
    success: bool = Field(..., description="Whether the crawl operation was successful")
    books_crawled: int = Field(..., description="Number of books successfully crawled")
    errors: List[str] = Field(default_factory=list, description="List of errors encountered")
    duration_seconds: float = Field(..., description="Total crawl duration in seconds")
    start_time: datetime = Field(..., description="Crawl start time")
    end_time: datetime = Field(..., description="Crawl end time")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
