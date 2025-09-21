"""
FastAPI main application for the FilersKeepers Book Management API.
"""

import os
from contextlib import asynccontextmanager
from typing import Dict

import structlog
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient

from api.auth import verify_api_key, get_rate_limit_headers
from api.database import APIDatabaseService
from api.models import (
    BookQueryParams, BookListResponse, BookResponse,
    ChangeQueryParams, ChangeListResponse,
    ErrorResponse, HealthResponse
)
from utilities.config import config
from api.config import config as api_config
from datetime import datetime

# Setup logging
logger = structlog.get_logger(__name__)

# Global database service
db_service: APIDatabaseService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting FilersKeepers API")
    
    # Initialize database connection
    global db_service
    try:
        client = AsyncIOMotorClient(config.mongodb_url)
        database = client[config.mongodb_database]
        
        # Test connection
        await database.command("ping")
        logger.info("Database connection established")
        
        # Initialize database service
        db_service = APIDatabaseService(database)
        
    except Exception as e:
        logger.error("Failed to connect to database", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down FilersKeepers API")
    if db_service:
        client.close()


# Create FastAPI application
app = FastAPI(
    title="FilersKeepers Book Management API",
    description="""
    A comprehensive REST API for managing and monitoring book data with change detection.
    
    ## Features
    
    * **Book Management**: Browse, search, and filter books
    * **Change Tracking**: Monitor price changes, availability updates, and new books
    * **Authentication**: API key-based authentication
    * **Rate Limiting**: 100 requests per hour per API key
    * **Pagination**: Efficient pagination for large datasets
    
    ## Authentication
    
    All endpoints require an API key. Include your API key in the Authorization header:
    
    ```
    Authorization: Bearer your_api_key_here
    ```
    
    ## Rate Limiting
    
    Each API key is limited to 100 requests per hour. Rate limit information is included in response headers.
    """,
    version="1.0.0",
    contact={
        "name": "FilersKeepers API Support",
        "email": "support@filerskeepers.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            status_code=exc.status_code
        ).dict(),
        headers=exc.headers
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions."""
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc) if api_config.debug else None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ).dict()
    )


# Health check endpoint (no authentication required)
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    try:
        db_status = "healthy"
        if db_service:
            health_info = await db_service.health_check()
            db_status = health_info.get("status", "unknown")
        
        return HealthResponse(
            status="healthy" if db_status == "healthy" else "degraded",
            timestamp=datetime.utcnow(),
            version="1.0.0",
            database_status=db_status
        )
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            version="1.0.0",
            database_status="unhealthy"
        )


# Books endpoints
@app.get("/books", response_model=BookListResponse, tags=["Books"])
async def get_books(
    category: str = None,
    min_price: float = None,
    max_price: float = None,
    rating: int = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    page: int = 1,
    per_page: int = 20,
    api_key: str = Depends(verify_api_key)
):
    """
    Get books with filtering, sorting, and pagination.
    
    - **category**: Filter by book category
    - **min_price**: Minimum price filter
    - **max_price**: Maximum price filter  
    - **rating**: Filter by rating (1-5)
    - **sort_by**: Sort field (name, rating, price, reviews, created_at, updated_at)
    - **sort_order**: Sort order (asc, desc)
    - **page**: Page number (starts from 1)
    - **per_page**: Items per page (1-100)
    """
    try:
        # Create query parameters
        query_params = BookQueryParams(
            category=category,
            min_price=min_price,
            max_price=max_price,
            rating=rating,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page
        )
        
        # Get books from database
        if not db_service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database service not available"
            )
        result = await db_service.get_books(query_params)
        
        # Add rate limit headers
        headers = get_rate_limit_headers(api_key)
        
        return JSONResponse(
            content=result.dict(),
            headers=headers
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to get books", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve books: {str(e)}"
        )


@app.get("/books/{book_id}", response_model=BookResponse, tags=["Books"])
async def get_book(
    book_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get a single book by ID.
    
    - **book_id**: Book identifier (MongoDB ObjectId or source URL)
    """
    try:
        book = await db_service.get_book_by_id(book_id)
        
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID '{book_id}' not found"
            )
        
        # Add rate limit headers
        headers = get_rate_limit_headers(api_key)
        
        return JSONResponse(
            content=book.dict(),
            headers=headers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get book", book_id=book_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve book"
        )


# Changes endpoints
@app.get("/changes", response_model=ChangeListResponse, tags=["Changes"])
async def get_changes(
    book_id: str = None,
    change_type: str = None,
    severity: str = None,
    since: str = None,
    page: int = 1,
    per_page: int = 20,
    api_key: str = Depends(verify_api_key)
):
    """
    Get recent changes with filtering and pagination.
    
    - **book_id**: Filter by book ID
    - **change_type**: Filter by change type (price_change, availability_change, rating_change, new_book, book_removed, description_change, category_change)
    - **severity**: Filter by severity (low, medium, high, critical)
    - **since**: Changes since this date (ISO format)
    - **page**: Page number (starts from 1)
    - **per_page**: Items per page (1-100)
    """
    try:
        # Parse since date if provided
        since_date = None
        if since:
            try:
                from datetime import datetime
                since_date = datetime.fromisoformat(since.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date format for 'since' parameter. Use ISO format."
                )
        
        # Create query parameters
        query_params = ChangeQueryParams(
            book_id=book_id,
            change_type=change_type,
            severity=severity,
            since=since_date,
            page=page,
            per_page=per_page
        )
        
        # Get changes from database
        result = await db_service.get_changes(query_params)
        
        # Add rate limit headers
        headers = get_rate_limit_headers(api_key)
        
        return JSONResponse(
            content=result.dict(),
            headers=headers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get changes", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve changes: {str(e)}"
        )


# Statistics endpoint
@app.get("/stats", tags=["Statistics"])
async def get_stats(api_key: str = Depends(verify_api_key)):
    """Get database statistics."""
    try:
        stats = await db_service.get_stats()
        
        # Add rate limit headers
        headers = get_rate_limit_headers(api_key)
        
        return JSONResponse(
            content=stats,
            headers=headers
        )
        
    except Exception as e:
        logger.error("Failed to get stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
