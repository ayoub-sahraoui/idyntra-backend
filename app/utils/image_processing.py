import numpy as np
import cv2
from PIL import Image
import io
from fastapi import UploadFile, HTTPException


async def read_uploaded_image(file: UploadFile) -> np.ndarray:
    """
    Read and validate uploaded image file

    Args:
        file: FastAPI UploadFile

    Returns:
        numpy.ndarray: OpenCV image in BGR format

    Raises:
        HTTPException: If image is invalid or cannot be read
    """
    try:
        # Read file contents
        contents = await file.read()

        # Validate size (e.g., max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(contents) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"Image too large. Maximum size: {max_size // (1024*1024)}MB"
            )

        # Open with PIL
        try:
            image = Image.open(io.BytesIO(contents))
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image format: {str(e)}"
            )

        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Convert to numpy array and then to BGR (OpenCV format)
        np_image = np.array(image)
        bgr_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)

        # Validate dimensions
        height, width = bgr_image.shape[:2]
        if height < 100 or width < 100:
            raise HTTPException(
                status_code=400,
                detail="Image too small. Minimum size: 100x100 pixels"
            )

        if height > 4096 or width > 4096:
            raise HTTPException(
                status_code=400,
                detail="Image too large. Maximum size: 4096x4096 pixels"
            )

        return bgr_image

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to read image: {str(e)}"
        )


def resize_image(image: np.ndarray, max_dimension: int = 1920) -> np.ndarray:
    """
    Resize image if it exceeds max dimension while maintaining aspect ratio

    Args:
        image: Input image
        max_dimension: Maximum width or height

    Returns:
        Resized image
    """
    height, width = image.shape[:2]

    if height <= max_dimension and width <= max_dimension:
        return image

    # Calculate scaling factor
    scale = max_dimension / max(height, width)
    new_width = int(width * scale)
    new_height = int(height * scale)

    return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)


def validate_image_quality(image: np.ndarray) -> dict:
    """
    Quick image quality validation

    Returns:
        dict with quality metrics
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    # Check blur
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()

    # Check brightness
    brightness = np.mean(gray)

    # Check contrast
    contrast = np.std(gray)

    return {
        "blur_score": float(blur_score),
        "is_blurry": blur_score < 50,
        "brightness": float(brightness),
        "is_too_dark": brightness < 50,
        "is_too_bright": brightness > 200,
        "contrast": float(contrast),
        "is_low_contrast": contrast < 30
    }