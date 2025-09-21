"""
Main entry point for the FilersKeepers Assessment crawler.
Provides CLI interface for running the crawler with different options.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from crawler.database import MongoDBManager
from crawler.book_crawler import BookCrawler
from utilities.config import config
from utilities.logger import setup_logging, get_logger


async def main():
    """Main function to run the crawler."""
    # Set up logging
    setup_logging(
        log_level=config.log_level,
        log_format=config.log_format,
        log_file=config.get_log_file_path(),
        debug=config.debug
    )
    
    logger = get_logger(__name__)
    logger.info("Starting FilersKeepers Assessment Crawler")
    
    try:
        # Initialize database manager
        db_manager = MongoDBManager(
            connection_url=config.mongodb_url,
            database_name=config.mongodb_database,
            collection_name=config.mongodb_collection
        )
        
        # Connect to database
        await db_manager.connect()
        logger.info("Connected to MongoDB successfully")
        
        # Initialize crawler
        crawler = BookCrawler(db_manager)
        
        # Run crawler
        logger.info("Starting crawl operation")
        result = await crawler.crawl_all_books(resume=config.resume_on_failure)
        
        # Log results
        if result.success:
            logger.info(
                "Crawl completed successfully",
                books_crawled=result.books_crawled,
                duration_seconds=result.duration_seconds
            )
        else:
            logger.error(
                "Crawl completed with errors",
                books_crawled=result.books_crawled,
                errors=len(result.errors),
                duration_seconds=result.duration_seconds
            )
            for error in result.errors:
                logger.error("Crawl error", error=error)
        
        # Get database statistics
        stats = await db_manager.get_database_stats()
        logger.info("Database statistics", **stats)
        
    except Exception as e:
        logger.error("Fatal error occurred", error=str(e))
        sys.exit(1)
    
    finally:
        # Clean up
        if 'db_manager' in locals():
            await db_manager.disconnect()
            logger.info("Disconnected from MongoDB")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
