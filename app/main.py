from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import time
import logging
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.api.v1.auth import check_rate_limit
from app.utils.logging import (
    setup_logging,
    log_request_start,
    log_request_end,
    get_request_id
)
from app.utils.error_handling import (
    http_exception_handler,
    validation_exception_handler,
    python_exception_handler
)
from app.api.v1.endpoints import verification, health, extraction

# Security headers will be added manually in middleware
# The 'secure' package 0.3.0 has a different API, so we'll add headers directly


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    import os
    settings = get_settings()
    logger = setup_logging(
        log_level=settings.LOG_LEVEL,
        max_bytes=settings.LOG_MAX_BYTES,
        backup_count=settings.LOG_BACKUP_COUNT
    )

    # Log worker process ID for debugging
    worker_id = os.getpid()
    logger.info("=" * 70)
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.VERSION} [PID: {worker_id}]")
    logger.info(f"Device mode: {'GPU' if not settings.CPU_ONLY else 'CPU'}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info("=" * 70)

    # Initialize components (triggers @lru_cache)
    try:
        from app.dependencies import (
            get_liveness_detector,
            get_face_matcher,
            get_mrz_extractor,
            get_document_authenticator,
            get_deepfake_detector
        )

        logger.info("Loading ML models...")
        
        try:
            get_liveness_detector()
            logger.info("✓ Liveness detector loaded")
        except Exception as e:
            logger.exception(f"✗ FAILED to load liveness detector: {str(e)}")
            raise
        
        try:
            get_face_matcher()
            logger.info("✓ Face matcher loaded")
        except Exception as e:
            logger.exception(f"✗ FAILED to load face matcher: {str(e)}")
            raise
        
        try:
            get_mrz_extractor()
            logger.info("✓ MRZ extractor loaded")
        except Exception as e:
            logger.exception(f"✗ FAILED to load MRZ extractor: {str(e)}")
            raise
        
        try:
            get_document_authenticator()
            logger.info("✓ Document authenticator loaded")
        except Exception as e:
            logger.exception(f"✗ FAILED to load document authenticator: {str(e)}")
            raise
        
        try:
            get_deepfake_detector()
            logger.info("✓ Deepfake detector loaded")
        except Exception as e:
            logger.exception(f"✗ FAILED to load deepfake detector: {str(e)}")
            raise

        logger.info("=" * 70)
        logger.info("✓ ALL COMPONENTS INITIALIZED SUCCESSFULLY")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.exception(f"CRITICAL: Model initialization failed: {str(e)}")
        logger.error("Application will continue but endpoints may fail!")
        # Don't raise - allow app to start even if models fail

    # Register exception handlers
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, python_exception_handler)

    yield

    logger.info("Shutting down gracefully")


def create_app() -> FastAPI:
    """Application factory pattern"""

    settings = get_settings()
    
    # Convert string settings to lists for CORS/Host middleware
    allowed_origins = [settings.ALLOWED_ORIGINS] if settings.ALLOWED_ORIGINS == "*" else [
        origin.strip() for origin in settings.ALLOWED_ORIGINS.split(',')
    ]
    allowed_hosts = [settings.ALLOWED_HOSTS] if settings.ALLOWED_HOSTS == "*" else [
        host.strip() for host in settings.ALLOWED_HOSTS.split(',')
    ]

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        description="Production-grade identity verification API",
        lifespan=lifespan,
        debug=settings.DEBUG
    )

    # Configure request tracking middleware
    @app.middleware("http")
    async def request_middleware(request: Request, call_next):
        # Get logger instance
        logger = logging.getLogger("idv_api")
        
        # Generate request ID
        request_id = get_request_id()
        
        # Start timing
        start_time = time.time()
        
        # Log request start
        log_request_start(
            logger=logger,
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            client_host=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log request completion
            log_request_end(
                logger=logger,
                request_id=request_id,
                duration_ms=duration_ms,
                status_code=response.status_code
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as e:
            # Log error and re-raise
            logger.exception(
                "Request failed",
                extra={
                    "structured_data": {
                        "event_type": "request_error",
                        "request_id": request_id,
                        "error": str(e)
                    }
                }
            )
            raise
    
    # Configure security headers middleware
    @app.middleware("http")
    async def add_secure_headers(request: Request, call_next):
        response = await call_next(request)
        # Add security headers manually
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

    # Configure CORS with stricter settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-API-Key",
            "Accept",
            "Origin",
            "X-Requested-With"
        ],
        expose_headers=["X-Request-ID", "Retry-After"],
        max_age=3600,
    )

    # Add trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts
    )

    # Request timing middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger = logging.getLogger("idv_api")
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "type": type(exc).__name__}
        )

    # Include routers with auth and rate limiting
    app.include_router(
        verification.router,
        dependencies=[Depends(check_rate_limit)]
    )
    app.include_router(
        extraction.router,
        dependencies=[Depends(check_rate_limit)]
    )
    
    # Health check endpoint doesn't need auth
    app.include_router(health.router)

    return app


app = create_app()