"""
Configuration management using environment variables.
Handles all crawler settings with proper validation and defaults.
"""

import os
from typing import Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from pathlib import Path


class CrawlerConfig(BaseSettings):
    """
    Configuration class for crawler settings.
    Uses pydantic BaseSettings for environment variable management.
    """
    
    # MongoDB Configuration
    mongodb_url: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    mongodb_database: str = Field(default="filers_keepers", env="MONGODB_DATABASE")
    mongodb_collection: str = Field(default="books", env="MONGODB_COLLECTION")
    
    # Crawler Configuration
    base_url: str = Field(default="https://books.toscrape.com", env="BASE_URL")
    max_concurrent_requests: int = Field(default=10, env="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")
    retry_attempts: int = Field(default=3, env="RETRY_ATTEMPTS")
    retry_delay: float = Field(default=1.0, env="RETRY_DELAY")
    rate_limit_per_second: float = Field(default=2.0, env="RATE_LIMIT_PER_SECOND")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file: Optional[str] = Field(default="logs/crawler.log", env="LOG_FILE")
    
    # Crawl State Management
    state_file: str = Field(default="crawl_state.json", env="STATE_FILE")
    resume_on_failure: bool = Field(default=True, env="RESUME_ON_FAILURE")
    
    # Development/Testing
    debug: bool = Field(default=False, env="DEBUG")
    test_mode: bool = Field(default=False, env="TEST_MODE")
    
    # Scheduler Configuration
    schedule_hour: int = Field(default=2, env="SCHEDULE_HOUR")
    schedule_minute: int = Field(default=0, env="SCHEDULE_MINUTE")
    timezone: str = Field(default="UTC", env="TIMEZONE")
    enable_change_detection: bool = Field(default=True, env="ENABLE_CHANGE_DETECTION")
    generate_daily_reports: bool = Field(default=True, env="GENERATE_DAILY_REPORTS")
    batch_size: int = Field(default=100, env="BATCH_SIZE")
    
    @validator('max_concurrent_requests')
    def validate_concurrent_requests(cls, v):
        """Ensure concurrent requests is reasonable."""
        if v < 1 or v > 50:
            raise ValueError('max_concurrent_requests must be between 1 and 50')
        return v
    
    @validator('request_timeout')
    def validate_timeout(cls, v):
        """Ensure timeout is reasonable."""
        if v < 5 or v > 300:
            raise ValueError('request_timeout must be between 5 and 300 seconds')
        return v
    
    @validator('retry_attempts')
    def validate_retry_attempts(cls, v):
        """Ensure retry attempts is reasonable."""
        if v < 0 or v > 10:
            raise ValueError('retry_attempts must be between 0 and 10')
        return v
    
    @validator('rate_limit_per_second')
    def validate_rate_limit(cls, v):
        """Ensure rate limit is reasonable."""
        if v < 0.1 or v > 10:
            raise ValueError('rate_limit_per_second must be between 0.1 and 10')
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Ensure log level is valid."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'log_level must be one of: {valid_levels}')
        return v.upper()
    
    @validator('log_format')
    def validate_log_format(cls, v):
        """Ensure log format is valid."""
        valid_formats = ['json', 'console']
        if v.lower() not in valid_formats:
            raise ValueError(f'log_format must be one of: {valid_formats}')
        return v.lower()
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env
    
    def get_log_file_path(self) -> Optional[Path]:
        """Get log file path as Path object."""
        if self.log_file:
            return Path(self.log_file)
        return None
    
    def get_state_file_path(self) -> Path:
        """Get state file path as Path object."""
        return Path(self.state_file)
    
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.debug and not self.test_mode
    
    def get_user_agent(self) -> str:
        """Get user agent string for requests."""
        return "FilersKeepers-Crawler/1.0 (Educational Assessment)"
    
    def get_headers(self) -> dict:
        """Get default headers for HTTP requests."""
        return {
            "User-Agent": self.get_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }


# Global configuration instance
config = CrawlerConfig()
