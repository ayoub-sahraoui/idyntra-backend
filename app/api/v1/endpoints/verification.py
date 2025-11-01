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