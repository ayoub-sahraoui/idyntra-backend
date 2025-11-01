from fastapi import APIRouter, Depends
from app.api.v1.schemas import HealthResponse
from app.dependencies import (
    get_liveness_detector,
    get_face_matcher,
    get_deepfake_detector,
    get_mrz_extractor,
    get_logger
)
from app.config import get_settings
from datetime import datetime
import torch

router = APIRouter(tags=["health"])


@router.get("/", response_model=dict)
async def root(logger = Depends(get_logger)):
    """Root endpoint - API information"""
    try:
        logger.info("Root endpoint accessed")
        return {
            "service": "Enhanced ID Verification API",
            "version": get_settings().VERSION,
            "status": "online",
            "docs": "/docs",
            "health": "/health"
        }
    except Exception as e:
        logger.exception(f"Root endpoint failed: {str(e)}")
        return {
            "service": "Enhanced ID Verification API",
            "status": "error",
            "error": str(e)
        }


@router.get("/health", response_model=HealthResponse)
async def health_check(logger = Depends(get_logger)):
    """
    **Basic health check**

    Returns API status without loading ML models.
    For detailed component status, use /health/detailed
    """

    try:
        logger.info("Health check request received")
        settings = get_settings()

        # Basic health check without loading models
        response = HealthResponse(
            status="healthy",
            version=settings.VERSION,
            device="cpu" if settings.CPU_ONLY else "gpu",
            gpu_available=torch.cuda.is_available() and not settings.CPU_ONLY,
            timestamp=datetime.utcnow(),
            components={
                "api": True,
                "config": True
            }
        )
        logger.info("Health check response prepared successfully")
        return response
    except Exception as e:
        logger.exception(f"Health check failed: {str(e)}")
        # Still try to return something
        return HealthResponse(
            status="unhealthy",
            version="unknown",
            device="unknown",
            gpu_available=False,
            timestamp=datetime.utcnow(),
            components={
                "api": False,
                "config": False,
                "error": str(e)
            }
        )


@router.get("/health/detailed", response_model=HealthResponse)
async def detailed_health_check(
    liveness = Depends(get_liveness_detector),
    face_matcher = Depends(get_face_matcher),
    deepfake = Depends(get_deepfake_detector),
    mrz = Depends(get_mrz_extractor),
    logger = Depends(get_logger)
):
    """
    **Detailed health check with component verification**

    Loads and verifies all ML models are functional.
    Note: Models should already be loaded at startup.
    """

    try:
        logger.info("=== DETAILED HEALTH CHECK START ===")
        settings = get_settings()

        components = {
            "liveness_detector": liveness is not None,
            "face_matcher": face_matcher is not None,
            "deepfake_detector": deepfake is not None,
            "mrz_extractor": mrz is not None,
            "readmrz": mrz.engines.get('readmrz', False) if mrz else False,
            "passport_mrz_extractor": mrz.engines.get('passport_mrz_extractor', False) if mrz else False
        }

        logger.info(f"Component status: {components}")

        all_healthy = all(components.values())

        response = HealthResponse(
            status="healthy" if all_healthy else "degraded",
            version=settings.VERSION,
            device="gpu" if torch.cuda.is_available() and not settings.CPU_ONLY else "cpu",
            gpu_available=torch.cuda.is_available() and not settings.CPU_ONLY,
            timestamp=datetime.utcnow(),
            components=components
        )

        logger.info(f"=== DETAILED HEALTH CHECK COMPLETE: {response.status} ===")
        return response
    
    except Exception as e:
        logger.exception(f"Detailed health check failed: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            version=get_settings().VERSION if get_settings() else "unknown",
            device="unknown",
            gpu_available=False,
            timestamp=datetime.utcnow(),
            components={
                "error": str(e)
            }
        )


@router.get("/ready")
async def readiness_check(logger = Depends(get_logger)):
    """
    **Kubernetes/Docker readiness probe**
    
    Indicates the application is ready to receive traffic.
    Used by load balancers and orchestration systems.
    """
    try:
        logger.debug("Readiness probe check")
        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return {"status": "not_ready", "error": str(e)}


@router.get("/live")
async def liveness_check(logger = Depends(get_logger)):
    """
    **Kubernetes/Docker liveness probe**
    
    Indicates the application process is alive and running.
    Used by orchestration systems to restart unhealthy containers.
    """
    try:
        logger.debug("Liveness probe check")
        return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Liveness check failed: {str(e)}")
        # Even if logging fails, try to return alive
        return {"status": "alive"}