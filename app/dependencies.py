from functools import lru_cache
from app.config import get_settings
from app.core.liveness import LivenessDetector, LivenessConfig
from app.core.face_matching import FaceMatcher
from app.core.document_auth import DocumentAuthenticator
from app.core.deepfake import DeepfakeDetector
from app.core.mrz_extraction import MRZExtractor
from app.services.verification_service import VerificationService
import logging


@lru_cache()
def get_logger() -> logging.Logger:
    """Get application logger"""
    return logging.getLogger("idv_api")


@lru_cache()
def get_liveness_detector() -> LivenessDetector:
    """Get liveness detector instance"""
    settings = get_settings()
    config = LivenessConfig(
        blur_threshold=settings.BLUR_THRESHOLD,
        liveness_score_threshold=settings.LIVENESS_SCORE_MIN
    )
    return LivenessDetector(config)


@lru_cache()
def get_face_matcher() -> FaceMatcher:
    """Get face matcher instance"""
    settings = get_settings()
    return FaceMatcher(
        tolerance=settings.FACE_MATCH_TOLERANCE,
        use_gpu=not settings.CPU_ONLY
    )


@lru_cache()
def get_document_authenticator() -> DocumentAuthenticator:
    """Get document authenticator instance"""
    settings = get_settings()
    return DocumentAuthenticator(
        min_score=settings.AUTHENTICITY_SCORE_MIN
    )


@lru_cache()
def get_deepfake_detector() -> DeepfakeDetector:
    """Get deepfake detector instance"""
    settings = get_settings()
    return DeepfakeDetector(
        model_name=settings.DEEPFAKE_MODEL_NAME,
        use_gpu=not settings.CPU_ONLY
    )


@lru_cache()
def get_mrz_extractor() -> MRZExtractor:
    """Get MRZ extractor instance"""
    return MRZExtractor()


@lru_cache()
def get_verification_service() -> VerificationService:
    """Get verification service with all dependencies"""
    return VerificationService(
        liveness_detector=get_liveness_detector(),
        face_matcher=get_face_matcher(),
        doc_checker=get_document_authenticator(),
        deepfake_detector=get_deepfake_detector(),
        config=get_settings(),
        logger=get_logger()
    )