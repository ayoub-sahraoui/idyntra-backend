from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import logging

from app.config import get_settings
from app.utils.logging import setup_logging
from app.api.v1.endpoints import verification, health, extraction


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    settings = get_settings()
    logger = setup_logging(
        log_file=settings.LOG_FILE,
        log_level=settings.LOG_LEVEL,
        max_bytes=settings.LOG_MAX_BYTES,
        backup_count=settings.LOG_BACKUP_COUNT
    )

    logger.info("=" * 70)
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"Device mode: {'GPU' if not settings.CPU_ONLY else 'CPU'}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info("=" * 70)

    # Initialize components (triggers @lru_cache)
    from app.dependencies import (
        get_liveness_detector,
        get_face_matcher,
        get_mrz_extractor
    )

    get_liveness_detector()
    get_face_matcher()
    get_mrz_extractor()

    logger.info("✓ All components initialized")

    yield

    logger.info("Shutting down gracefully")


def create_app() -> FastAPI:
    """Application factory pattern"""

    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        description="Production-grade identity verification API",
        lifespan=lifespan,
        debug=settings.DEBUG
    )

    # CORS
    # Coerce ALLOWED_ORIGINS into a list (supports both List[str] and
    # comma-separated string from environment variables).
    allowed_origins = settings.ALLOWED_ORIGINS
    if isinstance(allowed_origins, str):
        allowed_origins = [o.strip() for o in allowed_origins.split(",") if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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

    # Include routers
    app.include_router(verification.router)
    app.include_router(extraction.router)
    app.include_router(health.router)

    return app


app = create_app()