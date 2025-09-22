"""
Main async crawler for books.toscrape.com.
Implements robust crawling with retry logic, pagination, and error handling.
"""

import asyncio
import json
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from asyncio_throttle import Throttler
import structlog

from .models import BookData, CrawlState, CrawlResult, BookAvailability, BookRating, CrawlStatus
from .database import MongoDBManager
from utilities.config import config
from utilities.logger import CrawlLogger

logger = structlog.get_logger(__name__)


class BookCrawler:
    """
    Async crawler for books.toscrape.com with robust error handling and resumability.
    """
    
    def __init__(self, db_manager: MongoDBManager):
        """
        Initialize the crawler.
        
        Args:
            db_manager: MongoDB manager instance
        """
        self.db_manager = db_manager
        self.crawl_logger = CrawlLogger("book_crawler")
        self.throttler = Throttler(rate_limit=config.rate_limit_per_second)
        self.state_file = config.get_state_file_path()
        self.crawl_state: Optional[CrawlState] = None
        self.errors: List[str] = []
        
        # HTTP client configuration
        self.client_config = {
            "timeout": config.request_timeout,
            "headers": config.get_headers(),
            "follow_redirects": True,
            "limits": httpx.Limits(max_keepalive_connections=20, max_connections=100)
        }
    
    async def crawl_all_books(self, resume: bool = True) -> CrawlResult:
        """
        Crawl all books from books.toscrape.com.
        
        Args:
            resume: Whether to resume from last successful crawl
            
        Returns:
            CrawlResult with crawl statistics
        """
        start_time = datetime.utcnow()
        self.crawl_logger.bind_context(operation="crawl_all_books")
        
        try:
            # Load or initialize crawl state
            if resume and self.state_file.exists():
                await self._load_crawl_state()
            else:
                self.crawl_state = CrawlState()
            
            self.crawl_logger.log_crawl_start(config.base_url)
            
            # Get total pages first
            total_pages = await self._get_total_pages()
            self.crawl_state.total_pages = total_pages
            
            # Process pages
            books_processed = 0
            async with httpx.AsyncClient(**self.client_config) as client:
                for page_num in range(self.crawl_state.last_processed_page, total_pages + 1):
                    try:
                        page_books = await self._crawl_page(client, page_num)
                        books_processed += len(page_books)
                        
                        # Update state
                        self.crawl_state.last_processed_page = page_num
                        self.crawl_state.books_processed = books_processed
                        self.crawl_state.last_update_time = datetime.utcnow()
                        
                        # Save state periodically
                        if page_num % 10 == 0:
                            await self._save_crawl_state()
                        
                        # Log progress
                        self.crawl_logger.log_crawl_progress(
                            page_num, total_pages, books_processed
                        )
                        
                    except Exception as e:
                        error_msg = f"Failed to crawl page {page_num}: {str(e)}"
                        self.errors.append(error_msg)
                        self.crawl_logger.log_error(error_msg)
                        
                        # Continue with next page unless it's a critical error
                        if "connection" in str(e).lower():
                            await asyncio.sleep(5)  # Wait before retrying
                        continue
            
            # Final state save
            await self._save_crawl_state()
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            result = CrawlResult(
                success=len(self.errors) == 0,
                books_crawled=books_processed,
                errors=self.errors,
                duration_seconds=duration,
                start_time=start_time,
                end_time=end_time
            )
            
            self.crawl_logger.log_crawl_complete(
                books_processed, duration, len(self.errors)
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Crawl operation failed: {str(e)}"
            self.crawl_logger.log_error(error_msg)
            self.errors.append(error_msg)
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            return CrawlResult(
                success=False,
                books_crawled=self.crawl_state.books_processed if self.crawl_state else 0,
                errors=self.errors,
                duration_seconds=duration,
                start_time=start_time,
                end_time=end_time
            )
    
    async def _get_total_pages(self) -> int:
        """Get total number of pages to crawl."""
        try:
            async with httpx.AsyncClient(**self.client_config) as client:
                # First, check if there's a next button (indicating multiple pages)
                response = await client.get(config.base_url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                next_button = soup.find('li', class_='next')
                
                if not next_button:
                    # No next button means only one page
                    return 1
                
                # If there's a next button, use binary search to find the last page
                return await self._find_last_page_binary_search(client)
                
        except Exception as e:
            logger.error("Failed to get total pages", error=str(e))
            return 1
    
    async def _find_last_page_binary_search(self, client: httpx.AsyncClient) -> int:
        """Use binary search to find the last page."""
        low, high = 1, 1000  # Start with a reasonable range
        
        while low <= high:
            mid = (low + high) // 2
            try:
                test_url = f"{config.base_url}/catalogue/page-{mid}.html"
                response = await client.get(test_url)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    books = soup.find_all('article', class_='product_pod')
                    if len(books) > 0:
                        # This page has books, so there might be more pages
                        low = mid + 1
                    else:
                        # No books on this page, so the last page is probably mid - 1
                        high = mid - 1
                else:
                    # Page doesn't exist, so the last page is probably mid - 1
                    high = mid - 1
            except:
                high = mid - 1
        
        return max(1, high)
    
    async def _crawl_page(self, client: httpx.AsyncClient, page_num: int) -> List[BookData]:
        """
        Crawl a single page and extract book data.
        
        Args:
            client: HTTP client instance
            page_num: Page number to crawl
            
        Returns:
            List of BookData instances
        """
        page_url = f"{config.base_url}/catalogue/page-{page_num}.html" if page_num > 1 else config.base_url
        
        async with self.throttler:
            try:
                response = await self._make_request_with_retry(client, page_url)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all book containers
                book_containers = soup.find_all('article', class_='product_pod')
                books = []
                
                # Process books concurrently
                tasks = []
                for container in book_containers:
                    task = self._extract_book_data(client, container, page_url)
                    tasks.append(task)
                
                if tasks:
                    book_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for result in book_results:
                        if isinstance(result, BookData):
                            books.append(result)
                        elif isinstance(result, Exception):
                            self.errors.append(f"Book extraction failed: {str(result)}")
                
                return books
                
            except Exception as e:
                error_msg = f"Failed to crawl page {page_num}: {str(e)}"
                self.errors.append(error_msg)
                self.crawl_logger.log_error(error_msg, url=page_url)
                return []
    
    async def _extract_book_data(self, client: httpx.AsyncClient, container, page_url: str) -> BookData:
        """
        Extract book data from a book container element.
        
        Args:
            client: HTTP client instance
            container: BeautifulSoup element containing book data
            page_url: URL of the page being crawled
            
        Returns:
            BookData instance
        """
        try:
            # Extract basic info from container
            title_elem = container.find('h3').find('a')
            book_url = urljoin(page_url, title_elem['href'])
            
            # Get detailed book page
            book_response = await self._make_request_with_retry(client, book_url)
            book_soup = BeautifulSoup(book_response.text, 'html.parser')
            
            # Extract all required fields
            name = self._extract_text(book_soup, 'h1')
            description = self._extract_text(book_soup, 'div#product_description + p')
            category = self._extract_text(book_soup, 'ul.breadcrumb li:nth-of-type(3) a')
            
            # Extract prices
            price_including_tax = self._extract_price(book_soup, 'p.price_color')
            price_excluding_tax = self._extract_price(book_soup, 'table.table tr:nth-of-type(3) td')
            
            # Extract availability
            availability_text = self._extract_text(book_soup, 'p.availability')
            availability = BookAvailability.IN_STOCK if "in stock" in availability_text.lower() else BookAvailability.OUT_OF_STOCK
            
            # Extract number of reviews
            reviews_text = self._extract_text(book_soup, 'table.table tr:nth-of-type(7) td')
            number_of_reviews = int(re.findall(r'\d+', reviews_text)[0]) if re.findall(r'\d+', reviews_text) else 0
            
            # Extract image URL
            image_elem = book_soup.find('div', class_='item active').find('img')
            image_url = urljoin(book_url, image_elem['src'])
            
            # Extract rating
            rating_elem = book_soup.find('p', class_='star-rating')
            rating = None
            if rating_elem:
                rating_classes = rating_elem.get('class', [])
                for cls in rating_classes:
                    if cls.startswith('One'):
                        rating = BookRating.ONE
                        break
                    elif cls.startswith('Two'):
                        rating = BookRating.TWO
                        break
                    elif cls.startswith('Three'):
                        rating = BookRating.THREE
                        break
                    elif cls.startswith('Four'):
                        rating = BookRating.FOUR
                        break
                    elif cls.startswith('Five'):
                        rating = BookRating.FIVE
                        break
            
            # Create BookData instance
            book_data = BookData(
                name=name,
                description=description,
                category=category,
                price_including_tax=price_including_tax,
                price_excluding_tax=price_excluding_tax,
                availability=availability,
                number_of_reviews=number_of_reviews,
                image_url=image_url,
                rating=rating,
                source_url=book_url,
                raw_html=book_response.text
            )
            
            # Save to database (this will also create the fingerprint)
            success = await self.db_manager.insert_book(book_data)
            self.crawl_logger.log_book_processed(name, book_url, success)
            
            return book_data
            
        except Exception as e:
            error_msg = f"Failed to extract book data: {str(e)}"
            self.crawl_logger.log_error(error_msg, url=book_url if 'book_url' in locals() else page_url)
            raise
    
    async def _make_request_with_retry(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        """
        Make HTTP request with retry logic and exponential backoff.
        
        Args:
            client: HTTP client instance
            url: URL to request
            
        Returns:
            HTTP response
        """
        last_exception = None
        
        for attempt in range(config.retry_attempts + 1):
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response
                
            except Exception as e:
                last_exception = e
                
                if attempt < config.retry_attempts:
                    delay = config.retry_delay * (2 ** attempt)  # Exponential backoff
                    self.crawl_logger.log_retry(str(url), attempt + 1, config.retry_attempts, delay)
                    await asyncio.sleep(delay)
                else:
                    self.crawl_logger.log_error(f"Request failed after {config.retry_attempts} retries", url=str(url))
        
        raise last_exception
    
    def _extract_text(self, soup: BeautifulSoup, selector: str) -> str:
        """Extract text from element using CSS selector."""
        try:
            element = soup.select_one(selector)
            return element.get_text(strip=True) if element else ""
        except Exception:
            return ""
    
    def _extract_price(self, soup: BeautifulSoup, selector: str) -> Decimal:
        """Extract price as Decimal from element."""
        try:
            text = self._extract_text(soup, selector)
            # Remove currency symbols and extract number
            price_text = re.sub(r'[^\d.]', '', text)
            return Decimal(price_text) if price_text else Decimal('0.00')
        except Exception:
            return Decimal('0.00')
    
    async def _load_crawl_state(self) -> None:
        """Load crawl state from file."""
        try:
            with open(self.state_file, 'r') as f:
                state_data = json.load(f)
                self.crawl_state = CrawlState(**state_data)
                logger.info("Loaded crawl state", state=self.crawl_state.dict())
        except Exception as e:
            logger.warning("Failed to load crawl state", error=str(e))
            self.crawl_state = CrawlState()
    
    async def _save_crawl_state(self) -> None:
        """Save crawl state to file."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.crawl_state.dict(), f, indent=2, default=str)
        except Exception as e:
            logger.error("Failed to save crawl state", error=str(e))
    
    async def _fetch_book_details_from_url(self, source_url) -> Optional[BookData]:
        """
        Fetch book details from a specific URL.
        
        Args:
            source_url: URL of the book to fetch (str or HttpUrl)
            
        Returns:
            BookData instance or None if failed
        """
        try:
            # Convert HttpUrl to string if needed
            url_str = str(source_url)
            
            async with httpx.AsyncClient(**self.client_config) as client:
                # Fetch the book page
                response = await self._make_request_with_retry(client, url_str)
                if not response:
                    return None
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract book data using the same logic as _extract_book_data
                name = self._extract_text(soup, 'h1')
                description = self._extract_text(soup, 'div#product_description + p')
                category = self._extract_text(soup, 'ul.breadcrumb li:nth-of-type(3) a')
                
                # Extract prices
                price_including_tax = self._extract_price(soup, 'p.price_color')
                price_excluding_tax = self._extract_price(soup, 'table.table tr:nth-of-type(3) td')
                
                # Extract availability
                availability_text = self._extract_text(soup, 'p.availability')
                availability = self._parse_availability(availability_text)
                
                # Extract rating
                rating_elem = soup.find('p', class_='star-rating')
                rating = self._parse_rating(rating_elem)
                
                # Extract number of reviews
                reviews_text = self._extract_text(soup, 'table.table tr:nth-of-type(7) td')
                number_of_reviews = self._parse_number_of_reviews(reviews_text)
                
                # Extract image URL
                image_elem = soup.find('div', class_='item active').find('img')
                image_url = urljoin(url_str, image_elem['src']) if image_elem else None
                
                # Create BookData instance
                book_data = BookData(
                    name=name,
                    description=description,
                    category=category,
                    price_including_tax=price_including_tax,
                    price_excluding_tax=price_excluding_tax,
                    availability=availability,
                    rating=rating,
                    number_of_reviews=number_of_reviews,
                    image_url=image_url,
                    source_url=url_str,
                    raw_html=response.text,
                    html_snapshot_timestamp=datetime.utcnow(),
                    html_size_bytes=len(response.text),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                return book_data
                
        except Exception as e:
            logger.error(
                "Failed to fetch book details from URL",
                source_url=str(source_url),
                error=str(e)
            )
            return None
    
    def _parse_availability(self, availability_text: str) -> BookAvailability:
        """Parse availability text to BookAvailability enum."""
        if not availability_text:
            return BookAvailability.OUT_OF_STOCK
        
        availability_lower = availability_text.lower()
        if "in stock" in availability_lower:
            return BookAvailability.IN_STOCK
        else:
            return BookAvailability.OUT_OF_STOCK
    
    def _parse_rating(self, rating_elem) -> Optional[BookRating]:
        """Parse rating element to BookRating enum."""
        if not rating_elem:
            return None
        
        rating_classes = rating_elem.get('class', [])
        for cls in rating_classes:
            if cls.startswith('One'):
                return BookRating.ONE
            elif cls.startswith('Two'):
                return BookRating.TWO
            elif cls.startswith('Three'):
                return BookRating.THREE
            elif cls.startswith('Four'):
                return BookRating.FOUR
            elif cls.startswith('Five'):
                return BookRating.FIVE
        
        return None
    
    def _parse_number_of_reviews(self, reviews_text: str) -> int:
        """Parse number of reviews from text."""
        if not reviews_text:
            return 0
        
        numbers = re.findall(r'\d+', reviews_text)
        return int(numbers[0]) if numbers else 0
