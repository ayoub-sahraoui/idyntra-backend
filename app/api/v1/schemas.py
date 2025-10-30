from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class LivenessCheckResponse(BaseModel):
    is_live: bool
    liveness_score: float = Field(..., ge=0.0, le=1.0)
    checks_passed: str
    confidence: str
    checks: Dict[str, Any]


class FaceMatchResponse(BaseModel):
    matched: bool
    confidence: float = Field(..., ge=0.0, le=100.0)
    distance: Optional[float] = None
    strategy: str


class DocumentAuthResponse(BaseModel):
    is_authentic: bool
    authenticity_score: float = Field(..., ge=0.0, le=100.0)
    checks_passed: str
    checks: Dict[str, Any]


class DeepfakeCheckResponse(BaseModel):
    is_real: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    label: Optional[str] = None
    model_available: bool


class StructuredDataResponse(BaseModel):
    # Core identity fields
    prenom: Optional[str] = None
    nom: Optional[str] = None
    nom_complet: Optional[str] = None
    sexe: Optional[str] = None
    
    # Dates (normalized to YYYYMMDD format)
    date_naissance: Optional[str] = None
    date_expiration: Optional[str] = None
    date_emission: Optional[str] = None
    lieu_naissance: Optional[str] = None
    
    # Document information
    type_document: Optional[str] = None
    numero_carte: Optional[str] = None  # Maps to numero_document
    numero_document: Optional[str] = None
    numero_personnel: Optional[str] = None
    
    # Nationality and country
    can: Optional[str] = None  # Maps to nationalite
    nationalite: Optional[str] = None
    pays_emission: Optional[str] = None
    
    # Check digits for validation
    check_digit_document: Optional[str] = None
    check_digit_naissance: Optional[str] = None
    check_digit_expiration: Optional[str] = None
    check_digit_final: Optional[str] = None
    
    # Raw MRZ data
    raw_mrz: Optional[str] = None
    mrz_type: Optional[str] = None
    
    # Additional fields that might be extracted
    additional_fields: Optional[Dict[str, Any]] = None


class VerificationResponse(BaseModel):
    """Main verification response"""
    verification_id: str
    timestamp: datetime
    status: str = Field(..., description="approved, rejected, manual_review, or error")
    overall_confidence: float = Field(..., ge=0.0, le=100.0)
    message: str

    # Individual check results
    face_match: Optional[FaceMatchResponse] = None
    liveness_check: Optional[LivenessCheckResponse] = None
    deepfake_check: Optional[DeepfakeCheckResponse] = None
    document_authenticity: Optional[DocumentAuthResponse] = None

    class Config:
        json_schema_extra = {
            "example": {
                "verification_id": "123e4567-e89b-12d3-a456-426614174000",
                "timestamp": "2025-10-26T12:00:00Z",
                "status": "approved",
                "overall_confidence": 92.5,
                "message": "✅ Identity verified successfully",
                "face_match": {
                    "matched": True,
                    "confidence": 95.2,
                    "distance": 0.35
                }
            }
        }


class ExtractionResponse(BaseModel):
    """MRZ extraction response"""
    success: bool
    mrz_detected: bool
    fields_extracted: int
    message: str
    structured_data: Optional[StructuredDataResponse] = None
    timestamp: datetime


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    device: str
    gpu_available: bool
    timestamp: datetime
    components: Dict[str, bool]