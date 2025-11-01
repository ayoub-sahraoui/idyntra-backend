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
async def root():
    """Root endpoint"""
    return {
        "service": "Enhanced ID Verification API",
        "version": get_settings().VERSION,
        "status": "online"
    }


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    **Basic health check**

    Returns API status without loading ML models.
    For detailed component status, use /health/detailed
    """

    settings = get_settings()

    # Basic health check without loading models
    return HealthResponse(
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
    Note: First call may take 2-5 minutes while models download.
    """

    settings = get_settings()

    components = {
        "liveness_detector": liveness is not None,
        "face_matcher": face_matcher is not None,
        "deepfake_detector": deepfake is not None,
        "mrz_extractor": mrz is not None,
        "readmrz": mrz.engines.get('readmrz', False) if mrz else False,
        "passport_mrz_extractor": mrz.engines.get('passport_mrz_extractor', False) if mrz else False
    }

    all_healthy = all(components.values())

    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        version=settings.VERSION,
        device="gpu" if torch.cuda.is_available() and not settings.CPU_ONLY else "cpu",
        gpu_available=torch.cuda.is_available() and not settings.CPU_ONLY,
        timestamp=datetime.utcnow(),
        components=components
    )


@router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive"}