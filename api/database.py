"""
Database service layer for the FastAPI application.
"""

import math
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.models import (
    BookQueryParams, BookResponse, BookListResponse,
    ChangeQueryParams, ChangeResponse, ChangeListResponse,
    SortBy, SortOrder, ChangeType, ChangeSeverity
)

logger = structlog.get_logger(__name__)


class APIDatabaseService:
    """Database service for API operations."""

    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.books_collection = database.books
        self.changes_collection = database.change_logs

    async def get_books(
        self, 
        query_params: BookQueryParams
    ) -> BookListResponse:
        """
        Get books with filtering, sorting, and pagination.
        
        Args:
            query_params: Query parameters for filtering and pagination
            
        Returns:
            BookListResponse with paginated results
        """
        try:
            # Build filter query
            filter_query = {}
            
            if query_params.category:
                filter_query["category"] = {"$regex": query_params.category, "$options": "i"}
            
            if query_params.min_price is not None or query_params.max_price is not None:
                price_filter = {}
                if query_params.min_price is not None:
                    price_filter["$gte"] = float(query_params.min_price)
                if query_params.max_price is not None:
                    price_filter["$lte"] = float(query_params.max_price)
                filter_query["price_including_tax"] = price_filter
            
            if query_params.rating is not None:
                filter_query["rating"] = query_params.rating.value

            # Build sort query
            sort_field = query_params.sort_by.value
            sort_direction = 1 if query_params.sort_order == SortOrder.ASC else -1
            sort_query = [(sort_field, sort_direction)]

            # Calculate pagination
            skip = (query_params.page - 1) * query_params.per_page

            # Get total count
            total = await self.books_collection.count_documents(filter_query)
            total_pages = math.ceil(total / query_params.per_page)

            # Get books
            cursor = self.books_collection.find(filter_query).sort(sort_query).skip(skip).limit(query_params.per_page)
            books_docs = await cursor.to_list(length=query_params.per_page)

            # Convert to response models
            books = []
            for book_doc in books_docs:
                book_doc["id"] = str(book_doc["_id"])
                del book_doc["_id"]
                
                # Handle missing timestamp fields
                if "created_at" not in book_doc and "crawl_timestamp" in book_doc:
                    book_doc["created_at"] = book_doc["crawl_timestamp"]
                if "updated_at" not in book_doc and "crawl_timestamp" in book_doc:
                    book_doc["updated_at"] = book_doc["crawl_timestamp"]
                
                # Convert HttpUrl fields to strings for JSON serialization
                book_doc["image_url"] = str(book_doc["image_url"])
                book_doc["source_url"] = str(book_doc["source_url"])
                
                # Convert datetime fields to ISO format strings for JSON serialization
                if "created_at" in book_doc and book_doc["created_at"]:
                    book_doc["created_at"] = book_doc["created_at"].isoformat()
                if "updated_at" in book_doc and book_doc["updated_at"]:
                    book_doc["updated_at"] = book_doc["updated_at"].isoformat()
                if "crawl_timestamp" in book_doc and book_doc["crawl_timestamp"]:
                    book_doc["crawl_timestamp"] = book_doc["crawl_timestamp"].isoformat()
                
                books.append(BookResponse(**book_doc))

            return BookListResponse(
                books=books,
                total=total,
                page=query_params.page,
                per_page=query_params.per_page,
                total_pages=total_pages,
                has_next=query_params.page < total_pages,
                has_prev=query_params.page > 1
            )

        except Exception as e:
            logger.error("Failed to get books", error=str(e), query_params=query_params.dict())
            raise

    async def get_book_by_id(self, book_id: str) -> Optional[BookResponse]:
        """
        Get a single book by ID.
        
        Args:
            book_id: Book identifier
            
        Returns:
            BookResponse if found, None otherwise
        """
        try:
            from bson import ObjectId
            
            # Try to convert to ObjectId first
            try:
                object_id = ObjectId(book_id)
                book_doc = await self.books_collection.find_one({"_id": object_id})
            except:
                # If not a valid ObjectId, try as string
                book_doc = await self.books_collection.find_one({"source_url": book_id})

            if book_doc:
                book_doc["id"] = str(book_doc["_id"])
                del book_doc["_id"]

                
                # Handle missing timestamp fields
                if "created_at" not in book_doc and "crawl_timestamp" in book_doc:
                    book_doc["created_at"] = book_doc["crawl_timestamp"]
                if "updated_at" not in book_doc and "crawl_timestamp" in book_doc:
                    book_doc["updated_at"] = book_doc["crawl_timestamp"]
                
                # Convert HttpUrl fields to strings for JSON serialization
                book_doc["image_url"] = str(book_doc["image_url"])
                book_doc["source_url"] = str(book_doc["source_url"])
                
                # Convert datetime fields to ISO format strings for JSON serialization
                if "created_at" in book_doc and book_doc["created_at"]:
                    book_doc["created_at"] = book_doc["created_at"].isoformat()
                if "updated_at" in book_doc and book_doc["updated_at"]:
                    book_doc["updated_at"] = book_doc["updated_at"].isoformat()
                if "crawl_timestamp" in book_doc and book_doc["crawl_timestamp"]:
                    book_doc["crawl_timestamp"] = book_doc["crawl_timestamp"].isoformat()
                
                return BookResponse(**book_doc)
            
            return None

        except Exception as e:
            logger.error("Failed to get book by ID", book_id=book_id, error=str(e))
            raise

    async def get_changes(
        self, 
        query_params: ChangeQueryParams
    ) -> ChangeListResponse:
        """
        Get changes with filtering and pagination.
        
        Args:
            query_params: Query parameters for filtering and pagination
            
        Returns:
            ChangeListResponse with paginated results
        """
        try:
            # Build filter query
            filter_query = {}
            
            if query_params.book_id:
                filter_query["book_id"] = query_params.book_id
            
            if query_params.change_type:
                filter_query["change_type"] = query_params.change_type.value
            
            if query_params.severity:
                filter_query["severity"] = query_params.severity.value
            
            if query_params.since:
                filter_query["detected_at"] = {"$gte": query_params.since}

            # Calculate pagination
            skip = (query_params.page - 1) * query_params.per_page

            # Get total count
            total = await self.changes_collection.count_documents(filter_query)
            total_pages = math.ceil(total / query_params.per_page)

            # Get changes (sorted by detected_at descending)
            cursor = self.changes_collection.find(filter_query).sort("detected_at", -1).skip(skip).limit(query_params.per_page)
            changes_docs = await cursor.to_list(length=query_params.per_page)

            # Convert to response models
            changes = []
            for change_doc in changes_docs:
                # Convert old_value and new_value to strings for JSON serialization
                if "old_value" in change_doc:
                    if change_doc["old_value"] is not None:
                        change_doc["old_value"] = str(change_doc["old_value"])
                    else:
                        change_doc["old_value"] = None
                if "new_value" in change_doc:
                    if change_doc["new_value"] is not None:
                        change_doc["new_value"] = str(change_doc["new_value"])
                    else:
                        change_doc["new_value"] = None
                
                # Convert datetime fields to ISO format strings for JSON serialization
                if "detected_at" in change_doc and change_doc["detected_at"]:
                    if hasattr(change_doc["detected_at"], 'isoformat'):
                        change_doc["detected_at"] = change_doc["detected_at"].isoformat()
                
                if "processed_at" in change_doc and change_doc["processed_at"]:
                    if hasattr(change_doc["processed_at"], 'isoformat'):
                        change_doc["processed_at"] = change_doc["processed_at"].isoformat()
                    else:
                        change_doc["processed_at"] = None
                else:
                    change_doc["processed_at"] = None
                
                changes.append(ChangeResponse(**change_doc))

            return ChangeListResponse(
                changes=changes,
                total=total,
                page=query_params.page,
                per_page=query_params.per_page,
                total_pages=total_pages,
                has_next=query_params.page < total_pages,
                has_prev=query_params.page > 1
            )

        except Exception as e:
            logger.error("Failed to get changes", error=str(e), query_params=query_params.dict())
            raise



    async def health_check(self) -> Dict:
        """
        Perform database health check.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Test basic connectivity
            await self.database.command("ping")
            
            # Test collections exist and are accessible
            books_count = await self.books_collection.count_documents({})
            changes_count = await self.changes_collection.count_documents({})
            
            return {
                "status": "healthy",
                "books_collection": "accessible",
                "changes_collection": "accessible",
                "books_count": books_count,
                "changes_count": changes_count
            }
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }

