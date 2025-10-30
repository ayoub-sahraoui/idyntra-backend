from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from app.services.verification_service import VerificationService
from app.dependencies import get_verification_service, get_logger
from app.api.v1.schemas import VerificationResponse
from app.utils.image_processing import read_uploaded_image
import uuid
from datetime import datetime

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
        # Validate file types
        if not id_document.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="ID document must be an image")
        if not selfie.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Selfie must be an image")

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