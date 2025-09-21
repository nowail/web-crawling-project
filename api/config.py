"""
API configuration settings.
"""

import os
from typing import Optional

from pydantic_settings import BaseSettings


class APIConfig(BaseSettings):
    """API configuration settings."""
    
    # API Settings
    api_title: str = "FilersKeepers Book Management API"
    api_version: str = "1.0.0"
    api_description: str = "A comprehensive REST API for managing and monitoring book data"
    
    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Database Settings
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "filers_keepers"
    
    # Security Settings
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # API Key Settings
    api_keys: str = ""  # Comma-separated list of valid API keys
    
    # Rate Limiting
    default_rate_limit: int = 100  # requests per hour
    rate_limit_window: int = 3600  # 1 hour in seconds
    
    # CORS Settings
    cors_origins: list = ["*"]  # Configure appropriately for production
    cors_allow_credentials: bool = True
    cors_allow_methods: list = ["*"]
    cors_allow_headers: list = ["*"]
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    model_config = {
        "env_file": ".env",
        "extra": "ignore"  # Ignore extra fields from .env
    }


# Global config instance
config = APIConfig()
