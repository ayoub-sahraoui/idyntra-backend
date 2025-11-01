from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from app.services.verification_service import VerificationService
from app.dependencies import get_verification_service, get_logger
from app.api.v1.schemas import VerificationResponse
from app.utils.image_processing import read_uploaded_image
from app.utils.validation import validate_files, FileMetadata
import uuid
from datetime import datetime
from typing import List

router = APIRouter(prefix="/api/v1", tags=["verification"])


@router.post(
    "/verify",
    response_model=VerificationResponse,
    summary="Verify Identity",
    description="""
    Perform comprehensive identity verification by comparing a government-issued ID document with a live selfie.
    
    ## Security Checks Performed:
    
    1. **Liveness Detection** - Verifies the selfie is from a live person (not a photo of a photo, screen, or mask)
    2. **Face Matching** - Compares the face in the ID document with the selfie face
    3. **Deepfake Detection** - Ensures the selfie is not AI-generated or manipulated
    4. **Document Authenticity** - Checks for signs of document tampering or forgery
    
    ## Response Status Values:
    
    - **approved** (≥75% confidence) - High confidence verification, identity confirmed
    - **manual_review** (55-74% confidence) - Medium confidence, human review recommended
    - **rejected** (<55% confidence) - Failed security checks, identity not verified
    
    ## Requirements:
    
    - **ID Document**: Clear photo of government ID (passport, driver's license, ID card)
      - Format: JPEG, PNG
      - Size: 640x480 minimum, 4096x4096 maximum
      - File size: Max 10MB
      
    - **Selfie**: Live photo of the person's face
      - Format: JPEG, PNG
      - Size: 640x480 minimum, 4096x4096 maximum
      - File size: Max 10MB
      - Should be well-lit, facing camera
    
    ## Authentication:
    
    Requires `X-API-Key` header with valid API key.
    
    ## Response Time:
    
    Typical response time: 10-15 seconds
    """,
    responses={
        200: {
            "description": "Verification completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "verification_id": "54ee01af-5059-40da-bf40-e5e9092bdade",
                        "timestamp": "2025-11-01T19:17:04.473461",
                        "status": "approved",
                        "overall_confidence": 78.5,
                        "message": "✅ Identity verified (confidence: 78.5%)",
                        "face_match": {"matched": True, "confidence": 85.2, "distance": 0.32, "strategy": "face_recognition"},
                        "liveness_check": {"is_live": True, "liveness_score": 0.83, "checks_passed": "5/6", "confidence": "high"},
                        "deepfake_check": {"is_real": True, "confidence": 0.99, "label": "Real", "model_available": True},
                        "document_authenticity": {"is_authentic": True, "authenticity_score": 100.0, "checks_passed": "1/1"}
                    }
                }
            }
        },
        400: {"description": "Invalid request - file validation failed"},
        403: {"description": "Authentication failed - invalid or missing API key"},
        500: {"description": "Internal server error - verification process failed"},
        503: {"description": "Service unavailable - ML models not initialized"}
    }
)
async def verify_identity(
    id_document: UploadFile = File(..., description="Government-issued ID document (passport, driver's license, or ID card)"),
    selfie: UploadFile = File(..., description="Live selfie photo of the person"),
    service: VerificationService = Depends(get_verification_service),
    logger = Depends(get_logger)
):
    """Verify identity with comprehensive security checks"""

    verification_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[{verification_id}] === VERIFICATION REQUEST START ===")
        logger.info(f"[{verification_id}] ID Document: {id_document.filename}, Content-Type: {id_document.content_type}")
        logger.info(f"[{verification_id}] Selfie: {selfie.filename}, Content-Type: {selfie.content_type}")
        
        # Check if service is available
        if service is None:
            logger.error(f"[{verification_id}] CRITICAL: VerificationService is None!")
            raise HTTPException(status_code=503, detail="Verification service not initialized")
        
        logger.info(f"[{verification_id}] Service available, starting validation...")

        # Validate files
        try:
            file_metadata: List[FileMetadata] = await validate_files(
                [id_document, selfie],
                min_dimensions=(640, 480),
                max_dimensions=(4096, 4096)
            )
            logger.info(
                f"[{verification_id}] ✓ File validation passed: "
                f"ID ({file_metadata[0].width}x{file_metadata[0].height}), "
                f"Selfie ({file_metadata[1].width}x{file_metadata[1].height})"
            )
        except Exception as e:
            logger.error(f"[{verification_id}] File validation failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"File validation failed: {str(e)}")

        # Read images
        try:
            logger.info(f"[{verification_id}] Reading images...")
            id_img = await read_uploaded_image(id_document)
            logger.info(f"[{verification_id}] ✓ ID document image read, shape: {id_img.shape}")
            
            selfie_img = await read_uploaded_image(selfie)
            logger.info(f"[{verification_id}] ✓ Selfie image read, shape: {selfie_img.shape}")
        except Exception as e:
            logger.error(f"[{verification_id}] Image reading failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to read images: {str(e)}")

        # Run verification
        try:
            logger.info(f"[{verification_id}] Starting verification process...")
            result = await service.verify_identity(id_img, selfie_img)
            logger.info(f"[{verification_id}] ✓ Verification process completed")
        except Exception as e:
            logger.error(f"[{verification_id}] Verification process failed: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Verification process failed: {str(e)}")

        # Build response
        response = VerificationResponse(
            verification_id=verification_id,
            timestamp=datetime.utcnow(),
            **result
        )

        logger.info(f"[{verification_id}] === VERIFICATION COMPLETE: {result['status']} ===")
        return response

    except HTTPException:
        logger.error(f"[{verification_id}] HTTPException raised")
        raise
    except Exception as e:
        logger.exception(f"[{verification_id}] UNEXPECTED ERROR: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")