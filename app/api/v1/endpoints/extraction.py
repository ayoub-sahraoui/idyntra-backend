from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from app.dependencies import get_mrz_extractor, get_logger
from app.api.v1.schemas import ExtractionResponse
from app.utils.image_processing import read_uploaded_image
from app.utils.validation import validate_file, FileMetadata
from datetime import datetime

router = APIRouter(prefix="/api/v1", tags=["extraction"])


@router.post("/extract-text", response_model=ExtractionResponse)
async def extract_document_text(
    document: UploadFile = File(..., description="Document image with MRZ zone"),
    extractor = Depends(get_mrz_extractor),
    logger = Depends(get_logger)
):
    """
    **Extract MRZ data from document**

    Supports:
    - Passports
    - ID cards
    - Visas
    - Other machine-readable documents

    Uses multiple OCR engines with fallback support.
    """

    try:
        logger.info(f"=== MRZ EXTRACTION REQUEST START ===")
        logger.info(f"Document: {document.filename}, Content-Type: {document.content_type}")
        
        # Check if extractor is available
        if extractor is None:
            logger.error("CRITICAL: MRZ Extractor is None!")
            raise HTTPException(status_code=503, detail="MRZ extraction service not initialized")

        # Read image
        try:
            logger.info("Reading document image...")
            image = await read_uploaded_image(document)
            logger.info(f"✓ Document image read, shape: {image.shape}")
        except Exception as e:
            logger.error(f"Image reading failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to read image: {str(e)}")

        # Extract MRZ
        try:
            logger.info("Starting MRZ extraction...")
            result = extractor.extract(image)
            logger.info(f"✓ MRZ extraction completed")
        except Exception as e:
            logger.error(f"MRZ extraction failed: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"MRZ extraction failed: {str(e)}")

        fields_extracted = sum(1 for v in result.values() if v is not None and v != '')
        mrz_detected = fields_extracted > 0

        # Map to structured response format
        structured_data = extractor.map_mrz_to_api_response(result) if mrz_detected else None

        response = ExtractionResponse(
            success=True,
            mrz_detected=mrz_detected,
            fields_extracted=fields_extracted,
            message=(
                f"✅ MRZ detected - {fields_extracted} fields extracted"
                if mrz_detected
                else "⚠️ No MRZ detected. Ensure document is clear and MRZ zone is visible."
            ),
            structured_data=structured_data,
            timestamp=datetime.utcnow()
        )

        logger.info(f"=== MRZ EXTRACTION COMPLETE: {fields_extracted} fields ===")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"UNEXPECTED ERROR: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")