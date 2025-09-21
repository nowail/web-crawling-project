"""
Authentication and rate limiting for the FastAPI API.
"""

import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

import structlog
from fastapi import HTTPException, Request, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from utilities.config import config

logger = structlog.get_logger(__name__)

# In-memory storage for API keys and rate limiting
# In production, this should be stored in Redis or a database
api_keys: Dict[str, Dict] = {}
rate_limits: Dict[str, Dict] = {}

# Security scheme
security = HTTPBearer()


class APIKeyManager:
    """Manages API keys and authentication."""

    @staticmethod
    def generate_api_key() -> str:
        """Generate a new API key."""
        return f"fk_{secrets.token_urlsafe(32)}"

    @staticmethod
    def create_api_key(
        name: str, 
        description: str = "", 
        expires_hours: Optional[int] = None
    ) -> Dict:
        """
        Create a new API key.
        
        Args:
            name: Name for the API key
            description: Description of the API key
            expires_hours: Hours until expiration (None for no expiration)
            
        Returns:
            Dictionary with API key details
        """
        api_key = APIKeyManager.generate_api_key()
        expires_at = None
        
        if expires_hours:
            expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
        
        api_keys[api_key] = {
            "name": name,
            "description": description,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "is_active": True,
            "rate_limit": 100  # requests per hour
        }
        
        logger.info("API key created", name=name, expires_at=expires_at, api_key=api_key)
        
        return {
            "api_key": api_key,
            "name": name,
            "description": description,
            "expires_at": expires_at,
            "rate_limit": 100
        }

    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """
        Validate an API key.
        
        Args:
            api_key: API key to validate
            
        Returns:
            True if valid, False otherwise
        """
        if api_key not in api_keys:
            return False
        
        key_info = api_keys[api_key]
        
        # Check if key is active
        if not key_info.get("is_active", False):
            return False
        
        # Check if key has expired
        expires_at = key_info.get("expires_at")
        if expires_at and datetime.utcnow() > expires_at:
            return False
        
        return True

    @staticmethod
    def get_api_key_info(api_key: str) -> Optional[Dict]:
        """
        Get API key information.
        
        Args:
            api_key: API key
            
        Returns:
            API key information if found, None otherwise
        """
        return api_keys.get(api_key)

    @staticmethod
    def revoke_api_key(api_key: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            api_key: API key to revoke
            
        Returns:
            True if revoked, False if not found
        """
        if api_key in api_keys:
            api_keys[api_key]["is_active"] = False
            logger.info("API key revoked", api_key=api_key[:10] + "...")
            return True
        return False

    @staticmethod
    def list_api_keys() -> Dict[str, Dict]:
        """
        List all API keys (without the actual key values).
        
        Returns:
            Dictionary of API key information
        """
        result = {}
        for api_key, info in api_keys.items():
            result[api_key[:10] + "..."] = {
                "name": info["name"],
                "description": info["description"],
                "created_at": info["created_at"],
                "expires_at": info["expires_at"],
                "is_active": info["is_active"],
                "rate_limit": info["rate_limit"]
            }
        return result


class RateLimiter:
    """Handles rate limiting for API requests."""

    @staticmethod
    def check_rate_limit(api_key: str) -> bool:
        """
        Check if API key has exceeded rate limit.
        
        Args:
            api_key: API key to check
            
        Returns:
            True if within limit, False if exceeded
        """
        current_time = time.time()
        hour_window = 3600  # 1 hour in seconds
        
        # Get rate limit for this API key
        key_info = APIKeyManager.get_api_key_info(api_key)
        if not key_info:
            return False
        
        rate_limit = key_info.get("rate_limit", 100)
        
        # Initialize rate limit tracking for this key
        if api_key not in rate_limits:
            rate_limits[api_key] = {
                "requests": [],
                "rate_limit": rate_limit
            }
        
        # Clean old requests (older than 1 hour)
        rate_limits[api_key]["requests"] = [
            req_time for req_time in rate_limits[api_key]["requests"]
            if current_time - req_time < hour_window
        ]
        
        # Check if under limit
        if len(rate_limits[api_key]["requests"]) < rate_limit:
            # Add current request
            rate_limits[api_key]["requests"].append(current_time)
            return True
        
        return False

    @staticmethod
    def get_rate_limit_info(api_key: str) -> Dict:
        """
        Get rate limit information for an API key.
        
        Args:
            api_key: API key
            
        Returns:
            Dictionary with rate limit information
        """
        current_time = time.time()
        hour_window = 3600
        
        if api_key not in rate_limits:
            return {
                "requests_used": 0,
                "requests_remaining": 100,
                "rate_limit": 100,
                "reset_time": current_time + hour_window
            }
        
        # Clean old requests
        rate_limits[api_key]["requests"] = [
            req_time for req_time in rate_limits[api_key]["requests"]
            if current_time - req_time < hour_window
        ]
        
        requests_used = len(rate_limits[api_key]["requests"])
        rate_limit = rate_limits[api_key]["rate_limit"]
        requests_remaining = max(0, rate_limit - requests_used)
        
        # Calculate reset time (next hour boundary)
        reset_time = current_time + hour_window
        
        return {
            "requests_used": requests_used,
            "requests_remaining": requests_remaining,
            "rate_limit": rate_limit,
            "reset_time": reset_time
        }


async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Verify API key from request using environment variables.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        API key if valid
        
    Raises:
        HTTPException: If API key is invalid or rate limit exceeded
    """
    api_key = credentials.credentials
    
    # Get valid API keys from environment
    from api.config import config
    
    # Parse comma-separated API keys from environment
    valid_api_keys = []
    if config.api_keys:
        valid_api_keys = [key.strip() for key in config.api_keys.split(",") if key.strip()]
    
    
    # Check if API key is valid
    if api_key not in valid_api_keys:
        logger.warning("Invalid API key attempted", api_key=api_key[:10] + "...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # TODO: Implement proper rate limiting with Redis or database storage
    
    return api_key


def get_rate_limit_headers(api_key: str) -> Dict[str, str]:
    """
    Get rate limit headers for response.
    
    Args:
        api_key: API key
        
    Returns:
        Dictionary with rate limit headers
    """
    rate_info = RateLimiter.get_rate_limit_info(api_key)
    return {
        "X-RateLimit-Limit": str(rate_info['rate_limit']),
        "X-RateLimit-Remaining": str(rate_info['requests_remaining']),
        "X-RateLimit-Reset": str(int(rate_info['reset_time']))
    }


async def initialize_default_api_key(db_service):
    """Initialize a default API key if none exists."""
    try:
        # Check if any API keys exist
        existing_keys = await db_service.get_api_keys()
        
        if not existing_keys:
            # Create default API key
            default_key = APIKeyManager.create_api_key(
                name="Default API Key",
                description="Default API key for testing and development"
            )
            
            # Store in database
            await db_service.create_api_key(default_key)
            logger.info("Default API key created", api_key=default_key["api_key"])
        else:
            logger.info("API keys already exist, skipping default key creation")
            
    except Exception as e:
        logger.error("Failed to initialize default API key", error=str(e))
        raise
