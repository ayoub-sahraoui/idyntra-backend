from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class LivenessCheckResponse(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "is_live": True,
                "liveness_score": 0.6666666666666666,
                "checks_passed": "4/6",
                "confidence": "medium",
                "checks": {
                    "_check_blur": {"blur_score": 16.26, "passed": False},
                    "_detect_specular_reflections": {"reflection_score": 0.044, "passed": False},
                    "_analyze_micro_texture": {"micro_texture_score": 0.497, "passed": True},
                    "_detect_print_attack": {"high_freq_energy": 6586982084.085535, "passed": True},
                    "_estimate_depth_cues": {"depth_score": 0.586, "passed": True},
                    "_check_face_proportions": {
                        "passed": True,
                        "face_width": 666,
                        "face_height": 666,
                        "aspect_ratio": 1,
                        "size_valid": True,
                        "proportion_valid": True
                    }
                }
            }
        }
    }
    
    is_live: bool = Field(..., description="Whether the image is determined to be from a live person")
    liveness_score: float = Field(..., ge=0.0, le=1.0, description="Liveness score (0-1)")
    checks_passed: str = Field(..., description="Number of checks passed (e.g., '4/6')")
    confidence: str = Field(..., description="Confidence level: low, medium, or high")
    checks: Dict[str, Any] = Field(..., description="Detailed results for each liveness check")


class FaceMatchResponse(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "matched": True,
                "confidence": 60.28588325822444,
                "distance": 0.39714116741775557,
                "strategy": "face_recognition"
            }
        }
    }
    
    matched: bool = Field(..., description="Whether faces match between document and selfie")
    confidence: float = Field(..., ge=0.0, le=100.0, description="Match confidence percentage (0-100)")
    distance: float = Field(..., description="Face distance metric (lower = more similar)")
    strategy: str = Field(..., description="Matching strategy used (e.g., 'face_recognition')")


class DocumentAuthResponse(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "is_authentic": True,
                "authenticity_score": 100.0,
                "checks_passed": "1/1",
                "checks": {
                    "tampering": {
                        "is_tampered": False,
                        "uniformity": 0.6135338126974514,
                        "passed": True
                    }
                }
            }
        }
    }
    
    is_authentic: bool = Field(..., description="Whether the document appears authentic")
    authenticity_score: float = Field(..., ge=0.0, le=100.0, description="Authenticity score percentage (0-100)")
    checks_passed: str = Field(..., description="Number of authenticity checks passed (e.g., '1/1')")
    checks: Dict[str, Any] = Field(..., description="Detailed results for each authenticity check")


class DeepfakeCheckResponse(BaseModel):
    model_config = {
        "protected_namespaces": (),  # Allow 'model_' prefix
        "json_schema_extra": {
            "example": {
                "is_real": True,
                "confidence": 0.9970235228538513,
                "label": "Real",
                "model_available": True
            }
        }
    }
    
    is_real: bool = Field(..., description="Whether the image is determined to be real (not a deepfake)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    label: str = Field(..., description="Classification label: 'Real' or 'Fake'")
    model_available: bool = Field(..., description="Whether the deepfake detection model is loaded")


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
    verification_id: str = Field(..., description="Unique identifier for this verification")
    timestamp: datetime = Field(..., description="ISO 8601 timestamp of verification")
    status: str = Field(..., description="Verification status: 'approved', 'rejected', 'manual_review', or 'error'")
    overall_confidence: float = Field(..., ge=0.0, le=100.0, description="Overall confidence score (0-100)")
    message: str = Field(..., description="Human-readable verification result message")

    # Individual check results (all present in response)
    face_match: FaceMatchResponse = Field(..., description="Face matching results between document and selfie")
    liveness_check: LivenessCheckResponse = Field(..., description="Liveness detection results")
    deepfake_check: DeepfakeCheckResponse = Field(..., description="Deepfake detection results")
    document_authenticity: DocumentAuthResponse = Field(..., description="Document authenticity verification results")

    model_config = {
        "json_schema_extra": {
            "example": {
                "verification_id": "54ee01af-5059-40da-bf40-e5e9092bdade",
                "timestamp": "2025-11-01T19:17:04.473461",
                "status": "manual_review",
                "overall_confidence": 73.42,
                "message": "⚠️ Manual review required (confidence: 73.4%)",
                "face_match": {
                    "matched": True,
                    "confidence": 60.28588325822444,
                    "distance": 0.39714116741775557,
                    "strategy": "face_recognition"
                },
                "liveness_check": {
                    "is_live": True,
                    "liveness_score": 0.6666666666666666,
                    "checks_passed": "4/6",
                    "confidence": "medium",
                    "checks": {
                        "_check_blur": {"blur_score": 16.26, "passed": False},
                        "_analyze_micro_texture": {"micro_texture_score": 0.497, "passed": True}
                    }
                },
                "deepfake_check": {
                    "is_real": True,
                    "confidence": 0.9970235228538513,
                    "label": "Real",
                    "model_available": True
                },
                "document_authenticity": {
                    "is_authentic": True,
                    "authenticity_score": 100.0,
                    "checks_passed": "1/1",
                    "checks": {
                        "tampering": {"is_tampered": False, "uniformity": 0.613, "passed": True}
                    }
                }
            }
        }
    }


class ExtractionResponse(BaseModel):
    """MRZ extraction response"""
    success: bool = Field(..., description="Whether the extraction operation was successful")
    mrz_detected: bool = Field(..., description="Whether MRZ (Machine Readable Zone) was detected")
    fields_extracted: int = Field(..., ge=0, description="Number of fields successfully extracted")
    message: str = Field(..., description="Human-readable result message")
    structured_data: Optional[StructuredDataResponse] = Field(None, description="Structured extracted data (null if no MRZ detected)")
    timestamp: datetime = Field(..., description="ISO 8601 timestamp of extraction")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "mrz_detected": True,
                "fields_extracted": 12,
                "message": "✅ MRZ detected - 12 fields extracted",
                "structured_data": {
                    "prenom": "JOHN",
                    "nom": "DOE",
                    "date_naissance": "19900115",
                    "nationalite": "USA",
                    "numero_document": "P123456789"
                },
                "timestamp": "2025-11-01T19:00:00Z"
            }
        }
    }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Overall health status: 'healthy', 'degraded', or 'unhealthy'")
    version: str = Field(..., description="API version")
    device: str = Field(..., description="Processing device: 'cpu' or 'gpu'")
    gpu_available: bool = Field(..., description="Whether GPU acceleration is available")
    timestamp: datetime = Field(..., description="ISO 8601 timestamp of health check")
    components: Dict[str, bool] = Field(..., description="Status of individual components")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "version": "2.0.0",
                "device": "cpu",
                "gpu_available": False,
                "timestamp": "2025-11-01T19:00:00Z",
                "components": {
                    "api": True,
                    "config": True,
                    "liveness_detector": True,
                    "face_matcher": True,
                    "deepfake_detector": True,
                    "mrz_extractor": True
                }
            }
        }
    }