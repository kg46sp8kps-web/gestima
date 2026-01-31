"""GESTIMA - Uploads API router"""

import logging
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

from app.dependencies import get_current_user
from app.models import User
from app.schemas.upload import TempUploadResponse
from app.services.drawing_service import DrawingService

logger = logging.getLogger(__name__)
router = APIRouter()

# Upload directories (keep backwards compatibility)
TEMP_UPLOAD_DIR = Path("uploads/temp")
DRAWINGS_DIR = Path("uploads/drawings")

# Ensure directories exist
TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DRAWINGS_DIR.mkdir(parents=True, exist_ok=True)

# In-memory temp file registry (in production, use Redis or DB)
temp_files: Dict[str, str] = {}

# Drawing service
drawing_service = DrawingService()


@router.post("/temp", response_model=TempUploadResponse)
async def upload_temp_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload file to temporary storage.
    Returns temp_id for later use in part creation.

    Security checks:
    - PDF validation via magic bytes (not just MIME type)
    - File size limit (10MB)
    - Temp files auto-cleanup after 24h

    Returns:
        TempUploadResponse: temp_id, filename, size, uploaded_at
    """
    # SECURITY: Validate PDF using magic bytes (not just MIME type!)
    await drawing_service.validate_pdf(file)

    # Validate file size (streaming, no memory overflow)
    file_size = await drawing_service.validate_file_size(file)

    # Generate temp ID
    temp_id = str(uuid.uuid4())

    # Save file to temp directory
    temp_path = TEMP_UPLOAD_DIR / f"{temp_id}.pdf"

    try:
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Register in memory (for backwards compatibility)
        temp_files[temp_id] = str(temp_path)

        logger.info(f"Temp file uploaded: {temp_id} by {current_user.username} ({file_size} bytes)")

        return TempUploadResponse(
            temp_id=temp_id,
            filename=file.filename or "unknown.pdf",
            size=file_size,
            uploaded_at=datetime.utcnow()
        )

    except HTTPException:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"Failed to save temp file: {e}", exc_info=True)
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail="Failed to save file")
    finally:
        await file.close()


@router.delete("/temp/{temp_id}")
async def delete_temp_file(
    temp_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete temporary file"""
    if temp_id not in temp_files:
        raise HTTPException(status_code=404, detail="Temp file not found")

    temp_path = Path(temp_files[temp_id])
    if temp_path.exists():
        temp_path.unlink()

    del temp_files[temp_id]

    logger.info(f"Temp file deleted: {temp_id} by {current_user.username}")
    return {"message": "Temp file deleted"}
