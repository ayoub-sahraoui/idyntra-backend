from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Dict, Any, Optional
import logging
import uuid
import traceback
from datetime import datetime
from app.config import get_settings

logger = logging.getLogger("idv_api")

class APIError(HTTPException):
    """Base API error class"""
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str,
        error_type: str = "api_error"
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.error_type = error_type

class ValidationError(APIError):
    """Validation error"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=400,
            detail=detail,
            error_code="VALIDATION_ERROR",
            error_type="validation_error"
        )

class AuthenticationError(APIError):
    """Authentication error"""
    def __init__(self, detail: str = "Invalid API key"):
        super().__init__(
            status_code=401,
            detail=detail,
            error_code="AUTHENTICATION_ERROR",
            error_type="auth_error"
        )

class RateLimitError(APIError):
    """Rate limit exceeded error"""
    def __init__(self, retry_after: int):
        super().__init__(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds",
            error_code="RATE_LIMIT_ERROR",
            error_type="rate_limit_error"
        )
        self.headers = {"Retry-After": str(retry_after)}

def create_error_response(
    request: Request,
    exc: Exception,
    status_code: int,
    error_code: str,
    error_type: str,
    detail: str,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create standardized error response"""
    error_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    # Log error with context
    log_context = {
        "error_id": error_id,
        "error_type": error_type,
        "error_code": error_code,
        "status_code": status_code,
        "path": str(request.url),
        "method": request.method,
        "client_ip": request.client.host if request.client else None,
        "timestamp": timestamp
    }
    
    if get_settings().DEBUG:
        log_context["traceback"] = traceback.format_exc()
    
    logger.error(
        f"API Error: {detail}",
        extra=log_context
    )
    
    response = {
        "error": {
            "id": error_id,
            "type": error_type,
            "code": error_code,
            "message": detail,
            "timestamp": timestamp,
            "path": str(request.url)
        },
        "success": False
    }
    
    if meta:
        response["error"]["meta"] = meta
    
    if get_settings().DEBUG:
        response["error"]["debug_info"] = {
            "exception_type": exc.__class__.__name__,
            "traceback": traceback.format_exc()
        }
    
    return response

async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException
) -> JSONResponse:
    """Handle HTTP exceptions"""
    if isinstance(exc, APIError):
        response = create_error_response(
            request=request,
            exc=exc,
            status_code=exc.status_code,
            error_code=exc.error_code,
            error_type=exc.error_type,
            detail=str(exc.detail)
        )
    else:
        response = create_error_response(
            request=request,
            exc=exc,
            status_code=exc.status_code,
            error_code="HTTP_ERROR",
            error_type="http_error",
            detail=str(exc.detail)
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response,
        headers=getattr(exc, "headers", None)
    )

async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors"""
    errors = []
    for error in exc.errors():
        error_location = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": error_location,
            "type": error["type"],
            "message": error["msg"]
        })
    
    response = create_error_response(
        request=request,
        exc=exc,
        status_code=422,
        error_code="VALIDATION_ERROR",
        error_type="validation_error",
        detail="Request validation failed",
        meta={"validation_errors": errors}
    )
    
    return JSONResponse(
        status_code=422,
        content=response
    )

async def python_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Handle unhandled Python exceptions"""
    response = create_error_response(
        request=request,
        exc=exc,
        status_code=500,
        error_code="INTERNAL_ERROR",
        error_type="server_error",
        detail="An unexpected error occurred"
    )
    
    return JSONResponse(
        status_code=500,
        content=response
    )