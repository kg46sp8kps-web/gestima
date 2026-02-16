"""
GESTIMA - STEP File Router

Endpoints for serving and listing STEP/STP files from uploads/drawings/.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response

from app.models.user import User
from app.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOADS_DIR = Path(__file__).parent.parent.parent / "uploads" / "drawings"


@router.get("/api/step/raw/{filename}")
async def get_step_file(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """
    Download raw STEP file.

    Args:
        filename: STEP filename in uploads/drawings/

    Returns:
        Binary STEP file content

    Raises:
        404: File not found
    """
    try:
        # Path traversal protection
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")

        filepath = UPLOADS_DIR / filename

        # Verify resolved path stays within UPLOADS_DIR
        if not filepath.resolve().is_relative_to(UPLOADS_DIR.resolve()):
            raise HTTPException(status_code=400, detail="Invalid filename")

        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")

        # Read and return binary content
        with open(filepath, 'rb') as f:
            content = f.read()

        return Response(
            content=content,
            media_type='application/octet-stream',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STEP file download failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/step-files/list")
async def list_step_files(
    current_user: User = Depends(get_current_user)
):
    """
    List all STEP files in uploads/drawings directory.

    Returns:
        List of dictionaries with filename and size
    """
    try:
        if not UPLOADS_DIR.exists():
            return []

        files = []
        for filepath in UPLOADS_DIR.glob("*.step"):
            if filepath.is_file():
                files.append({
                    "filename": filepath.name,
                    "size_kb": round(filepath.stat().st_size / 1024, 1)
                })

        # Sort by filename
        files.sort(key=lambda x: x["filename"])

        return files

    except Exception as e:
        logger.error(f"Failed to list STEP files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
