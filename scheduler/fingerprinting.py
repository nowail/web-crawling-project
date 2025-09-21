"""
Content fingerprinting system for efficient change detection.

This module provides:
- Content hashing for change detection
- Fingerprint generation and comparison
- Optimized change detection algorithms
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from decimal import Decimal

import structlog
from pydantic import HttpUrl

from scheduler.models import ContentFingerprint, ChangeType, ChangeSeverity
from crawler.models import BookData

logger = structlog.get_logger(__name__)


class ContentFingerprinter:
    """Content fingerprinting system for change detection."""
    
    def __init__(self, fingerprint_fields: List[str] = None):
        """
        Initialize the fingerprinting system.
        
        Args:
            fingerprint_fields: List of fields to include in fingerprint
        """
        self.fingerprint_fields = fingerprint_fields or [
            "name", "description", "category", "price_including_tax", 
            "availability", "rating", "number_of_reviews"
        ]
        self.logger = logger.bind(component="fingerprinter")
    
    def generate_content_hash(self, book_data: BookData) -> str:
        """
        Generate SHA-256 hash of book content for change detection.
        
        Args:
            book_data: BookData instance to fingerprint
            
        Returns:
            SHA-256 hash string
        """
        try:
            # Extract relevant fields for hashing
            content_data = {}
            for field in self.fingerprint_fields:
                if hasattr(book_data, field):
                    value = getattr(book_data, field)
                    # Convert to string for consistent hashing
                    if isinstance(value, Decimal):
                        content_data[field] = str(value)
                    elif isinstance(value, datetime):
                        content_data[field] = value.isoformat()
                    elif isinstance(value, HttpUrl):
                        content_data[field] = str(value)
                    else:
                        content_data[field] = str(value)
            
            # Sort keys for consistent hashing
            sorted_data = json.dumps(content_data, sort_keys=True, ensure_ascii=False)
            
            # Generate SHA-256 hash
            content_hash = hashlib.sha256(sorted_data.encode('utf-8')).hexdigest()
            
            self.logger.debug(
                "Generated content hash",
                book_name=book_data.name,
                hash=content_hash[:16] + "...",
                fields_hashed=len(content_data)
            )
            
            return content_hash
            
        except Exception as e:
            self.logger.error(
                "Failed to generate content hash",
                book_name=book_data.name,
                error=str(e)
            )
            raise
    
    def generate_price_hash(self, book_data: BookData) -> str:
        """
        Generate hash specifically for price information.
        
        Args:
            book_data: BookData instance
            
        Returns:
            SHA-256 hash of price data
        """
        try:
            price_data = {
                "price_including_tax": str(book_data.price_including_tax),
                "price_excluding_tax": str(book_data.price_excluding_tax)
            }
            
            price_json = json.dumps(price_data, sort_keys=True)
            price_hash = hashlib.sha256(price_json.encode('utf-8')).hexdigest()
            
            self.logger.debug(
                "Generated price hash",
                book_name=book_data.name,
                hash=price_hash[:16] + "..."
            )
            
            return price_hash
            
        except Exception as e:
            self.logger.error(
                "Failed to generate price hash",
                book_name=book_data.name,
                error=str(e)
            )
            raise
    
    def generate_availability_hash(self, book_data: BookData) -> str:
        """
        Generate hash for availability information.
        
        Args:
            book_data: BookData instance
            
        Returns:
            SHA-256 hash of availability data
        """
        try:
            availability_data = {
                "availability": str(book_data.availability),
                "number_of_reviews": book_data.number_of_reviews
            }
            
            availability_json = json.dumps(availability_data, sort_keys=True)
            availability_hash = hashlib.sha256(availability_json.encode('utf-8')).hexdigest()
            
            self.logger.debug(
                "Generated availability hash",
                book_name=book_data.name,
                hash=availability_hash[:16] + "..."
            )
            
            return availability_hash
            
        except Exception as e:
            self.logger.error(
                "Failed to generate availability hash",
                book_name=book_data.name,
                error=str(e)
            )
            raise
    
    def generate_metadata_hash(self, book_data: BookData) -> str:
        """
        Generate hash for metadata (description, category, etc.).
        
        Args:
            book_data: BookData instance
            
        Returns:
            SHA-256 hash of metadata
        """
        try:
            metadata_data = {
                "description": book_data.description,
                "category": book_data.category,
                "rating": str(book_data.rating),
                "image_url": str(book_data.image_url)
            }
            
            metadata_json = json.dumps(metadata_data, sort_keys=True, ensure_ascii=False)
            metadata_hash = hashlib.sha256(metadata_json.encode('utf-8')).hexdigest()
            
            self.logger.debug(
                "Generated metadata hash",
                book_name=book_data.name,
                hash=metadata_hash[:16] + "..."
            )
            
            return metadata_hash
            
        except Exception as e:
            self.logger.error(
                "Failed to generate metadata hash",
                book_name=book_data.name,
                error=str(e)
            )
            raise
    
    def generate_complete_fingerprint(self, book_data: BookData) -> ContentFingerprint:
        """
        Generate complete fingerprint for a book.
        
        Args:
            book_data: BookData instance
            
        Returns:
            ContentFingerprint instance
        """
        try:
            book_id = self._generate_book_id(book_data)
            
            fingerprint = ContentFingerprint(
                book_id=book_id,
                source_url=book_data.source_url,
                content_hash=self.generate_content_hash(book_data),
                price_hash=self.generate_price_hash(book_data),
                availability_hash=self.generate_availability_hash(book_data),
                metadata_hash=self.generate_metadata_hash(book_data),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.logger.info(
                "Generated complete fingerprint",
                book_name=book_data.name,
                book_id=book_id
            )
            
            return fingerprint
            
        except Exception as e:
            self.logger.error(
                "Failed to generate complete fingerprint",
                book_name=book_data.name,
                error=str(e)
            )
            raise
    
    def compare_fingerprints(
        self, 
        old_fingerprint: ContentFingerprint, 
        new_fingerprint: ContentFingerprint
    ) -> List[Tuple[ChangeType, ChangeSeverity, str]]:
        """
        Compare two fingerprints and detect changes.
        
        Args:
            old_fingerprint: Previous fingerprint
            new_fingerprint: Current fingerprint
            
        Returns:
            List of (change_type, severity, description) tuples
        """
        changes = []
        
        try:
            # Compare content hash (overall changes)
            if old_fingerprint.content_hash != new_fingerprint.content_hash:
                changes.append((
                    ChangeType.DESCRIPTION_CHANGE,
                    ChangeSeverity.MEDIUM,
                    "Content has changed"
                ))
            
            # Compare price hash
            if old_fingerprint.price_hash != new_fingerprint.price_hash:
                changes.append((
                    ChangeType.PRICE_CHANGE,
                    ChangeSeverity.HIGH,
                    "Price has changed"
                ))
            
            # Compare availability hash
            if old_fingerprint.availability_hash != new_fingerprint.availability_hash:
                changes.append((
                    ChangeType.AVAILABILITY_CHANGE,
                    ChangeSeverity.MEDIUM,
                    "Availability or reviews have changed"
                ))
            
            # Compare metadata hash
            if old_fingerprint.metadata_hash != new_fingerprint.metadata_hash:
                changes.append((
                    ChangeType.DESCRIPTION_CHANGE,
                    ChangeSeverity.LOW,
                    "Metadata has changed"
                ))
            
            self.logger.debug(
                "Compared fingerprints",
                book_id=old_fingerprint.book_id,
                changes_detected=len(changes)
            )
            
            return changes
            
        except Exception as e:
            self.logger.error(
                "Failed to compare fingerprints",
                book_id=old_fingerprint.book_id,
                error=str(e)
            )
            raise
    
    def _generate_book_id(self, book_data: BookData) -> str:
        """
        Generate unique book ID from source URL.
        
        Args:
            book_data: BookData instance
            
        Returns:
            Unique book identifier
        """
        # Use source URL as base for ID generation
        url_str = str(book_data.source_url)
        book_id = hashlib.md5(url_str.encode('utf-8')).hexdigest()
        return f"book_{book_id}"
    
    def get_changed_fields(
        self, 
        old_data: BookData, 
        new_data: BookData
    ) -> Dict[str, Tuple[Any, Any]]:
        """
        Get specific fields that have changed between two BookData instances.
        
        Args:
            old_data: Previous book data
            new_data: Current book data
            
        Returns:
            Dictionary of field_name -> (old_value, new_value)
        """
        changed_fields = {}
        
        try:
            for field in self.fingerprint_fields:
                if hasattr(old_data, field) and hasattr(new_data, field):
                    old_value = getattr(old_data, field)
                    new_value = getattr(new_data, field)
                    
                    if old_value != new_value:
                        changed_fields[field] = (old_value, new_value)
            
            self.logger.debug(
                "Detected field changes",
                book_name=new_data.name,
                changed_fields=list(changed_fields.keys())
            )
            
            return changed_fields
            
        except Exception as e:
            self.logger.error(
                "Failed to detect field changes",
                book_name=new_data.name,
                error=str(e)
            )
            raise


class FingerprintManager:
    """Manager for storing and retrieving content fingerprints."""
    
    def __init__(self, db_manager):
        """
        Initialize fingerprint manager.
        
        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self.fingerprinter = ContentFingerprinter()
        self.logger = logger.bind(component="fingerprint_manager")
    
    async def store_fingerprint(self, fingerprint: ContentFingerprint) -> bool:
        """
        Store fingerprint in database.
        
        Args:
            fingerprint: ContentFingerprint to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            fingerprint_dict = fingerprint.model_dump()
            fingerprint_dict['source_url'] = str(fingerprint_dict['source_url'])
            
            await self.db_manager.database.fingerprints.insert_one(fingerprint_dict)
            
            self.logger.debug(
                "Stored fingerprint",
                book_id=fingerprint.book_id
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to store fingerprint",
                book_id=fingerprint.book_id,
                error=str(e)
            )
            return False
    
    async def get_fingerprint(self, book_id: str) -> Optional[ContentFingerprint]:
        """
        Retrieve fingerprint from database.
        
        Args:
            book_id: Book identifier
            
        Returns:
            ContentFingerprint if found, None otherwise
        """
        try:
            fingerprint_doc = await self.db_manager.database.fingerprints.find_one(
                {"book_id": book_id}
            )
            
            if fingerprint_doc:
                # Convert string URL back to HttpUrl
                fingerprint_doc['source_url'] = HttpUrl(fingerprint_doc['source_url'])
                return ContentFingerprint(**fingerprint_doc)
            
            return None
            
        except Exception as e:
            self.logger.error(
                "Failed to retrieve fingerprint",
                book_id=book_id,
                error=str(e)
            )
            return None
    
    async def fingerprint_exists_by_url(self, source_url: str) -> bool:
        """
        Check if a fingerprint exists for a given source URL.
        
        Args:
            source_url: Source URL to check
            
        Returns:
            True if fingerprint exists, False otherwise
        """
        try:
            # Check directly by source_url in fingerprints collection
            fingerprint_doc = await self.db_manager.database.fingerprints.find_one({
                "source_url": source_url
            })
            return fingerprint_doc is not None
            
        except Exception as e:
            self.logger.error(
                "Failed to check fingerprint existence by URL",
                source_url=source_url,
                error=str(e)
            )
            return False
    
    async def get_fingerprint_by_url(self, source_url: str) -> Optional[ContentFingerprint]:
        """
        Get fingerprint by source URL.
        
        Args:
            source_url: Source URL to look up
            
        Returns:
            ContentFingerprint if found, None otherwise
        """
        try:
            fingerprint_doc = await self.db_manager.database.fingerprints.find_one({
                "source_url": source_url
            })
            
            if fingerprint_doc:
                # Convert source_url back to HttpUrl for Pydantic validation
                fingerprint_doc['source_url'] = HttpUrl(fingerprint_doc['source_url'])
                return ContentFingerprint(**fingerprint_doc)
            return None
            
        except Exception as e:
            self.logger.error(
                "Failed to retrieve fingerprint by URL",
                source_url=source_url,
                error=str(e)
            )
            return None
    
    async def update_fingerprint(self, fingerprint: ContentFingerprint) -> bool:
        """
        Update existing fingerprint in database, or create if it doesn't exist.
        
        Args:
            fingerprint: Updated ContentFingerprint
            
        Returns:
            True if successful, False otherwise
        """
        try:
            fingerprint_dict = fingerprint.model_dump()
            fingerprint_dict['source_url'] = str(fingerprint_dict['source_url'])
            fingerprint_dict['updated_at'] = datetime.utcnow()
            
            result = await self.db_manager.database.fingerprints.update_one(
                {"book_id": fingerprint.book_id},
                {"$set": fingerprint_dict},
                upsert=True  # Create if doesn't exist
            )
            
            if result.modified_count > 0:
                self.logger.info(
                    "Updated existing fingerprint",
                    book_id=fingerprint.book_id,
                    source_url=str(fingerprint.source_url)
                )
            elif result.upserted_id is not None:
                self.logger.info(
                    "Created new fingerprint",
                    book_id=fingerprint.book_id,
                    source_url=str(fingerprint.source_url)
                )
            else:
                self.logger.debug(
                    "Fingerprint unchanged",
                    book_id=fingerprint.book_id
                )
            
            return True  # Always return True since upsert=True ensures success
            
        except Exception as e:
            self.logger.error(
                "Failed to update fingerprint",
                book_id=fingerprint.book_id,
                error=str(e)
            )
            return False
    
    async def delete_fingerprint(self, book_id: str) -> bool:
        """
        Delete a fingerprint by book_id.
        
        Args:
            book_id: Book identifier
            
        Returns:
            True if deleted, False if not found
        """
        try:
            result = await self.db_manager.database.fingerprints.delete_one(
                {"book_id": book_id}
            )
            
            if result.deleted_count > 0:
                self.logger.info(
                    "Successfully deleted fingerprint",
                    book_id=book_id
                )
                return True
            else:
                self.logger.warning(
                    "Fingerprint not found for deletion",
                    book_id=book_id
                )
                return False
                
        except Exception as e:
            self.logger.error(
                "Failed to delete fingerprint",
                book_id=book_id,
                error=str(e)
            )
            return False
    
    async def get_all_fingerprints(self) -> List[ContentFingerprint]:
        """
        Retrieve all fingerprints from database.
        
        Returns:
            List of ContentFingerprint instances
        """
        try:
            cursor = self.db_manager.database.fingerprints.find({})
            fingerprints = []
            
            async for doc in cursor:
                doc['source_url'] = HttpUrl(doc['source_url'])
                fingerprints.append(ContentFingerprint(**doc))
            
            self.logger.debug(
                "Retrieved all fingerprints",
                count=len(fingerprints)
            )
            
            return fingerprints
            
        except Exception as e:
            self.logger.error(
                "Failed to retrieve all fingerprints",
                error=str(e)
            )
            return []
    
    async def cleanup_orphaned_fingerprints(self) -> int:
        """
        Remove fingerprints that don't have corresponding books in the books collection.
        
        Returns:
            Number of orphaned fingerprints removed
        """
        try:
            # Get all fingerprints
            fingerprints = await self.get_all_fingerprints()
            orphaned_count = 0
            
            for fingerprint in fingerprints:
                # Check if book exists in books collection
                book_exists = await self.db_manager.collection.find_one({
                    "source_url": str(fingerprint.source_url)
                })
                
                if not book_exists:
                    # Book doesn't exist, remove fingerprint
                    deleted = await self.delete_fingerprint(fingerprint.book_id)
                    if deleted:
                        orphaned_count += 1
                        self.logger.info(
                            "Removed orphaned fingerprint",
                            book_id=fingerprint.book_id,
                            source_url=str(fingerprint.source_url)
                        )
            
            if orphaned_count > 0:
                self.logger.info(
                    "Cleanup completed",
                    orphaned_fingerprints_removed=orphaned_count
                )
            else:
                self.logger.debug("No orphaned fingerprints found")
            
            return orphaned_count
            
        except Exception as e:
            self.logger.error("Failed to cleanup orphaned fingerprints", error=str(e))
            return 0

