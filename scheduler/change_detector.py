"""
Change detection engine for monitoring book data changes.

This module provides:
- Change detection algorithms
- Comparison logic for book data
- Change classification and severity assessment
- Integration with fingerprinting system
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog
from pydantic import HttpUrl

from scheduler.models import (
    ChangeLog, ChangeType, ChangeSeverity, ChangeDetectionResult
)
from scheduler.fingerprinting import ContentFingerprinter, FingerprintManager
from crawler.models import BookData
from crawler.book_crawler import BookCrawler

logger = structlog.get_logger(__name__)


class ChangeDetector:
    """Engine for detecting changes in book data."""
    
    def __init__(self, db_manager, fingerprint_manager: FingerprintManager):
        """
        Initialize change detector.
        
        Args:
            db_manager: Database manager instance
            fingerprint_manager: Fingerprint manager instance
        """
        self.db_manager = db_manager
        self.fingerprint_manager = fingerprint_manager
        self.fingerprinter = ContentFingerprinter()
        self.logger = logger.bind(component="change_detector")
    
    async def detect_changes(
        self, 
        max_books: Optional[int] = None,
        batch_size: int = 100,
        verbose: bool = True
    ) -> ChangeDetectionResult:
        """
        Detect changes in book data by comparing current vs stored data.
        
        Args:
            max_books: Maximum number of books to check (None for all)
            batch_size: Number of books to process in each batch
            
        Returns:
            ChangeDetectionResult with detection summary
        """
        detection_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        if verbose:
            self.logger.info(
                "Starting change detection",
                detection_id=detection_id,
                max_books=max_books,
                batch_size=batch_size
            )
        
        try:
            # First, cleanup orphaned fingerprints
            if verbose:
                self.logger.info("Starting fingerprint cleanup before change detection")
            orphaned_count = await self.fingerprint_manager.cleanup_orphaned_fingerprints()
            if orphaned_count > 0:
                self.logger.info(f"Cleaned up {orphaned_count} orphaned fingerprints")
            
            # Get all stored books
            stored_books = await self._get_stored_books(max_books, verbose)
            total_books = len(stored_books)
            
            if total_books == 0:
                self.logger.warning("No stored books found for change detection")
                return ChangeDetectionResult(
                    detection_id=detection_id,
                    total_books_checked=0,
                    success=True
                )
            
            # Check for missing books and re-crawl if needed
            missing_books_count = await self._detect_and_restore_missing_books(verbose)
            if missing_books_count > 0:
                self.logger.info(f"Restored {missing_books_count} missing books")
                # Re-fetch stored books after restoration
                stored_books = await self._get_stored_books(max_books, verbose)
                total_books = len(stored_books)
            
            # Check for new books that exist on website but not in database
            new_books_count = await self._detect_new_books(verbose)
            if new_books_count > 0:
                self.logger.info(f"Found {new_books_count} new books")
                # Re-fetch stored books after adding new ones
                stored_books = await self._get_stored_books(max_books, verbose)
                total_books = len(stored_books)
            
            # Initialize result tracking
            changes_detected = 0
            new_books = 0
            updated_books = 0
            removed_books = 0
            restored_books = missing_books_count
            changes_by_type = {}
            changes_by_severity = {}
            errors = []
            
            # Process books in batches
            for i in range(0, total_books, batch_size):
                batch = stored_books[i:i + batch_size]
                batch_result = await self._process_batch(batch, detection_id)
                
                # Aggregate results
                changes_detected += batch_result['changes_detected']
                new_books += batch_result['new_books']
                updated_books += batch_result['updated_books']
                removed_books += batch_result['removed_books']
                errors.extend(batch_result['errors'])
                
                # Merge change type and severity counts
                for change_type, count in batch_result['changes_by_type'].items():
                    changes_by_type[change_type] = changes_by_type.get(change_type, 0) + count
                
                for severity, count in batch_result['changes_by_severity'].items():
                    changes_by_severity[severity] = changes_by_severity.get(severity, 0) + count
                
                # Log progress (only if verbose)
                if verbose:
                    self.logger.info(
                        "Processed batch",
                        batch_start=i,
                        batch_end=min(i + batch_size, total_books),
                        total_books=total_books,
                        changes_in_batch=batch_result['changes_detected']
                    )
                else:
                    # Show progress even in non-verbose mode for run-once
                    progress = min(i + batch_size, total_books)
                    print(f"📊 Progress: {progress}/{total_books} books processed ({progress/total_books*100:.1f}%)")
            
            # Calculate performance metrics
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            avg_processing_time = duration / total_books if total_books > 0 else 0
            
            result = ChangeDetectionResult(
                detection_id=detection_id,
                run_timestamp=start_time,
                total_books_checked=total_books,
                changes_detected=changes_detected,
                new_books=new_books + restored_books + new_books_count,  # Include restored and discovered books
                updated_books=updated_books,
                removed_books=removed_books,
                detection_duration_seconds=duration,
                average_book_processing_time=avg_processing_time,
                changes_by_type=changes_by_type,
                changes_by_severity=changes_by_severity,
                success=len(errors) == 0,
                errors=errors
            )
            
            # Store detection result
            await self._store_detection_result(result)
            
            self.logger.info(
                "Change detection completed",
                detection_id=detection_id,
                total_books=total_books,
                changes_detected=changes_detected,
                restored_books=restored_books,
                duration_seconds=duration
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Change detection failed",
                detection_id=detection_id,
                error=str(e)
            )
            
            return ChangeDetectionResult(
                detection_id=detection_id,
                run_timestamp=start_time,
                success=False,
                errors=[str(e)]
            )
    
    async def _get_stored_books(self, max_books: Optional[int] = None, verbose: bool = True) -> List[Dict[str, Any]]:
        """Get stored books from database."""
        try:
            query = {}
            if max_books:
                cursor = self.db_manager.collection.find(query).limit(max_books)
            else:
                cursor = self.db_manager.collection.find(query)
            
            books = []
            async for book in cursor:
                books.append(book)
            
            if verbose:
                self.logger.debug(
                    "Retrieved stored books",
                    count=len(books),
                    max_books=max_books
                )
            
            return books
            
        except Exception as e:
            self.logger.error(
                "Failed to retrieve stored books",
                error=str(e)
            )
            raise
    
    async def _process_batch(
        self, 
        stored_books: List[Dict[str, Any]], 
        detection_id: str
    ) -> Dict[str, Any]:
        """Process a batch of books for change detection."""
        changes_detected = 0
        new_books = 0
        updated_books = 0
        removed_books = 0
        changes_by_type = {}
        changes_by_severity = {}
        errors = []
        
        try:
            # Create crawler for fetching current data
            crawler = BookCrawler(self.db_manager)
            
            for stored_book in stored_books:
                try:
                    # Convert stored book to BookData
                    stored_book_data = self._dict_to_book_data(stored_book)
                    
                    # Fetch current book data
                    current_book_data = await self._fetch_current_book_data(
                        crawler, stored_book_data.source_url
                    )
                    
                    if current_book_data is None:
                        # Book no longer exists
                        await self._handle_removed_book(stored_book_data, detection_id)
                        removed_books += 1
                        changes_detected += 1
                        continue
                    
                    # Check if fingerprint exists for this book
                    fingerprint_exists = await self.fingerprint_manager.fingerprint_exists_by_url(str(current_book_data.source_url))
                    
                    # Compare stored vs current data
                    changes = await self._compare_book_data(
                        stored_book_data, current_book_data, detection_id
                    )
                    
                    if changes:
                        changes_detected += len(changes)
                        updated_books += 1
                        
                        # Update change type and severity counts
                        for change in changes:
                            change_type = change.change_type
                            severity = change.severity
                            
                            changes_by_type[change_type] = changes_by_type.get(change_type, 0) + 1
                            changes_by_severity[severity] = changes_by_severity.get(severity, 0) + 1
                        
                        # Update stored book data
                        await self._update_stored_book(current_book_data)
                        
                        # Update fingerprint only when changes are detected
                        new_fingerprint = self.fingerprinter.generate_complete_fingerprint(current_book_data)
                        await self.fingerprint_manager.update_fingerprint(new_fingerprint)
                    elif not fingerprint_exists:
                        # No changes detected, but no fingerprint exists - create one
                        # This handles the case where a book exists but has no fingerprint
                        new_fingerprint = self.fingerprinter.generate_complete_fingerprint(current_book_data)
                        await self.fingerprint_manager.store_fingerprint(new_fingerprint)
                        self.logger.debug(
                            "Created missing fingerprint for existing book",
                            book_name=current_book_data.name,
                            source_url=str(current_book_data.source_url)
                        )
                    
                except Exception as e:
                    error_msg = f"Error processing book {stored_book.get('name', 'unknown')}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(
                        "Error processing book",
                        book_name=stored_book.get('name', 'unknown'),
                        error=str(e)
                    )
            
            return {
                'changes_detected': changes_detected,
                'new_books': new_books,
                'updated_books': updated_books,
                'removed_books': removed_books,
                'changes_by_type': changes_by_type,
                'changes_by_severity': changes_by_severity,
                'errors': errors
            }
            
        except Exception as e:
            self.logger.error(
                "Error processing batch",
                error=str(e)
            )
            errors.append(f"Batch processing error: {str(e)}")
            
            return {
                'changes_detected': 0,
                'new_books': 0,
                'updated_books': 0,
                'removed_books': 0,
                'changes_by_type': {},
                'changes_by_severity': {},
                'errors': errors
            }
    
    async def _fetch_current_book_data(
        self, 
        crawler: BookCrawler, 
        source_url: HttpUrl
    ) -> Optional[BookData]:
        """Fetch current book data from the web."""
        try:
            # Use crawler's method to fetch book details
            # This is a simplified version - in practice, you'd extract the specific book
            # from the crawler's existing methods
            current_data = await crawler._fetch_book_details_from_url(source_url)
            return current_data
            
        except Exception as e:
            self.logger.warning(
                "Failed to fetch current book data",
                source_url=str(source_url),
                error=str(e)
            )
            return None
    
    async def _compare_book_data(
        self, 
        stored_data: BookData, 
        current_data: BookData, 
        detection_id: str
    ) -> List[ChangeLog]:
        """Compare stored and current book data to detect changes using fingerprint optimization."""
        changes = []
        
        try:
            book_id = self.fingerprinter._generate_book_id(current_data)
            
            # Try to use fingerprint comparison first (FAST)
            old_fingerprint = await self.fingerprint_manager.get_fingerprint(book_id)
            
            if old_fingerprint:
                # Use optimized fingerprint comparison
                new_fingerprint = self.fingerprinter.generate_complete_fingerprint(current_data)
                fingerprint_changes = self.fingerprinter.compare_fingerprints(old_fingerprint, new_fingerprint)
                
                if fingerprint_changes:
                    # Fingerprints differ - need to get specific field changes
                    changed_fields = self.fingerprinter.get_changed_fields(stored_data, current_data)
                    
                    for field_name, (old_value, new_value) in changed_fields.items():
                        # Determine change type and severity
                        change_type, severity = self._classify_change(field_name, old_value, new_value)
                        
                        # Create change log
                        change_log = ChangeLog(
                            change_id=str(uuid.uuid4()),
                            book_id=book_id,
                            source_url=current_data.source_url,
                            change_type=change_type,
                            severity=severity,
                            old_value=old_value,
                            new_value=new_value,
                            field_name=field_name,
                            change_summary=f"{field_name} changed from '{old_value}' to '{new_value}'",
                            confidence_score=1.0
                        )
                        
                        changes.append(change_log)
                        
                        # Store change log
                        await self._store_change_log(change_log)
                else:
                    # No changes detected via fingerprint comparison (FAST PATH)
                    self.logger.debug(
                        "No changes detected via fingerprint comparison",
                        book_name=current_data.name,
                        book_id=book_id
                    )
            else:
                # No fingerprint exists - fall back to field-by-field comparison (SLOW)
                self.logger.debug(
                    "No fingerprint found, using field-by-field comparison",
                    book_name=current_data.name,
                    book_id=book_id
                )
                
                changed_fields = self.fingerprinter.get_changed_fields(stored_data, current_data)
                
                for field_name, (old_value, new_value) in changed_fields.items():
                    # Determine change type and severity
                    change_type, severity = self._classify_change(field_name, old_value, new_value)
                    
                    # Create change log
                    change_log = ChangeLog(
                        change_id=str(uuid.uuid4()),
                        book_id=book_id,
                        source_url=current_data.source_url,
                        change_type=change_type,
                        severity=severity,
                        old_value=old_value,
                        new_value=new_value,
                        field_name=field_name,
                        change_summary=f"{field_name} changed from '{old_value}' to '{new_value}'",
                        confidence_score=1.0
                    )
                    
                    changes.append(change_log)
                    
                    # Store change log
                    await self._store_change_log(change_log)
            
            self.logger.debug(
                "Compared book data",
                book_name=current_data.name,
                changes_detected=len(changes)
            )
            
            return changes
            
        except Exception as e:
            self.logger.error(
                "Failed to compare book data",
                book_name=current_data.name,
                error=str(e)
            )
            raise
    
    def _classify_change(
        self, 
        field_name: str, 
        old_value: Any, 
        new_value: Any
    ) -> Tuple[ChangeType, ChangeSeverity]:
        """Classify change type and severity based on field and values."""
        
        # Price changes are high severity
        if field_name in ['price_including_tax', 'price_excluding_tax']:
            return ChangeType.PRICE_CHANGE, ChangeSeverity.HIGH
        
        # Availability changes are medium severity
        elif field_name == 'availability':
            return ChangeType.AVAILABILITY_CHANGE, ChangeSeverity.MEDIUM
        
        # Rating changes are medium severity
        elif field_name == 'rating':
            return ChangeType.RATING_CHANGE, ChangeSeverity.MEDIUM
        
        # Review count changes are low severity
        elif field_name == 'number_of_reviews':
            return ChangeType.REVIEWS_CHANGE, ChangeSeverity.LOW
        
        # Category changes are medium severity
        elif field_name == 'category':
            return ChangeType.CATEGORY_CHANGE, ChangeSeverity.MEDIUM
        
        # Image URL changes are low severity
        elif field_name == 'image_url':
            return ChangeType.IMAGE_CHANGE, ChangeSeverity.LOW
        
        # Description changes are low severity
        elif field_name == 'description':
            return ChangeType.DESCRIPTION_CHANGE, ChangeSeverity.LOW
        
        # Name changes are high severity (rare but important)
        elif field_name == 'name':
            return ChangeType.DESCRIPTION_CHANGE, ChangeSeverity.HIGH
        
        # Default to description change with low severity
        else:
            return ChangeType.DESCRIPTION_CHANGE, ChangeSeverity.LOW
    
    async def _handle_removed_book(self, book_data: BookData, detection_id: str) -> None:
        """Handle a book that has been removed from the site."""
        try:
            change_log = ChangeLog(
                change_id=str(uuid.uuid4()),
                book_id=self.fingerprinter._generate_book_id(book_data),
                source_url=book_data.source_url,
                change_type=ChangeType.BOOK_REMOVED,
                severity=ChangeSeverity.HIGH,
                old_value=book_data.name,
                new_value=None,
                field_name="book",
                change_summary=f"Book '{book_data.name}' has been removed from the site",
                confidence_score=1.0
            )
            
            await self._store_change_log(change_log)
            
            # Mark book as removed in database
            await self.db_manager.collection.update_one(
                {"source_url": str(book_data.source_url)},
                {"$set": {"crawl_status": "removed", "updated_at": datetime.utcnow()}}
            )
            
            self.logger.info(
                "Handled removed book",
                book_name=book_data.name,
                source_url=str(book_data.source_url)
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to handle removed book",
                book_name=book_data.name,
                error=str(e)
            )
    
    async def _update_stored_book(self, book_data: BookData) -> None:
        """Update stored book data in database."""
        try:
            book_dict = book_data.model_dump()
            book_dict['price_including_tax'] = float(book_dict['price_including_tax'])
            book_dict['price_excluding_tax'] = float(book_dict['price_excluding_tax'])
            book_dict['image_url'] = str(book_dict['image_url'])
            book_dict['source_url'] = str(book_dict['source_url'])
            book_dict['updated_at'] = datetime.utcnow()
            
            await self.db_manager.collection.update_one(
                {"source_url": str(book_data.source_url)},
                {"$set": book_dict}
            )
            
            self.logger.debug(
                "Updated stored book",
                book_name=book_data.name
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to update stored book",
                book_name=book_data.name,
                error=str(e)
            )
    
    async def _store_change_log(self, change_log: ChangeLog) -> None:
        """Store change log in database."""
        try:
            change_dict = change_log.model_dump()
            change_dict['source_url'] = str(change_dict['source_url'])
            
            # Convert Decimal values to float for MongoDB compatibility
            if 'old_value' in change_dict and change_dict['old_value'] is not None:
                if hasattr(change_dict['old_value'], '__float__'):
                    change_dict['old_value'] = float(change_dict['old_value'])
            if 'new_value' in change_dict and change_dict['new_value'] is not None:
                if hasattr(change_dict['new_value'], '__float__'):
                    change_dict['new_value'] = float(change_dict['new_value'])
            
            await self.db_manager.database.change_logs.insert_one(change_dict)
            
            self.logger.debug(
                "Stored change log",
                change_id=change_log.change_id,
                change_type=change_log.change_type
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to store change log",
                change_id=change_log.change_id,
                error=str(e)
            )
    
    async def _store_detection_result(self, result: ChangeDetectionResult) -> None:
        """Store detection result in database."""
        try:
            result_dict = result.model_dump()
            await self.db_manager.database.detection_results.insert_one(result_dict)
            
            self.logger.debug(
                "Stored detection result",
                detection_id=result.detection_id
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to store detection result",
                detection_id=result.detection_id,
                error=str(e)
            )
    
    def _dict_to_book_data(self, book_dict: Dict[str, Any]) -> BookData:
        """Convert database document to BookData instance."""
        try:
            # Convert string URLs back to HttpUrl
            if 'image_url' in book_dict and book_dict['image_url']:
                book_dict['image_url'] = HttpUrl(book_dict['image_url'])
            if 'source_url' in book_dict and book_dict['source_url']:
                book_dict['source_url'] = HttpUrl(book_dict['source_url'])
            
            return BookData(**book_dict)
            
        except Exception as e:
            self.logger.error(
                "Failed to convert dict to BookData",
                book_name=book_dict.get('name', 'unknown'),
                error=str(e)
            )
            raise
    
    async def _detect_and_restore_missing_books(self, verbose: bool = True) -> int:
        """Detect missing books by comparing with expected book count and restore them."""
        try:
            if verbose:
                self.logger.info("Checking for missing books...")
            
            # Get current book count
            current_count = await self.db_manager.collection.count_documents({})
            
            # Expected book count (you can adjust this based on your knowledge of the site)
            # For books.toscrape.com, there should be around 1000 books
            expected_count = 1000
            
            if current_count >= expected_count:
                if verbose:
                    self.logger.info(f"Book count looks good: {current_count} books")
                return 0
            
            missing_count = expected_count - current_count
            if verbose:
                self.logger.info(f"Detected {missing_count} missing books. Starting restoration...")
            
            # Use the crawler to find and restore missing books
            restored_count = await self._restore_missing_books(missing_count, verbose)
            
            return restored_count
            
        except Exception as e:
            self.logger.error(f"Error detecting missing books: {str(e)}")
            return 0
    
    async def _restore_missing_books(self, missing_count: int, verbose: bool = True) -> int:
        """Restore missing books by crawling the website."""
        try:
            from crawler.book_crawler import BookCrawler
            
            if verbose:
                self.logger.info(f"Starting restoration of {missing_count} missing books...")
            
            # Create a crawler instance
            crawler = BookCrawler(self.db_manager)
            
            # Get the main catalog page to find book URLs
            catalog_url = "https://books.toscrape.com/catalogue/page-1.html"
            
            restored_count = 0
            page_num = 1
            consecutive_errors = 0
            max_consecutive_errors = 5  # Stop after 5 consecutive page errors
            
            while restored_count < missing_count and page_num <= 50 and consecutive_errors < max_consecutive_errors:
                try:
                    if verbose:
                        print(f"📖 Checking page {page_num} for missing books...")
                    
                    # Get book URLs from the page
                    book_urls = await self._get_book_urls_from_page(catalog_url.replace("page-1", f"page-{page_num}"))
                    
                    if not book_urls:
                        consecutive_errors += 1
                        if verbose:
                            print(f"⚠️  No books found on page {page_num}, consecutive errors: {consecutive_errors}")
                        page_num += 1
                        continue
                    
                    # Reset consecutive errors if we got book URLs
                    consecutive_errors = 0
                    
                    for book_url in book_urls:
                        if restored_count >= missing_count:
                            break
                            
                        # Check if book already exists
                        existing_book = await self.db_manager.collection.find_one({
                            "source_url": str(book_url)
                        })
                        
                        if not existing_book:
                            # Book is missing, crawl it
                            try:
                                book_data = await crawler._fetch_book_details_from_url(book_url)
                                if book_data:
                                    # Insert the missing book
                                    book_dict = book_data.model_dump()
                                    book_dict['price_including_tax'] = float(book_dict['price_including_tax'])
                                    book_dict['price_excluding_tax'] = float(book_dict['price_excluding_tax'])
                                    book_dict['image_url'] = str(book_dict['image_url'])
                                    book_dict['source_url'] = str(book_dict['source_url'])
                                    book_dict['created_at'] = datetime.utcnow()
                                    book_dict['updated_at'] = datetime.utcnow()
                                    
                                    await self.db_manager.collection.insert_one(book_dict)
                                    restored_count += 1
                                    
                                    # Create fingerprint for the restored book
                                    book_id = self.fingerprinter._generate_book_id(book_data)
                                    new_fingerprint = self.fingerprinter.generate_complete_fingerprint(book_data)
                                    await self.fingerprint_manager.store_fingerprint(new_fingerprint)
                                    
                                    # Create change log for restored book
                                    change_log = ChangeLog(
                                        change_id=str(uuid.uuid4()),
                                        book_id=book_id,
                                        source_url=book_data.source_url,
                                        change_type=ChangeType.NEW_BOOK,
                                        severity=ChangeSeverity.MEDIUM,
                                        old_value=None,
                                        new_value=book_data.name,
                                        field_name="book_restored",
                                        detected_at=datetime.utcnow(),
                                        change_summary=f"Book restored: {book_data.name}",
                                        confidence_score=1.0
                                    )
                                    await self._store_change_log(change_log)
                                    
                                    if verbose:
                                        print(f"✅ Restored: {book_data.name} (fingerprint created)")
                                        
                            except Exception as e:
                                if verbose:
                                    print(f"❌ Failed to restore book from {book_url}: {str(e)}")
                    
                    page_num += 1
                    
                except Exception as e:
                    consecutive_errors += 1
                    if verbose:
                        print(f"❌ Failed to process page {page_num}: {str(e)} (consecutive errors: {consecutive_errors})")
                    page_num += 1
                    continue
            
            if consecutive_errors >= max_consecutive_errors:
                if verbose:
                    print(f"⚠️  Stopping restoration due to {consecutive_errors} consecutive page errors")
            
            if verbose:
                self.logger.info(f"Restoration completed. Restored {restored_count} books.")
            
            return restored_count
            
        except Exception as e:
            self.logger.error(f"Error restoring missing books: {str(e)}")
            return 0
    
    async def _get_book_urls_from_page(self, page_url: str) -> List[HttpUrl]:
        """Get book URLs from a catalog page."""
        try:
            import httpx
            from bs4 import BeautifulSoup
            
            # Retry logic for network issues
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.get(page_url)
                        response.raise_for_status()
                        
                        soup = BeautifulSoup(response.content, 'html.parser')
                        book_links = soup.find_all('h3')
                        
                        book_urls = []
                        for link in book_links:
                            a_tag = link.find('a')
                            if a_tag and a_tag.get('href'):
                                book_url = HttpUrl(f"https://books.toscrape.com/catalogue/{a_tag['href']}")
                                book_urls.append(book_url)
                        
                        return book_urls
                        
                except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
                    if attempt < max_retries - 1:
                        self.logger.warning(f"Network error on attempt {attempt + 1} for {page_url}: {str(e)}. Retrying...")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        self.logger.error(f"Failed to get book URLs from page {page_url} after {max_retries} attempts: {str(e)}")
                        return []
                except Exception as e:
                    self.logger.error(f"Error getting book URLs from page {page_url}: {str(e)}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Unexpected error getting book URLs from page {page_url}: {str(e)}")
            return []
    
    async def _detect_new_books(self, verbose: bool = True) -> int:
        """Detect new books that exist on the website but not in our database."""
        try:
            from crawler.book_crawler import BookCrawler
            
            if verbose:
                self.logger.info("Checking for new books on the website...")
            
            # Create a crawler instance
            crawler = BookCrawler(self.db_manager)
            
            # Get the main catalog page to find book URLs
            catalog_url = "https://books.toscrape.com/catalogue/page-1.html"
            
            new_books_count = 0
            page_num = 1
            consecutive_errors = 0
            max_consecutive_errors = 5
            max_pages_to_check = 10  # Limit to avoid infinite loops
            
            while page_num <= max_pages_to_check and consecutive_errors < max_consecutive_errors:
                try:
                    if verbose:
                        print(f"🔍 Checking page {page_num} for new books...")
                    
                    # Get book URLs from the page
                    book_urls = await self._get_book_urls_from_page(catalog_url.replace("page-1", f"page-{page_num}"))
                    
                    if not book_urls:
                        consecutive_errors += 1
                        if verbose:
                            print(f"⚠️  No books found on page {page_num}, consecutive errors: {consecutive_errors}")
                        page_num += 1
                        continue
                    
                    # Reset consecutive errors if we got book URLs
                    consecutive_errors = 0
                    
                    for book_url in book_urls:
                        # Check if book already exists in our database
                        existing_book = await self.db_manager.collection.find_one({
                            "source_url": str(book_url)
                        })
                        
                        if not existing_book:
                            # Book doesn't exist in our database, crawl it
                            try:
                                book_data = await crawler._fetch_book_details_from_url(book_url)
                                if book_data:
                                    # Insert the new book
                                    book_dict = book_data.model_dump()
                                    book_dict['price_including_tax'] = float(book_dict['price_including_tax'])
                                    book_dict['price_excluding_tax'] = float(book_dict['price_excluding_tax'])
                                    book_dict['image_url'] = str(book_dict['image_url'])
                                    book_dict['source_url'] = str(book_dict['source_url'])
                                    book_dict['created_at'] = datetime.utcnow()
                                    book_dict['updated_at'] = datetime.utcnow()
                                    
                                    await self.db_manager.collection.insert_one(book_dict)
                                    new_books_count += 1
                                    
                                    # Create fingerprint for the new book
                                    book_id = self.fingerprinter._generate_book_id(book_data)
                                    new_fingerprint = self.fingerprinter.generate_complete_fingerprint(book_data)
                                    await self.fingerprint_manager.store_fingerprint(new_fingerprint)
                                    
                                    # Create change log for new book
                                    change_log = ChangeLog(
                                        change_id=str(uuid.uuid4()),
                                        book_id=book_id,
                                        source_url=book_data.source_url,
                                        change_type=ChangeType.NEW_BOOK,
                                        severity=ChangeSeverity.MEDIUM,
                                        old_value=None,
                                        new_value=book_data.name,
                                        field_name="new_book",
                                        detected_at=datetime.utcnow(),
                                        change_summary=f"New book discovered: {book_data.name}",
                                        confidence_score=1.0
                                    )
                                    await self._store_change_log(change_log)
                                    
                                    if verbose:
                                        print(f"🆕 New book: {book_data.name} (fingerprint created)")
                                        
                            except Exception as e:
                                if verbose:
                                    print(f"❌ Failed to crawl new book from {book_url}: {str(e)}")
                    
                    page_num += 1
                    
                except Exception as e:
                    consecutive_errors += 1
                    if verbose:
                        print(f"❌ Failed to process page {page_num}: {str(e)} (consecutive errors: {consecutive_errors})")
                    page_num += 1
                    continue
            
            if verbose:
                self.logger.info(f"New book detection completed. Found {new_books_count} new books.")
            
            return new_books_count
            
        except Exception as e:
            self.logger.error(f"Error detecting new books: {str(e)}")
            return 0

