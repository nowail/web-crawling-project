"""
MongoDB database utilities for async operations.
Handles connection, indexing, and CRUD operations for book data.
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError, ConnectionFailure
import structlog

from .models import BookData, CrawlState, CrawlResult

logger = structlog.get_logger(__name__)


class MongoDBManager:
    """
    Async MongoDB manager for book data operations.
    Handles connection, indexing, and CRUD operations.
    """
    
    def __init__(self, connection_url: str, database_name: str, collection_name: str):
        """
        Initialize MongoDB manager.
        
        Args:
            connection_url: MongoDB connection URL
            database_name: Name of the database
            collection_name: Name of the collection
        """
        self.connection_url = connection_url
        self.database_name = database_name
        self.collection_name = collection_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self.collection: Optional[AsyncIOMotorCollection] = None
    
    async def connect(self) -> None:
        """Establish connection to MongoDB."""
        try:
            self.client = AsyncIOMotorClient(self.connection_url)
            self.database = self.client[self.database_name]
            self.collection = self.database[self.collection_name]
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB", 
                       database=self.database_name, 
                       collection=self.collection_name)
            
            # Create indexes for efficient querying
            await self._create_indexes()
            
        except ConnectionFailure as e:
            logger.error("Failed to connect to MongoDB", error=str(e))
            raise
    
    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def _create_indexes(self) -> None:
        """
        Create indexes for efficient querying and deduplication.
        Optimized for the most common query patterns.
        """
        try:
            # Index on source_url for deduplication (unique)
            await self.collection.create_index("source_url", unique=True)
            
            # Index on category for filtering
            await self.collection.create_index("category")
            
            # Index on availability for filtering
            await self.collection.create_index("availability")
            
            # Index on price for range queries
            await self.collection.create_index("price_including_tax")
            
            # Index on rating for filtering
            await self.collection.create_index("rating")
            
            # Index on crawl_timestamp for time-based queries
            await self.collection.create_index("crawl_timestamp")
            
            # Compound index for category and availability
            await self.collection.create_index([("category", 1), ("availability", 1)])
            
            # Compound index for price range queries
            await self.collection.create_index([("price_including_tax", 1), ("category", 1)])
            
            logger.info("Successfully created MongoDB indexes")
            
        except Exception as e:
            logger.error("Failed to create indexes", error=str(e))
            raise
    
    async def insert_book(self, book: BookData) -> bool:
        """
        Insert a single book into the database.
        
        Args:
            book: BookData instance to insert
            
        Returns:
            bool: True if successful, False if duplicate
        """
        try:
            book_dict = book.dict()
            # Convert Decimal to float and HttpUrl to string for MongoDB compatibility
            if 'price_including_tax' in book_dict:
                book_dict['price_including_tax'] = float(book_dict['price_including_tax'])
            if 'price_excluding_tax' in book_dict:
                book_dict['price_excluding_tax'] = float(book_dict['price_excluding_tax'])
            if 'image_url' in book_dict:
                book_dict['image_url'] = str(book_dict['image_url'])
            if 'source_url' in book_dict:
                book_dict['source_url'] = str(book_dict['source_url'])
            await self.collection.insert_one(book_dict)
            logger.debug("Successfully inserted book", book_name=book.name, url=str(book.source_url))
            
            # Create fingerprint for the book
            try:
                from scheduler.fingerprinting import FingerprintManager
                fingerprint_manager = FingerprintManager(self)
                fingerprint = fingerprint_manager.fingerprinter.generate_complete_fingerprint(book)
                await fingerprint_manager.store_fingerprint(fingerprint)
                logger.info("Successfully created fingerprint for new book", 
                          book_name=book.name, 
                          book_id=fingerprint.book_id,
                          source_url=str(book.source_url))
            except Exception as e:
                logger.error("Failed to create fingerprint for new book", 
                           book_name=book.name, 
                           source_url=str(book.source_url),
                           error=str(e))
            
            return True
            
        except DuplicateKeyError:
            logger.warning("Book already exists", book_name=book.name, url=str(book.source_url))
            return False
            
        except Exception as e:
            logger.error("Failed to insert book", book_name=book.name, error=str(e))
            raise
    
    async def insert_books_batch(self, books: List[BookData]) -> Dict[str, int]:
        """
        Insert multiple books in batch for efficiency.
        
        Args:
            books: List of BookData instances
            
        Returns:
            Dict with success and failure counts
        """
        if not books:
            return {"success": 0, "failed": 0, "duplicates": 0}
        
        success_count = 0
        failed_count = 0
        duplicate_count = 0
        
        # Convert to list of dicts and fix Decimal objects
        book_dicts = []
        for book in books:
            book_dict = book.dict()
            # Convert Decimal to float and HttpUrl to string for MongoDB compatibility
            if 'price_including_tax' in book_dict:
                book_dict['price_including_tax'] = float(book_dict['price_including_tax'])
            if 'price_excluding_tax' in book_dict:
                book_dict['price_excluding_tax'] = float(book_dict['price_excluding_tax'])
            if 'image_url' in book_dict:
                book_dict['image_url'] = str(book_dict['image_url'])
            if 'source_url' in book_dict:
                book_dict['source_url'] = str(book_dict['source_url'])
            book_dicts.append(book_dict)
        
        try:
            # Use ordered=False to continue on duplicate key errors
            result = await self.collection.insert_many(book_dicts, ordered=False)
            success_count = len(result.inserted_ids)
            
            # Calculate duplicates (total - success)
            duplicate_count = len(books) - success_count
            
            logger.info("Batch insert completed", 
                       total=len(books), 
                       success=success_count, 
                       duplicates=duplicate_count)
            
        except Exception as e:
            logger.error("Batch insert failed", error=str(e))
            failed_count = len(books)
        
        return {
            "success": success_count,
            "failed": failed_count,
            "duplicates": duplicate_count
        }
    
    async def get_book_by_url(self, source_url: str) -> Optional[BookData]:
        """
        Retrieve a book by its source URL.
        
        Args:
            source_url: Source URL of the book
            
        Returns:
            BookData instance or None if not found
        """
        try:
            book_dict = await self.collection.find_one({"source_url": source_url})
            if book_dict:
                # Remove MongoDB's _id field
                book_dict.pop('_id', None)
                return BookData(**book_dict)
            return None
            
        except Exception as e:
            logger.error("Failed to retrieve book", url=source_url, error=str(e))
            raise
    
    async def get_books_by_category(self, category: str, limit: int = 100) -> List[BookData]:
        """
        Retrieve books by category.
        
        Args:
            category: Book category
            limit: Maximum number of books to return
            
        Returns:
            List of BookData instances
        """
        try:
            cursor = self.collection.find({"category": category}).limit(limit)
            books = []
            
            async for book_dict in cursor:
                book_dict.pop('_id', None)
                books.append(BookData(**book_dict))
            
            logger.debug("Retrieved books by category", category=category, count=len(books))
            return books
            
        except Exception as e:
            logger.error("Failed to retrieve books by category", category=category, error=str(e))
            raise
    
    async def get_books_count(self) -> int:
        """Get total number of books in the collection."""
        try:
            count = await self.collection.count_documents({})
            return count
        except Exception as e:
            logger.error("Failed to get books count", error=str(e))
            raise
    
    async def get_categories(self) -> List[str]:
        """Get list of all unique categories."""
        try:
            categories = await self.collection.distinct("category")
            return sorted(categories)
        except Exception as e:
            logger.error("Failed to get categories", error=str(e))
            raise
    
    async def update_book(self, source_url: str, update_data: Dict[str, Any]) -> bool:
        """
        Update a book's data.
        
        Args:
            source_url: Source URL of the book to update
            update_data: Dictionary of fields to update
            
        Returns:
            bool: True if updated, False if not found
        """
        try:
            # Add update timestamp
            update_data["crawl_timestamp"] = datetime.utcnow()
            
            result = await self.collection.update_one(
                {"source_url": source_url},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.debug("Successfully updated book", url=source_url)
                return True
            else:
                logger.warning("Book not found for update", url=source_url)
            return False
            
        except Exception as e:
            logger.error("Failed to update book", url=source_url, error=str(e))
            raise
    
    async def update_book_by_id(self, book_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update a book's data by MongoDB _id.
        
        Args:
            book_id: MongoDB _id of the book to update
            update_data: Dictionary of fields to update
            
        Returns:
            bool: True if updated, False if not found
        """
        try:
            from bson import ObjectId
            
            # Add update timestamp
            update_data["updated_at"] = datetime.utcnow()
            
            result = await self.collection.update_one(
                {"_id": ObjectId(book_id)},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.debug("Successfully updated book by ID", book_id=book_id)
                return True
            else:
                logger.warning("Book not found for update", book_id=book_id)
                return False
                
        except Exception as e:
            logger.error("Failed to update book by ID", book_id=book_id, error=str(e))
            raise
    
    async def get_random_book(self) -> Optional[Dict[str, Any]]:
        """
        Get a random book from the database.
        
        Returns:
            Random book document or None if no books found
        """
        try:
            # Use MongoDB's $sample aggregation to get a random document
            pipeline = [{"$sample": {"size": 1}}]
            cursor = self.collection.aggregate(pipeline)
            book = await cursor.to_list(length=1)
            
            if book:
                return book[0]
            else:
                return None
                
        except Exception as e:
            logger.error("Failed to get random book", error=str(e))
            raise
    
    async def get_book_by_id(self, book_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a book by MongoDB _id.
        
        Args:
            book_id: MongoDB _id of the book
            
        Returns:
            Book document or None if not found
        """
        try:
            from bson import ObjectId
            
            book = await self.collection.find_one({"_id": ObjectId(book_id)})
            return book
            
        except Exception as e:
            logger.error("Failed to get book by ID", book_id=book_id, error=str(e))
            raise
    
    async def delete_book(self, source_url: str) -> bool:
        """
        Delete a book by source URL and its associated fingerprint.
        
        Args:
            source_url: Source URL of the book to delete
            
        Returns:
            bool: True if deleted, False if not found
        """
        try:
            # First, delete the book
            result = await self.collection.delete_one({"source_url": source_url})
            
            if result.deleted_count > 0:
                logger.debug("Successfully deleted book", url=source_url)
                
                # Delete associated fingerprint
                try:
                    from scheduler.fingerprinting import FingerprintManager
                    fingerprint_manager = FingerprintManager(self)
                    
                    # Generate book_id from source_url
                    import hashlib
                    book_id = f"book_{hashlib.md5(source_url.encode('utf-8')).hexdigest()}"
                    
                    # Delete the fingerprint
                    fingerprint_deleted = await fingerprint_manager.delete_fingerprint(book_id)
                    
                    if fingerprint_deleted:
                        logger.info("Successfully deleted book and its fingerprint", 
                                  url=source_url, book_id=book_id)
                    else:
                        logger.warning("Book deleted but fingerprint not found", 
                                     url=source_url, book_id=book_id)
                        
                except Exception as e:
                    logger.error("Failed to delete fingerprint after book deletion", 
                               url=source_url, error=str(e))
                    # Don't fail the book deletion if fingerprint deletion fails
                
                return True
            else:
                logger.warning("Book not found for deletion", url=source_url)
                return False
                
        except Exception as e:
            logger.error("Failed to delete book", url=source_url, error=str(e))
            raise
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics for monitoring."""
        try:
            stats = await self.database.command("dbStats")
            collection_stats = await self.collection.estimated_document_count()
            
            return {
                "database_size": stats.get("dataSize", 0),
                "total_books": collection_stats,
                "categories": await self.get_categories(),
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get database stats", error=str(e))
            raise
