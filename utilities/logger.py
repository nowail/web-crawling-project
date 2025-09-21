"""
Comprehensive logging system using structlog.
Provides structured logging with different output formats and levels.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import structlog
from structlog.stdlib import LoggerFactory


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[str] = None,
    debug: bool = False
) -> None:
    """
    Set up structured logging with configurable output formats.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format (json, console, or both)
        log_file: Optional log file path
        debug: Enable debug mode for more verbose logging
    """
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Add format-specific processors
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    elif log_format == "console":
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        # Default to console for development
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )
    
    # Set up file logging if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        
        # Use JSON format for file logs
        file_formatter = logging.Formatter('%(message)s')
        file_handler.setFormatter(file_formatter)
        
        # Add handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
    
    # Enable debug mode if requested
    if debug:
        structlog.configure(
            processors=processors + [structlog.processors.CallsiteParameterAdder()],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=LoggerFactory(),
            context_class=dict,
            cache_logger_on_first_use=True,
        )
    
    # Log configuration
    logger = structlog.get_logger(__name__)
    try:
        logger.info(
            "Logging system initialized",
            level=log_level,
            format=log_format,
            file=str(log_file) if log_file else None,
            debug=debug
        )
    except Exception:
        # Fallback to simple logging if structlog fails
        print(f"Logging system initialized - Level: {log_level}, Format: {log_format}")


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


class CrawlLogger:
    """
    Specialized logger for crawl operations with context management.
    """
    
    def __init__(self, name: str = "crawler"):
        self.logger = structlog.get_logger(name)
        self.context = {}
    
    def bind_context(self, **kwargs) -> 'CrawlLogger':
        """
        Bind context variables to the logger.
        
        Args:
            **kwargs: Context variables to bind
            
        Returns:
            Self for method chaining
        """
        self.context.update(kwargs)
        return self
    
    def clear_context(self) -> 'CrawlLogger':
        """Clear all context variables."""
        self.context.clear()
        return self
    
    def log_crawl_start(self, base_url: str, max_pages: Optional[int] = None) -> None:
        """Log crawl operation start."""
        self.logger.info(
            "Crawl operation started",
            base_url=base_url,
            max_pages=max_pages,
            **self.context
        )
    
    def log_crawl_progress(self, current_page: int, total_pages: int, books_processed: int) -> None:
        """Log crawl progress."""
        progress_percent = (current_page / total_pages) * 100 if total_pages > 0 else 0
        self.logger.info(
            "Crawl progress update",
            current_page=current_page,
            total_pages=total_pages,
            books_processed=books_processed,
            progress_percent=round(progress_percent, 2),
            **self.context
        )
    
    def log_crawl_complete(self, total_books: int, duration_seconds: float, errors: int = 0) -> None:
        """Log crawl operation completion."""
        self.logger.info(
            "Crawl operation completed",
            total_books=total_books,
            duration_seconds=duration_seconds,
            errors=errors,
            **self.context
        )
    
    def log_book_processed(self, book_name: str, url: str, success: bool = True) -> None:
        """Log individual book processing."""
        level = "debug" if success else "warning"
        getattr(self.logger, level)(
            "Book processed",
            book_name=book_name,
            url=url,
            success=success,
            **self.context
        )
    
    def log_error(self, error: str, url: Optional[str] = None, retry_count: Optional[int] = None) -> None:
        """Log error with context."""
        self.logger.error(
            "Crawl error occurred",
            error=error,
            url=url,
            retry_count=retry_count,
            **self.context
        )
    
    def log_retry(self, url: str, attempt: int, max_attempts: int, delay: float) -> None:
        """Log retry attempt."""
        self.logger.warning(
            "Retrying request",
            url=url,
            attempt=attempt,
            max_attempts=max_attempts,
            delay_seconds=delay,
            **self.context
        )
    
    def log_database_operation(self, operation: str, success: bool, count: Optional[int] = None) -> None:
        """Log database operation."""
        level = "debug" if success else "error"
        getattr(self.logger, level)(
            "Database operation",
            operation=operation,
            success=success,
            count=count,
            **self.context
        )
