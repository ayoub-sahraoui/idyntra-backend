from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, Field
from functools import lru_cache
from typing import List
import os


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
        protected_namespaces=()  # Allow fields starting with 'model_'
    )

    # API Info
    APP_NAME: str = "Enhanced ID Verification API"
    VERSION: str = "2.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # Security Settings
    # CORS and Host Validation - Use string to avoid JSON parsing issues
    ALLOWED_ORIGINS: str = "*"
    ALLOWED_HOSTS: str = "*"
    
    # Rate Limiting
    MAX_REQUESTS_PER_MINUTE: int = 60
    
    # API Authentication (comma-separated string, converted to list at runtime)
    VALID_API_KEYS: str = ""
    
    # Security Headers
    ENABLE_SECURITY_HEADERS: bool = True
    CSP_POLICY: str = "default-src 'self'; img-src 'self' data:; script-src 'self'"
    HSTS_MAX_AGE: int = 31536000  # 1 year in seconds

    # Hardware
    CPU_ONLY: bool = False
    CUDA_VISIBLE_DEVICES: str = "0"

    # Verification Thresholds
    # Liveness Detection
    LIVENESS_SCORE_MIN: float = 0.55  # Minimum score to pass (55% of checks)
    LIVENESS_SCORE_HIGH: float = 0.75  # High confidence threshold
    BLUR_THRESHOLD: float = 80.0  # Lowered for better tolerance (was 100.0)

    # Face Matching
    FACE_MATCH_CONFIDENCE_MIN: float = 65.0  # Minimum confidence to consider a match
    FACE_MATCH_CONFIDENCE_HIGH: float = 80.0  # High confidence threshold
    FACE_MATCH_TOLERANCE: float = 0.5  # Distance tolerance (lower = stricter)

    # Document Authenticity
    AUTHENTICITY_SCORE_MIN: float = 50.0  # Minimum authenticity score
    AUTHENTICITY_SCORE_HIGH: float = 70.0  # High confidence threshold

    # Deepfake Detection
    DEEPFAKE_CONFIDENCE_MIN: float = 0.65  # Minimum confidence that image is real
    IMAGE_QUALITY_MIN: float = 50.0  # Minimum image quality score

    # Deepfake Detection
    DEEPFAKE_MODEL_NAME: str = "dima806/deepfake_vs_real_image_detection"

    # OCR Configuration
    TESSDATA_PREFIX: str = "/usr/share/tesseract-ocr/4/tessdata"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "idv_api.log"
    LOG_MAX_BYTES: int = 5 * 1024 * 1024
    LOG_BACKUP_COUNT: int = 3

    # Timeouts
    REQUEST_TIMEOUT: int = 30

    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance"""
    return Settings()