"""GESTIMA - Machining Time Estimation API Router

Physics-based machining time estimation endpoints.
ADR-040: Machining Time Estimation System
"""

import logging
import json
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.material import MaterialGroup
from app.schemas.machining_time import (
    MachiningTimeEstimateResponse,
    MaterialListItem,
    MachiningTimeReEstimateRequest,
)
from app.services.machining_time_estimation_service import MachiningTimeEstimationService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/estimate",
    response_model=MachiningTimeEstimateResponse,
    status_code=status.HTTP_200_OK
)
async def estimate_machining_time(
    step_file: UploadFile = File(..., description="STEP file (.stp, .step)"),
    material: str = Form(..., description="Material group code (e.g., 'OCEL-AUTO', 'HLINIK')"),
    stock_type: str = Form("bbox", description="Stock type: 'bbox' or 'cylinder'"),
    db: Session = Depends(get_db)
) -> MachiningTimeEstimateResponse:
    """
    Estimate machining time from STEP file.

    100% deterministic physics-based calculation:
    - Roughing time = (stock_volume - part_volume) / MRR
    - Finishing time = surface_area / finishing_rate
    - Setup time = base_time + size_factor
    - Constraint penalties applied (deep pockets, thin walls)

    Params:
    - step_file: STEP file (.stp, .step)
    - material: Material group code (e.g., "OCEL-AUTO" for free-cutting steel, "HLINIK" for aluminum)
    - stock_type: "bbox" (rectangular) or "cylinder" (turned parts)

    Returns:
    - Time estimate with detailed breakdown

    Raises:
    - 400: Invalid material code or stock type
    - 422: Invalid STEP file
    - 500: OCCT not available or internal error
    """
    # Validate file extension
    filename = step_file.filename or ""
    if not filename.lower().endswith((".stp", ".step")):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid file type. Only STEP files (.stp, .step) are supported."
        )

    # Validate material code exists in database
    material_group = db.query(MaterialGroup).filter(MaterialGroup.code == material).first()
    if not material_group:
        # Get list of available materials
        available_materials = db.query(MaterialGroup.code).filter(
            MaterialGroup.mrr_milling_roughing.isnot(None)
        ).all()
        available = ", ".join([m.code for m in available_materials])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown material code: {material}. Available: {available}"
        )

    if not material_group.mrr_milling_roughing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Material '{material}' has no cutting parameters. Run seed script first."
        )

    # Validate stock type
    if stock_type not in ("bbox", "cylinder"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid stock_type: {stock_type}. Must be 'bbox' or 'cylinder'."
        )

    # Save uploaded file temporarily
    temp_dir = Path("uploads/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / filename

    try:
        # Write uploaded file
        content = await step_file.read()
        temp_path.write_bytes(content)

        # Estimate time
        result = MachiningTimeEstimationService.estimate_time(
            step_path=temp_path,
            material=material,
            stock_type=stock_type
        )

        return MachiningTimeEstimateResponse(**result)

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        logger.error(f"Runtime error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during time estimation."
        )
    finally:
        # Cleanup temp file
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp file: {cleanup_error}")


@router.get(
    "/materials",
    response_model=List[MaterialListItem],
    status_code=status.HTTP_200_OK
)
async def list_materials(db: Session = Depends(get_db)) -> List[MaterialListItem]:
    """
    List all available materials for time estimation.

    Returns list of materials with MRR data and properties from database.
    Only returns materials with cutting parameters defined.

    Returns:
    - List of materials with codes, names, and properties
    """
    # Query materials with cutting parameters
    material_groups = db.query(MaterialGroup).filter(
        MaterialGroup.mrr_milling_roughing.isnot(None)
    ).all()

    materials = []
    for mg in material_groups:
        materials.append(MaterialListItem(
            code=mg.code,
            category=mg.name,  # Use name as category for display
            iso_group=mg.iso_group or "N/A",
            hardness_hb=int(mg.hardness_hb) if mg.hardness_hb else 0,
            density=round(mg.density, 2)
        ))

    # Sort by ISO group, then name
    materials.sort(key=lambda m: (m.iso_group, m.category))

    return materials


@router.get(
    "/batch",
    response_model=List[dict],
    status_code=status.HTTP_200_OK
)
async def get_batch_results() -> List[dict]:
    """
    Get batch estimation results from latest batch processing run.

    Reads from batch_estimation_results.json (generated by CLI script).

    Returns:
    - List of estimation results for all STEP files
    """
    results_file = Path("batch_estimation_results.json")

    if not results_file.exists():
        logger.warning("Batch results file not found. Run batch script first.")
        return []

    try:
        with open(results_file, "r", encoding="utf-8") as f:
            results = json.load(f)

        logger.info(f"Loaded {len(results)} batch estimation results")
        return results

    except Exception as e:
        logger.error(f"Failed to load batch results: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load batch estimation results."
        )


@router.post(
    "/re-estimate",
    response_model=MachiningTimeEstimateResponse,
    status_code=status.HTTP_200_OK
)
async def re_estimate_machining_time(
    request: MachiningTimeReEstimateRequest,
    db: AsyncSession = Depends(get_db)
) -> MachiningTimeEstimateResponse:
    """
    Re-estimate machining time for existing STEP file with different material.

    Allows user to change material selection and recalculate time estimate
    without re-uploading the file.

    Params:
    - filename: STEP filename from uploads/drawings directory
    - material_code: Material group code (e.g., "OCEL-AUTO", "HLINIK")
    - stock_type: "bbox" (rectangular) or "cylinder" (turned parts)

    Returns:
    - Time estimate with detailed breakdown

    Raises:
    - 400: Invalid material code or stock type
    - 404: STEP file not found
    - 500: OCCT not available or internal error
    """
    # Validate material code exists in database (async query)
    stmt = select(MaterialGroup).filter(MaterialGroup.code == request.material_code)
    result = await db.execute(stmt)
    material_group = result.scalar_one_or_none()

    if not material_group:
        # Get list of available materials
        stmt_available = select(MaterialGroup.code).filter(
            MaterialGroup.mrr_milling_roughing.isnot(None)
        )
        result_available = await db.execute(stmt_available)
        available_materials = result_available.scalars().all()
        available = ", ".join(available_materials)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown material code: {request.material_code}. Available: {available}"
        )

    if not material_group.mrr_milling_roughing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Material '{request.material_code}' has no cutting parameters. Run seed script first."
        )

    # Validate stock type
    if request.stock_type not in ("bbox", "cylinder"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid stock_type: {request.stock_type}. Must be 'bbox' or 'cylinder'."
        )

    # Find STEP file in uploads/drawings
    drawings_dir = Path("uploads/drawings")
    step_file = None

    # Search for file (case-insensitive)
    for pattern in ["**/*.step", "**/*.stp"]:
        for candidate in drawings_dir.glob(pattern):
            if candidate.name.lower() == request.filename.lower():
                step_file = candidate
                break
        if step_file:
            break

    if not step_file or not step_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"STEP file not found: {request.filename}"
        )

    # Estimate time with new material
    try:
        result = MachiningTimeEstimationService.estimate_time(
            step_path=step_file,
            material=request.material_code,
            stock_type=request.stock_type
        )

        return MachiningTimeEstimateResponse(**result)

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        logger.error(f"Runtime error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during time estimation."
        )


@router.get(
    "/drawing-pdf/{step_filename}",
    status_code=status.HTTP_200_OK
)
async def get_drawing_pdf(step_filename: str):
    """
    Get PDF drawing for a STEP file.

    Searches for corresponding PDF file in uploads/drawings directory.
    Matches are fuzzy - strips extensions and compares base names case-insensitively.

    Args:
        step_filename: STEP filename (e.g., "JR 808404.ipt.step")

    Returns:
        PDF file as FileResponse

    Raises:
        404: PDF not found
    """
    drawings_dir = Path("uploads/drawings")

    # Extract part number from STEP filename (first part before underscore or space)
    step_lower = step_filename.lower()

    # Try to extract part number - split by common delimiters
    step_parts = step_lower.replace('.step', '').replace('.stp', '').replace('_', ' ').replace('-', ' ').split()
    if not step_parts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cannot parse filename: {step_filename}"
        )

    # First part is usually the part number
    part_number = step_parts[0]

    logger.info(f"Searching PDF for part number: {part_number} (from {step_filename})")

    # Search for matching PDF
    for pdf_file in drawings_dir.glob("*.pdf"):
        pdf_lower = pdf_file.name.lower()

        # Check if PDF filename starts with the same part number
        if pdf_lower.startswith(part_number):
            logger.info(f"✓ Found PDF match: {step_filename} → {pdf_file.name}")

            # Read PDF file content
            pdf_content = pdf_file.read_bytes()

            # Return as Response with inline disposition
            return Response(
                content=pdf_content,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": "inline"
                }
            )

    # Not found
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"PDF drawing not found for: {step_filename}"
    )
