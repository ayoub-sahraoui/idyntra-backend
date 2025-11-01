from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
from typing import Optional
import time
from datetime import datetime, timedelta
import hashlib
import hmac
import os
from pydantic import BaseModel
from app.config import get_settings


# API Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Rate limiting storage
# In production, this should be replaced with Redis
rate_limits = {}


class RateLimitExceeded(HTTPException):
    def __init__(self, retry_after: int):
        super().__init__(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "retry_after": retry_after
            }
        )
        self.headers = {"Retry-After": str(retry_after)}


def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """Verify API key and return client ID"""
    if not api_key:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="API key is required"
        )

    settings = get_settings()
    
    # Parse valid API keys from comma-separated string
    valid_keys = [k.strip() for k in settings.VALID_API_KEYS.split(",") if k.strip()]
    
    # If no keys configured, skip validation (dev mode only)
    if not valid_keys:
        return "anonymous"
    
    # In production, this should be replaced with a database lookup
    if not any(hmac.compare_digest(api_key, valid_key) for valid_key in valid_keys):
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )

    # Use a hash of the API key as the client ID
    return hashlib.sha256(api_key.encode()).hexdigest()


def check_rate_limit(
    client_id: str = Depends(verify_api_key),
    settings = Depends(get_settings)
) -> None:
    """Check rate limit for the client"""
    now = datetime.now()
    window_size = 60  # 1 minute window
    max_requests = settings.MAX_REQUESTS_PER_MINUTE

    # Get client's request history
    if client_id not in rate_limits:
        rate_limits[client_id] = []

    # Clean up old requests
    rate_limits[client_id] = [
        ts for ts in rate_limits[client_id]
        if ts > now - timedelta(seconds=window_size)
    ]

    # Check if limit exceeded
    if len(rate_limits[client_id]) >= max_requests:
        # Calculate retry after
        oldest_request = min(rate_limits[client_id])
        retry_after = int((oldest_request + timedelta(seconds=window_size) - now).total_seconds())
        raise RateLimitExceeded(retry_after=retry_after)

    # Add current request
    rate_limits[client_id].append(now)