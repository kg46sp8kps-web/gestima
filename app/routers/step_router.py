"""
GESTIMA - STEP Raw Geometry Router

Minimal endpoint for extracting raw OCCT geometry data.
NO feature classification, NO interpretation.

For future Vision API integration.

ADR-042: OCCT Simplification - Raw Extraction Only
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.dependencies import get_current_user
from app.services.step_raw_extractor import extract_raw_geometry
from app.services.geometry_feature_extractor import GeometryFeatureExtractor

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOADS_DIR = Path(__file__).parent.parent.parent / "uploads" / "drawings"


@router.get("/api/step/raw-geometry/{filename}", response_model=dict)
async def get_step_raw_geometry(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Extract raw geometry measurements from STEP file.

    NO classification! Returns basic facts:
    - Bounding box (L×W×H)
    - Volume
    - Cylindrical faces (diameter, z-range, orientation)
    - Planar faces (z-position, area)

    For future Claude Vision API context.

    Args:
        filename: STEP filename in uploads/drawings/

    Returns:
        {
            "filename": str,
            "bbox_mm": {"length": float, "width": float, "height": float},
            "volume_mm3": float,
            "cylindrical_faces": [...],
            "planar_faces": [...],
            "source": "occt"
        }

    Raises:
        404: File not found
        500: OCCT extraction failed
    """
    try:
        filepath = Path("uploads/drawings") / filename

        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")

        if not filename.lower().endswith(('.step', '.stp')):
            raise HTTPException(status_code=400, detail="Not a STEP file")

        # Extract raw geometry (sync function, runs in thread pool)
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, extract_raw_geometry, filepath
        )

        return result

    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f"OCCT not available: {e}")
        raise HTTPException(
            status_code=503,
            detail="OCCT not available - install pythonocc-core"
        )
    except Exception as e:
        logger.error(f"Raw geometry extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
        filepath = Path("uploads/drawings") / filename

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


@router.get("/api/geometry-features/extract")
async def extract_geometry_features(
    filename: str,
    material: str = "20910000",  # Default: Ocel automatová
    current_user: User = Depends(get_current_user)
):
    """
    Extract 56 proxy features from STEP file.

    Query params:
        filename: STEP filename in uploads/drawings/
        material: Material code (8-digit, default: 20910000)

    Returns:
        GeometryFeatures schema (56 proxy metrics)
    """
    try:
        step_path = UPLOADS_DIR / filename
        if not step_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")

        extractor = GeometryFeatureExtractor()
        features = extractor.extract_features(step_path, material)

        return features.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Feature extraction failed for {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
