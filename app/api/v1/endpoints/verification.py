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


@router.post("/verify", response_model=VerificationResponse)
async def verify_identity(
    id_document: UploadFile = File(..., description="ID card, passport, or driver's license"),
    selfie: UploadFile = File(..., description="Live selfie photo"),
    service: VerificationService = Depends(get_verification_service),
    logger = Depends(get_logger)
):
    """
    **Verify identity with document and selfie**

    This endpoint performs comprehensive identity verification including:
    - Liveness detection (anti-spoofing)
    - Face matching between document and selfie
    - Document authenticity checks
    - Deepfake detection

    **Returns:**
    - `approved`: High confidence verification
    - `manual_review`: Medium confidence, human review recommended
    - `rejected`: Failed security checks
    - `error`: System error occurred
    """

    verification_id = str(uuid.uuid4())
    logger.info(f"[{verification_id}] Verification request: {id_document.filename}, {selfie.filename}")

    try:
        # Validate files
        file_metadata: List[FileMetadata] = await validate_files(
            [id_document, selfie],
            min_dimensions=(640, 480),  # Minimum resolution for good quality
            max_dimensions=(4096, 4096)  # Reasonable maximum size
        )
        
        logger.info(
            f"[{verification_id}] File validation passed: "
            f"ID ({file_metadata[0].width}x{file_metadata[0].height}), "
            f"Selfie ({file_metadata[1].width}x{file_metadata[1].height})"
        )

        # Read images
        id_img = await read_uploaded_image(id_document)
        selfie_img = await read_uploaded_image(selfie)

        # Run verification
        result = await service.verify_identity(id_img, selfie_img)

        # Build response
        response = VerificationResponse(
            verification_id=verification_id,
            timestamp=datetime.utcnow(),
            **result
        )

        logger.info(f"[{verification_id}] Verification complete: {result['status']}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[{verification_id}] Verification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")