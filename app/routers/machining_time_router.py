"""GESTIMA - Machining Time Estimation API Router

Physics-based machining time estimation endpoints.
ADR-040: Machining Time Estimation System
"""

import logging
import json
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status

from app.schemas.machining_time import (
    MachiningTimeEstimateResponse,
    MaterialListItem,
)
from app.services.machining_time_estimation_service import MachiningTimeEstimationService
from app.config.material_database import MATERIAL_DB, list_available_materials

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/estimate",
    response_model=MachiningTimeEstimateResponse,
    status_code=status.HTTP_200_OK
)
async def estimate_machining_time(
    step_file: UploadFile = File(..., description="STEP file (.stp, .step)"),
    material: str = Form(..., description="Material code (8-digit, e.g., '20910005')"),
    stock_type: str = Form("bbox", description="Stock type: 'bbox' or 'cylinder'")
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
    - material: 8-digit material code (e.g., "20910005" for alloy steel)
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

    # Validate material code
    if len(material) != 8 or not material.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid material code: {material}. Must be 8 digits (e.g., '20910005')."
        )

    if material not in MATERIAL_DB:
        available = ", ".join(list_available_materials())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown material code: {material}. Available: {available}"
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
async def list_materials() -> List[MaterialListItem]:
    """
    List all available materials for time estimation.

    Returns list of materials with MRR data and properties.

    Returns:
    - List of materials with codes, categories, and properties
    """
    materials = []
    for code, data in MATERIAL_DB.items():
        materials.append(MaterialListItem(
            code=code,
            category=data["category"],
            iso_group=data["iso_group"],
            hardness_hb=int(data["hardness_hb"]),
            density=round(data["density"], 2)
        ))

    # Sort by ISO group, then category
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
