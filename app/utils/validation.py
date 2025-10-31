from typing import List, Dict, Optional, Set
import magic
import hashlib
from pathlib import Path
import asyncio
from fastapi import UploadFile, HTTPException
from pydantic import BaseModel, Field
import logging
from app.config import get_settings

# Initialize mime-type checker
mime = magic.Magic(mime=True)

# Allowed image types and their corresponding MIME types
ALLOWED_IMAGE_TYPES = {
    'image/jpeg',
    'image/png',
    'image/webp'
}

# File size limits
MAX_FILE_SIZE = get_settings().MAX_UPLOAD_SIZE  # From config

class FileValidationError(HTTPException):
    """Custom exception for file validation errors"""
    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)

class FileMetadata(BaseModel):
    """File metadata model"""
    filename: str
    size: int
    mime_type: str
    hash: str = Field(..., description="SHA-256 hash of file contents")
    width: Optional[int] = None
    height: Optional[int] = None

async def validate_file(
    file: UploadFile,
    allowed_types: Set[str] = ALLOWED_IMAGE_TYPES,
    max_size: int = MAX_FILE_SIZE,
    min_dimensions: Optional[tuple] = (100, 100),
    max_dimensions: Optional[tuple] = (4096, 4096)
) -> FileMetadata:
    """
    Comprehensive file validation

    Args:
        file: FastAPI UploadFile
        allowed_types: Set of allowed MIME types
        max_size: Maximum file size in bytes
        min_dimensions: Minimum (width, height) for images
        max_dimensions: Maximum (width, height) for images

    Returns:
        FileMetadata: Validated file metadata

    Raises:
        FileValidationError: If validation fails
    """
    try:
        # Read file contents
        contents = await file.read()
        
        # Reset file position for subsequent reads
        await file.seek(0)
        
        # Basic checks
        if not contents:
            raise FileValidationError("Empty file")
            
        file_size = len(contents)
        if file_size > max_size:
            raise FileValidationError(
                f"File too large. Maximum size: {max_size // (1024*1024)}MB"
            )
            
        # Calculate hash
        file_hash = hashlib.sha256(contents).hexdigest()
        
        # Check MIME type
        detected_type = mime.from_buffer(contents)
        if detected_type not in allowed_types:
            raise FileValidationError(
                f"Invalid file type: {detected_type}. Allowed types: {', '.join(allowed_types)}"
            )
            
        # Image-specific validation
        width = height = None
        if detected_type.startswith('image/'):
            from PIL import Image
            import io
            
            try:
                img = Image.open(io.BytesIO(contents))
                width, height = img.size
                
                # Check dimensions
                if min_dimensions and (width < min_dimensions[0] or height < min_dimensions[1]):
                    raise FileValidationError(
                        f"Image too small. Minimum dimensions: {min_dimensions[0]}x{min_dimensions[1]}"
                    )
                    
                if max_dimensions and (width > max_dimensions[0] or height > max_dimensions[1]):
                    raise FileValidationError(
                        f"Image too large. Maximum dimensions: {max_dimensions[0]}x{max_dimensions[1]}"
                    )
                    
            except FileValidationError:
                raise
            except Exception as e:
                raise FileValidationError(f"Invalid image format: {str(e)}")
                
        return FileMetadata(
            filename=file.filename,
            size=file_size,
            mime_type=detected_type,
            hash=file_hash,
            width=width,
            height=height
        )
        
    except FileValidationError:
        raise
    except Exception as e:
        raise FileValidationError(f"File validation failed: {str(e)}")

async def validate_files(files: List[UploadFile], **kwargs) -> List[FileMetadata]:
    """
    Validate multiple files concurrently

    Args:
        files: List of FastAPI UploadFile objects
        **kwargs: Additional arguments passed to validate_file

    Returns:
        List[FileMetadata]: List of validated file metadata
    """
    tasks = [validate_file(file, **kwargs) for file in files]
    return await asyncio.gather(*tasks)

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and ensure safe storage

    Args:
        filename: Original filename

    Returns:
        str: Sanitized filename
    """
    # Remove path components
    filename = Path(filename).name
    
    # Remove potentially dangerous characters
    forbidden_chars = '<>:"/\\|?*'
    for char in forbidden_chars:
        filename = filename.replace(char, '_')
        
    return filename