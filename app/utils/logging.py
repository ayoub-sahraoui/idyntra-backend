import logging
from logging.handlers import RotatingFileHandler
import json
import os
import sys
import uuid
import time
from typing import Dict, Any, Optional
from datetime import datetime
from app.config import get_settings

class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def __init__(self, **kwargs):
        super().__init__()
        self.extras = kwargs

    def format(self, record) -> str:
        """Format log record as JSON"""
        # Base log data
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add process and thread info
        log_data.update({
            "process": {
                "id": record.process,
                "name": record.processName
            },
            "thread": {
                "id": record.thread,
                "name": record.threadName
            }
        })
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra fields from record
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        # Add any structured data passed via extra
        if hasattr(record, "structured_data"):
            log_data.update(record.structured_data)
        
        # Add static extras from formatter initialization
        log_data.update(self.extras)
        
        return json.dumps(log_data)

class RequestContextFilter(logging.Filter):
    """Add request context to log records"""
    
    def __init__(self):
        super().__init__()
        self._context = {}

    def update_context(self, **kwargs):
        """Update context with new values"""
        self._context.update(kwargs)

    def filter(self, record):
        """Add context to log record"""
        for key, value in self._context.items():
            setattr(record, key, value)
        return True

def setup_logging(
    log_file: Optional[str] = None,
    log_level: str = "INFO",
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3
) -> logging.Logger:
    """Setup structured logging with rotation"""
    settings = get_settings()
    
    # Use settings if no explicit values provided
    log_file = log_file or settings.LOG_FILE
    log_level = log_level or settings.LOG_LEVEL
    max_bytes = max_bytes or settings.LOG_MAX_BYTES
    backup_count = backup_count or settings.LOG_BACKUP_COUNT
    
    # Create logs directory if it doesn't exist
    if log_file:
        log_dir = os.path.dirname(log_file)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
    
    # Configure root logger
    logger = logging.getLogger("idv_api")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers = []
    
    # Create structured formatter
    formatter = StructuredFormatter(
        app_name=settings.APP_NAME,
        app_version=settings.VERSION,
        environment="production" if not settings.DEBUG else "development"
    )
    
    # Create request context filter
    context_filter = RequestContextFilter()
    
    # File handler with rotation (if log file specified)
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(context_filter)
        logger.addHandler(file_handler)
    
    # Console handler (always add for local development)
    if settings.DEBUG or not log_file:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(context_filter)
        logger.addHandler(console_handler)
    
    return logger

def log_request_start(logger: logging.Logger, request_id: str, **kwargs):
    """Log request start with context"""
    logger.info(
        "Request started",
        extra={
            "structured_data": {
                "event_type": "request_start",
                "request_id": request_id,
                **kwargs
            }
        }
    )

def log_request_end(
    logger: logging.Logger,
    request_id: str,
    duration_ms: float,
    status_code: int,
    **kwargs
):
    """Log request end with metrics"""
    logger.info(
        f"Request completed in {duration_ms:.2f}ms",
        extra={
            "structured_data": {
                "event_type": "request_end",
                "request_id": request_id,
                "duration_ms": duration_ms,
                "status_code": status_code,
                **kwargs
            }
        }
    )

def get_request_id() -> str:
    """Generate unique request ID"""
    return str(uuid.uuid4())