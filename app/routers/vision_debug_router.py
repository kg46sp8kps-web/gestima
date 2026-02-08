"""
Vision Debug Router — Endpoints for Vision Hybrid Pipeline testing.

Provides debug endpoints to test STEP → PDF annotation → Vision extraction workflow.

ADR-TBD: Vision Hybrid Pipeline
"""

import logging
import uuid
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.part import Part
from app.models.drawing import Drawing
from app.schemas.vision_hybrid import (
    AvailablePartResponse,
    VisionRefinementRequest,
    RefinementStatus
)
from app.services.occt_waterline_extractor import WaterlineExtractor
from app.services.pdf_step_annotator import PdfStepAnnotator
from app.services.vision_feature_extractor import VisionFeatureExtractor
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vision-debug", tags=["Vision Debug"])

# Background job storage (in-memory for POC, use Redis for production)
_active_jobs: Dict[str, Dict] = {}


# ============================================================================
# FILE-BASED MODE (no database required)
# ============================================================================

def extract_base_name(filename: str) -> str:
    """
    Extract base part number from filename.

    Reused from import_all_drawings.py for consistency.
    """
    name = filename
    for ext in ['.ipt.step', '.idw_Gelso.pdf', '_Gelso.pdf', '.idw', '.step', '.stp', '.pdf', '_Gelso']:
        name = name.replace(ext, '')
    return name.strip()


@router.get("/drawing-files")
async def list_drawing_files():
    """
    List all PDF + STEP pairs from uploads/drawings/.

    NO database required — direct filesystem scan.
    Returns only complete pairs (both PDF and STEP present).
    """
    try:
        drawings_dir = Path("uploads/drawings")

        if not drawings_dir.exists():
            return []

        pairs = {}

        for file_path in drawings_dir.iterdir():
            if not file_path.is_file():
                continue

            base_name = extract_base_name(file_path.name)

            if base_name not in pairs:
                pairs[base_name] = {"pdf": None, "step": None, "base_name": base_name}

            if file_path.suffix.lower() == ".pdf":
                pairs[base_name]["pdf"] = file_path.name
            elif file_path.suffix.lower() in [".step", ".stp"]:
                pairs[base_name]["step"] = file_path.name

        # Return only complete pairs
        complete_pairs = [
            {
                "baseName": files["base_name"],
                "pdfFile": files["pdf"],
                "stepFile": files["step"]
            }
            for files in pairs.values()
            if files["pdf"] and files["step"]
        ]

        logger.info(f"Found {len(complete_pairs)} drawing pairs in {drawings_dir}")
        return complete_pairs

    except Exception as e:
        logger.error(f"Failed to scan drawings directory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scan drawings: {str(e)}"
        )


@router.post("/refine-annotations-files")
async def refine_annotations_from_files(
    pdf_filename: str,
    step_filename: str
):
    """
    Start refinement using direct file paths (NO database).

    Args:
        pdf_filename: Filename in uploads/drawings/ (e.g., "JR 810663.idw_Gelso.pdf")
        step_filename: Filename in uploads/drawings/ (e.g., "JR 810663.ipt.step")

    Returns:
        {"job_id": "uuid", "base_name": "JR 810663"}
    """
    try:
        drawings_dir = Path("uploads/drawings")
        pdf_path = drawings_dir / pdf_filename
        step_path = drawings_dir / step_filename

        # Validate files exist
        if not pdf_path.exists():
            raise HTTPException(404, f"PDF file not found: {pdf_filename}")
        if not step_path.exists():
            raise HTTPException(404, f"STEP file not found: {step_filename}")

        # Extract STEP geometry
        logger.info(f"Extracting STEP geometry from {step_filename}")
        waterline_extractor = WaterlineExtractor()
        step_geometry = waterline_extractor.extract_waterline(step_path)

        # Add file metadata
        step_geometry["filename"] = step_filename
        step_geometry["pdf_filename"] = pdf_filename

        # Start refinement job
        job_id = str(uuid.uuid4())
        base_name = extract_base_name(pdf_filename)

        logger.info(f"Starting refinement job {job_id} for {base_name}")

        # Initialize job status
        _active_jobs[job_id] = {
            "status": "starting",
            "base_name": base_name,
            "pdf_filename": pdf_filename,
            "step_filename": step_filename,
            "iteration": 0,
            "error": 1.0,
            "converged": False
        }

        # Start background refinement task
        asyncio.create_task(
            _run_refinement_job_files(job_id, pdf_path, step_geometry)
        )

        return {
            "job_id": job_id,
            "base_name": base_name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start refinement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start refinement: {str(e)}"
        )


async def _run_refinement_job_files(job_id: str, pdf_path: Path, step_geometry: dict):
    """
    Background task for Vision API feature extraction.

    CORRECTED WORKFLOW:
    1. Original PDF + STEP segments → Claude Vision API
    2. Claude extracts features (what to machine, dimensions, contour)
    3. Create annotated PDF for validation (internal debugging)
    4. Return features JSON for machining time calculation

    Updates _active_jobs dict with progress.
    """
    import shutil

    try:
        # STEP 1: Call Vision API with ORIGINAL PDF + STEP data
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not configured in .env")

        logger.info(f"[{job_id}] Sending PDF + STEP segments to Vision API")

        extractor = VisionFeatureExtractor(api_key=settings.ANTHROPIC_API_KEY)

        # Single-pass Vision API call (Claude sees original PDF + STEP data)
        vision_result = await extractor.extract_features(
            pdf_path,
            step_geometry
        )

        if not vision_result:
            raise ValueError("Vision API contour extraction failed")

        contour = vision_result.get("contour", [])
        confidence = vision_result.get("confidence", 0)
        logger.info(f"[{job_id}] Vision API extracted contour: {len(contour)} points, confidence={confidence:.2f}")

        # STEP 2: Export SVG contour
        from app.services.svg_contour_exporter import export_contour_to_svg

        svg_dir = Path("uploads/contours")
        svg_dir.mkdir(parents=True, exist_ok=True)
        svg_filename = f"{pdf_path.stem}_contour.svg"
        svg_path = svg_dir / svg_filename

        export_contour_to_svg(contour, step_geometry, svg_path)
        logger.info(f"[{job_id}] SVG exported: {svg_path}")

        # STEP 3: Create annotated PDF with contour line
        logger.info(f"[{job_id}] Creating annotated PDF with contour")
        from app.services.pdf_contour_annotator import annotate_pdf_with_contour

        annotated_pdf_url = None
        try:
            annotated_pdf_path = annotate_pdf_with_contour(pdf_path, contour, step_geometry)

            if annotated_pdf_path and annotated_pdf_path.exists():
                temp_dir = Path("uploads/temp")
                temp_dir.mkdir(parents=True, exist_ok=True)
                public_pdf_path = temp_dir / annotated_pdf_path.name
                shutil.copy(annotated_pdf_path, public_pdf_path)
                annotated_pdf_url = f"/uploads/temp/{public_pdf_path.name}"
                logger.info(f"[{job_id}] Annotated PDF saved: {public_pdf_path}")
        except Exception as e:
            logger.warning(f"[{job_id}] PDF annotation failed: {e}")

        # Update job with final results
        _active_jobs[job_id] = {
            **_active_jobs[job_id],
            "status": "completed",
            "contour": contour,
            "confidence": confidence,
            "svg_url": f"/uploads/contours/{svg_filename}",
            "annotated_pdf_url": annotated_pdf_url,
            "vision_complete": True
        }

        logger.info(f"[{job_id}] Vision workflow completed: {len(contour)} contour points")

    except Exception as e:
        logger.error(f"[{job_id}] Vision workflow failed: {e}", exc_info=True)
        _active_jobs[job_id]["status"] = "failed"
        _active_jobs[job_id]["error_message"] = str(e)


# ============================================================================
# DATABASE-BASED MODE (legacy — keep for existing UI)
# ============================================================================

@router.get("/available-parts", response_model=List[AvailablePartResponse])
async def get_available_parts(db: AsyncSession = Depends(get_db)):
    """
    Get parts with BOTH PDF and STEP drawings.

    Returns list of parts suitable for Vision Hybrid testing.
    """
    try:
        # Query parts with both PDF and STEP drawings
        # Subquery for PDF drawings
        pdf_subquery = (
            select(Drawing.part_id)
            .where(
                and_(
                    Drawing.file_type == "pdf",
                    Drawing.deleted_at.is_(None)
                )
            )
            .subquery()
        )

        # Subquery for STEP drawings
        step_subquery = (
            select(Drawing.part_id)
            .where(
                and_(
                    Drawing.file_type == "step",
                    Drawing.deleted_at.is_(None)
                )
            )
            .subquery()
        )

        # Query parts with both
        stmt = (
            select(Part)
            .where(
                and_(
                    Part.id.in_(select(pdf_subquery)),
                    Part.id.in_(select(step_subquery)),
                    Part.deleted_at.is_(None)
                )
            )
            .limit(50)
        )
        result = await db.execute(stmt)
        parts = result.scalars().all()

        # Build response
        result_list = []
        for part in parts:
            # Get PDF and STEP drawings
            pdf_stmt = (
                select(Drawing)
                .where(
                    and_(
                        Drawing.part_id == part.id,
                        Drawing.file_type == "pdf",
                        Drawing.deleted_at.is_(None)
                    )
                )
            )
            pdf_result = await db.execute(pdf_stmt)
            pdf_drawing = pdf_result.scalars().first()

            step_stmt = (
                select(Drawing)
                .where(
                    and_(
                        Drawing.part_id == part.id,
                        Drawing.file_type == "step",
                        Drawing.deleted_at.is_(None)
                    )
                )
            )
            step_result = await db.execute(step_stmt)
            step_drawing = step_result.scalars().first()

            if pdf_drawing and step_drawing:
                result_list.append(
                    AvailablePartResponse(
                        part_id=part.id,
                        part_number=part.part_number,
                        name=part.name,
                        pdf_drawing_id=pdf_drawing.id,
                        pdf_filename=pdf_drawing.filename,
                        step_drawing_id=step_drawing.id,
                        step_filename=step_drawing.filename,
                    )
                )

        logger.info(f"Found {len(result_list)} parts with both PDF and STEP drawings")
        return result_list

    except Exception as e:
        logger.error(f"Failed to query available parts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query parts: {str(e)}"
        )


@router.post("/refine-annotations")
async def start_refinement_job(
    request: VisionRefinementRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Start Vision refinement job (background task).

    Returns job_id for progress monitoring.
    """
    try:
        # Validate part exists
        part_stmt = select(Part).where(Part.id == request.part_id)
        part_result = await db.execute(part_stmt)
        part = part_result.scalars().first()

        if not part:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Part {request.part_id} not found"
            )

        # Get PDF and STEP drawings
        pdf_stmt = (
            select(Drawing)
            .where(
                and_(
                    Drawing.part_id == request.part_id,
                    Drawing.file_type == "pdf",
                    Drawing.deleted_at.is_(None)
                )
            )
        )
        pdf_result = await db.execute(pdf_stmt)
        pdf_drawing = pdf_result.scalars().first()

        step_stmt = (
            select(Drawing)
            .where(
                and_(
                    Drawing.part_id == request.part_id,
                    Drawing.file_type == "step",
                    Drawing.deleted_at.is_(None)
                )
            )
        )
        step_result = await db.execute(step_stmt)
        step_drawing = step_result.scalars().first()

        if not pdf_drawing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No PDF drawing found for part {request.part_id}"
            )

        if not step_drawing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No STEP drawing found for part {request.part_id}"
            )

        # Create job ID
        job_id = str(uuid.uuid4())

        # Store job metadata
        _active_jobs[job_id] = {
            'status': 'starting',
            'part_id': request.part_id,
            'pdf_path': pdf_drawing.file_path,
            'step_path': step_drawing.file_path,
            'max_iterations': request.max_iterations,
            'convergence_threshold': request.convergence_threshold,
        }

        logger.info(f"Created refinement job {job_id} for part {request.part_id}")

        return {
            'job_id': job_id,
            'status': 'created',
            'message': f'Refinement job created for part {request.part_id}'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start refinement job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start job: {str(e)}"
        )


@router.get("/progress/{job_id}")
async def stream_refinement_progress(job_id: str):
    """
    SSE stream of refinement progress.

    Polls _active_jobs dict and streams updates (file-based workflow).
    Background task (_run_refinement_job_files) updates the job status.
    """
    if job_id not in _active_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    async def event_generator():
        """Poll job status and stream updates."""
        last_iteration = -1

        while True:
            if job_id not in _active_jobs:
                yield f"data: {json.dumps({'error': 'Job disappeared'})}\n\n"
                break

            job = _active_jobs[job_id]
            status_val = job.get('status', 'unknown')

            # Stream update if iteration changed
            iteration = job.get('iteration', 0)
            if iteration > last_iteration:
                update = {
                    'iteration': iteration,
                    'error': job.get('error', 1.0),
                    'converged': job.get('converged', False),
                    'features': job.get('features', []),
                    'annotated_pdf_url': job.get('annotated_pdf_url', '')
                }
                yield f"data: {json.dumps(update)}\n\n"
                last_iteration = iteration

            # Check for completion
            if status_val == 'completed':
                yield f"data: {json.dumps({'status': 'completed', 'converged': True})}\n\n"
                break
            elif status_val == 'failed':
                error_msg = job.get('error_message', 'Unknown error')
                yield f"data: {json.dumps({'status': 'failed', 'error_message': error_msg})}\n\n"
                break

            # Poll every 500ms
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/job-status/{job_id}")
async def get_job_status(job_id: str):
    """Get current job status (non-streaming)."""
    if job_id not in _active_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    job = _active_jobs[job_id]

    return {
        'job_id': job_id,
        'status': job['status'],
        'part_id': job['part_id'],
    }
