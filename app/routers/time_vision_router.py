"""TimeVision - API router for AI machining time estimation"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.models.time_vision import (
    TimeVisionEstimation,
    TimeVisionResponse,
    TimeVisionListItem,
    TimeVisionActualTimeUpdate,
)
from app.models.file_record import FileRecord
from app.services.openai_vision_service import estimate_from_pdf_openai, extract_features_from_pdf_openai, is_fine_tuned_model, OPENAI_MODEL
from app.services.feature_calculator import calculate_features_time
from app.dependencies import get_current_user, require_role
from app.models import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/time-vision", tags=["TimeVision"])

DRAWINGS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "drawings"


def _resolve_pdf_path(record_pdf_path: str, filename: str) -> Path:
    """Resolve PDF path — handles both absolute and legacy relative paths in DB."""
    path = Path(record_pdf_path)
    if path.is_absolute() and path.exists():
        return path
    # Legacy relative path ("uploads/drawings/file.pdf") — resolve via DRAWINGS_DIR
    resolved = DRAWINGS_DIR / filename
    if resolved.exists():
        return resolved
    return path  # Return as-is, caller will handle missing file


@router.get("/model-info")
async def get_model_info():
    """Return currently configured OpenAI model info."""
    return {
        "model": OPENAI_MODEL,
        "is_fine_tuned": is_fine_tuned_model(),
        "provider": "openai_ft" if is_fine_tuned_model() else "openai",
    }




# get_db imported from app.database (canonical, shared across all routers)


class DrawingEstimationInfo(BaseModel):
    """Estimation info for one model version (v1 or v2)."""
    estimation_id: Optional[int] = Field(default=None)
    status: Optional[str] = Field(default=None)
    ai_provider: Optional[str] = Field(default=None)
    ai_model: Optional[str] = Field(default=None)


class DrawingFileInfo(BaseModel):
    """Info about a drawing file in uploads/drawings"""
    filename: str = Field(min_length=1, max_length=500)
    size_bytes: int = Field(ge=0)
    has_estimation: bool = Field(default=False)
    # ADR-044 Phase 2: FileManager integration
    file_id: Optional[int] = Field(default=None)
    # Legacy fields (for backwards compatibility)
    estimation_id: Optional[int] = Field(default=None)
    status: Optional[str] = Field(default=None)
    has_openai_estimation: bool = Field(default=False)
    ai_provider: Optional[str] = Field(default=None)
    ai_model: Optional[str] = Field(default=None)
    # Per-model estimation info
    v1: Optional[DrawingEstimationInfo] = Field(default=None)
    v2: Optional[DrawingEstimationInfo] = Field(default=None)


class CalibrationUpdate(BaseModel):
    """Update estimation fields for calibration."""
    part_type: Optional[str] = Field(None, pattern="^(ROT|PRI|COMBINED)$")
    complexity: Optional[str] = Field(None, pattern="^(simple|medium|complex)$")
    actual_time_min: Optional[float] = Field(None, gt=0, lt=10000)
    actual_notes: Optional[str] = Field(None, max_length=2000)
    human_estimate_min: Optional[float] = Field(None, gt=0, lt=10000)
    version: int = Field(ge=0)


@router.get("/drawings", response_model=List[DrawingFileInfo])
async def list_drawings(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List PDF files in uploads/drawings directory."""
    if not DRAWINGS_DIR.exists():
        return []

    pdf_files = sorted(DRAWINGS_DIR.glob("*.pdf"), key=lambda p: p.name)

    # Query newest estimation per (filename, estimation_type) — V1 and V2 independent
    try:
        from sqlalchemy import func
        newest_ids = (
            select(
                func.max(TimeVisionEstimation.id).label("max_id"),
            )
            .where(TimeVisionEstimation.deleted_at.is_(None))
            .group_by(
                TimeVisionEstimation.pdf_filename,
                TimeVisionEstimation.estimation_type,
            )
            .subquery()
        )
        stmt = (
            select(
                TimeVisionEstimation.pdf_filename,
                TimeVisionEstimation.id,
                TimeVisionEstimation.status,
                TimeVisionEstimation.ai_provider,
                TimeVisionEstimation.ai_model,
                TimeVisionEstimation.estimation_type,
            )
            .where(
                TimeVisionEstimation.deleted_at.is_(None),
                TimeVisionEstimation.id.in_(select(newest_ids.c.max_id)),
            )
        )
        result = await db.execute(stmt)
        # Map: filename → {estimation_type: (id, status, provider, model)}
        estimation_map: dict = {}
        for row in result.all():
            fname, eid, status, provider, model, etype = row
            estimation_map.setdefault(fname, {})[etype] = (eid, status, provider, model)
    except Exception as exc:
        logger.warning("Failed to query estimations: %s", exc)
        estimation_map = {}

    # Query existing FileRecords for drawings directory
    file_record_map: dict[str, int] = {}
    try:
        fr_stmt = (
            select(FileRecord.original_filename, FileRecord.id)
            .where(
                FileRecord.deleted_at.is_(None),
                FileRecord.file_type == "pdf",
                FileRecord.status == "active",
            )
        )
        fr_result = await db.execute(fr_stmt)
        for row in fr_result.all():
            file_record_map[row[0]] = row[1]
    except Exception as exc:
        logger.warning("Failed to query file records: %s", exc)

    files = []
    for pdf_path in pdf_files:
        per_type = estimation_map.get(pdf_path.name, {})
        v1_info = per_type.get("time_v1")
        v2_info = per_type.get("features_v2")

        # Legacy fields: prefer V1, fall back to V2
        primary = v1_info or v2_info
        files.append(DrawingFileInfo(
            filename=pdf_path.name,
            size_bytes=pdf_path.stat().st_size,
            has_estimation=primary is not None,
            file_id=file_record_map.get(pdf_path.name),
            estimation_id=primary[0] if primary else None,
            status=primary[1] if primary else None,
            has_openai_estimation=v1_info is not None,
            ai_provider=primary[2] if primary else None,
            ai_model=primary[3] if primary else None,
            v1=DrawingEstimationInfo(
                estimation_id=v1_info[0], status=v1_info[1],
                ai_provider=v1_info[2], ai_model=v1_info[3],
            ) if v1_info else None,
            v2=DrawingEstimationInfo(
                estimation_id=v2_info[0], status=v2_info[1],
                ai_provider=v2_info[2], ai_model=v2_info[3],
            ) if v2_info else None,
        ))

    return files


@router.get("/drawings/{filename}/pdf")
async def serve_drawing_pdf(filename: str):
    """Serve a PDF drawing file for preview."""
    # Security: prevent path traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    pdf_path = DRAWINGS_DIR / filename
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"Drawing not found: {filename}")
    if not pdf_path.suffix.lower() == '.pdf':
        raise HTTPException(status_code=400, detail="Only PDF files supported")

    return FileResponse(
        str(pdf_path),
        media_type="application/pdf",
        content_disposition_type="inline",
    )


class ProcessRequest(BaseModel):
    """Request to process a PDF drawing."""
    filename: str = Field(default="", max_length=500)
    file_id: Optional[int] = Field(default=None, description="FileRecord ID (preferred over filename)")
    part_id: Optional[int] = Field(default=None, description="Part ID for direct Part↔TimeVision FK (ADR-045)")


@router.get("/estimations", response_model=List[TimeVisionListItem])
async def list_estimations(
    status: Optional[str] = Query(None),
    estimation_type: Optional[str] = Query(None),
    filename: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all estimations."""
    try:
        stmt = (
            select(TimeVisionEstimation)
            .where(TimeVisionEstimation.deleted_at.is_(None))
            .order_by(TimeVisionEstimation.created_at.desc())
        )
        if status:
            stmt = stmt.where(TimeVisionEstimation.status == status)
        if estimation_type:
            stmt = stmt.where(TimeVisionEstimation.estimation_type == estimation_type)
        if filename:
            stmt = stmt.where(TimeVisionEstimation.pdf_filename == filename)

        result = await db.execute(stmt)
        records = result.scalars().all()
        return [TimeVisionListItem.model_validate(r) for r in records]
    except Exception as exc:
        logger.error("Failed to list estimations: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list estimations")


@router.get("/estimations/by-part/{part_id}", response_model=List[TimeVisionListItem])
async def get_estimations_by_part(
    part_id: int,
    estimation_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all estimations for a specific Part (ADR-045)."""
    try:
        stmt = (
            select(TimeVisionEstimation)
            .where(
                TimeVisionEstimation.part_id == part_id,
                TimeVisionEstimation.deleted_at.is_(None),
            )
            .order_by(TimeVisionEstimation.created_at.desc())
        )
        if estimation_type:
            stmt = stmt.where(TimeVisionEstimation.estimation_type == estimation_type)

        result = await db.execute(stmt)
        records = result.scalars().all()
        return [TimeVisionListItem.model_validate(r) for r in records]
    except Exception as exc:
        logger.error("Failed to get estimations for part %d: %s", part_id, exc)
        raise HTTPException(status_code=500, detail="Failed to get estimations")


@router.get("/estimations/{estimation_id}", response_model=TimeVisionResponse)
async def get_estimation(
    estimation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full estimation detail."""
    try:
        stmt = select(TimeVisionEstimation).where(
            TimeVisionEstimation.id == estimation_id,
            TimeVisionEstimation.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
    except Exception as exc:
        logger.error("Failed to get estimation %d: %s", estimation_id, exc)
        raise HTTPException(status_code=500, detail="Failed to get estimation")

    if not record:
        raise HTTPException(status_code=404, detail="Estimation not found")

    return TimeVisionResponse.model_validate(record)


@router.put("/estimations/{estimation_id}/actual-time", response_model=TimeVisionResponse)
async def update_actual_time(
    estimation_id: int,
    data: TimeVisionActualTimeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enter actual production time after manufacturing (real shop floor time)."""
    try:
        stmt = select(TimeVisionEstimation).where(
            TimeVisionEstimation.id == estimation_id,
            TimeVisionEstimation.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
    except Exception as exc:
        logger.error("Failed to find estimation %d: %s", estimation_id, exc)
        raise HTTPException(status_code=500, detail="Database error")

    if not record:
        raise HTTPException(status_code=404, detail="Estimation not found")

    # Optimistic locking
    if record.version != data.version:
        raise HTTPException(status_code=409, detail="Data modified by another user")

    record.actual_time_min = data.actual_time_min
    record.actual_notes = data.actual_notes
    record.actual_entered_at = datetime.utcnow()
    record.status = "verified"

    try:
        await db.commit()
        await db.refresh(record)
        return TimeVisionResponse.model_validate(record)
    except Exception as exc:
        await db.rollback()
        logger.error("Failed to update actual time for %d: %s", estimation_id, exc)
        raise HTTPException(status_code=500, detail="Failed to update")


@router.put("/estimations/{estimation_id}/calibrate", response_model=TimeVisionResponse)
async def calibrate_estimation(
    estimation_id: int,
    data: CalibrationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """Update complexity and/or actual time for calibration."""
    try:
        stmt = select(TimeVisionEstimation).where(
            TimeVisionEstimation.id == estimation_id,
            TimeVisionEstimation.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
    except Exception as exc:
        logger.error("Failed to find estimation %d: %s", estimation_id, exc)
        raise HTTPException(status_code=500, detail="Database error")

    if not record:
        raise HTTPException(status_code=404, detail="Estimation not found")

    # Optimistic locking
    if record.version != data.version:
        raise HTTPException(status_code=409, detail="Data modified by another user")

    # Update part_type if provided
    if data.part_type is not None:
        record.part_type = data.part_type

    # Update complexity if provided
    if data.complexity is not None:
        record.complexity = data.complexity

    # Update human estimate if provided (user's estimate before manufacturing)
    if data.human_estimate_min is not None:
        record.human_estimate_min = data.human_estimate_min
        # Only upgrade status if not already verified by production time
        if record.status != "verified":
            record.status = "calibrated"

    # Update actual production time if provided (real manufacturing time)
    if data.actual_time_min is not None:
        record.actual_time_min = data.actual_time_min
        record.actual_entered_at = datetime.utcnow()
        record.status = "verified"

    # Update notes if provided
    if data.actual_notes is not None:
        record.actual_notes = data.actual_notes

    try:
        await db.commit()
        await db.refresh(record)
        return TimeVisionResponse.model_validate(record)
    except Exception as exc:
        await db.rollback()
        logger.error("Failed to calibrate estimation %d: %s", estimation_id, exc)
        raise HTTPException(status_code=500, detail="Failed to update")


@router.get("/batch-test-results")
async def get_batch_test_results(current_user: User = Depends(get_current_user)):
    """Serve batch test results from data/batch_test_results.json."""
    results_path = Path("data/batch_test_results.json")
    if not results_path.exists():
        raise HTTPException(
            status_code=404,
            detail="No batch test results. Run: python scripts/batch_opus_test.py",
        )

    try:
        data = json.loads(results_path.read_text(encoding="utf-8"))
        return data
    except Exception as exc:
        logger.error("Failed to read batch results: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to read batch results")


@router.delete("/estimations/{estimation_id}")
async def delete_estimation(
    estimation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft delete an estimation."""
    try:
        stmt = select(TimeVisionEstimation).where(
            TimeVisionEstimation.id == estimation_id,
            TimeVisionEstimation.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
    except Exception as exc:
        logger.error("Failed to find estimation %d: %s", estimation_id, exc)
        raise HTTPException(status_code=500, detail="Database error")

    if not record:
        raise HTTPException(status_code=404, detail="Estimation not found")

    record.deleted_at = datetime.utcnow()

    try:
        await db.commit()
        return {"detail": "Estimation deleted"}
    except Exception as exc:
        await db.rollback()
        logger.error("Failed to delete estimation %d: %s", estimation_id, exc)
        raise HTTPException(status_code=500, detail="Failed to delete")


@router.post("/process-openai")
async def process_drawing_openai(
    request: ProcessRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Process a drawing using OpenAI GPT-4o vision (single-call estimation).

    SSE stream with 2 steps:
      1. OpenAI vision estimation
      2. Save to database
    """
    # Resolve file path - prefer file_id, fallback to filename
    pdf_path = None
    file_record_id = request.file_id
    filename = request.filename

    if request.file_id:
        # ADR-044: resolve via FileRecord
        fr_result = await db.execute(
            select(FileRecord).where(
                FileRecord.id == request.file_id,
                FileRecord.deleted_at.is_(None),
            )
        )
        fr = fr_result.scalar_one_or_none()
        if not fr:
            raise HTTPException(status_code=404, detail=f"FileRecord not found: {request.file_id}")
        # Resolve physical path
        uploads_dir = Path(__file__).resolve().parent.parent.parent / "uploads"
        pdf_path = uploads_dir / fr.file_path
        if not pdf_path.exists():
            pdf_path = DRAWINGS_DIR / fr.original_filename
        filename = fr.original_filename
        file_record_id = fr.id
    else:
        # Legacy: filename-based resolution
        if not filename:
            raise HTTPException(status_code=400, detail="Either filename or file_id is required")
        if ".." in filename or "/" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        pdf_path = DRAWINGS_DIR / filename

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            # Step 1: OpenAI Vision estimation
            yield {"event": "step", "data": json.dumps({"step": 1, "total": 2, "label": "OpenAI GPT-4o vision odhad..."})}

            raw_result = await estimate_from_pdf_openai(
                pdf_path=str(pdf_path),
                similar_parts=None,  # TODO: add similar parts lookup later
            )

            # Step 2: Save to database
            yield {"event": "step", "data": json.dumps({"step": 2, "total": 2, "label": "Ukládám do databáze..."})}

            # Build breakdown JSON
            breakdown = raw_result.get("breakdown", [])
            breakdown_json = json.dumps(breakdown, ensure_ascii=False) if breakdown else None

            # Build operations JSON
            operations = raw_result.get("operations", [])
            operations_json = json.dumps(operations, ensure_ascii=False) if operations else None

            # UPSERT: prefer part_id > file_id > filename match (ADR-045)
            if request.part_id:
                existing_result = await db.execute(
                    select(TimeVisionEstimation)
                    .where(
                        TimeVisionEstimation.part_id == request.part_id,
                        TimeVisionEstimation.estimation_type == "time_v1",
                        TimeVisionEstimation.deleted_at.is_(None),
                    )
                    .order_by(TimeVisionEstimation.id.desc())
                    .limit(1)
                )
            elif file_record_id:
                existing_result = await db.execute(
                    select(TimeVisionEstimation)
                    .where(
                        TimeVisionEstimation.file_id == file_record_id,
                        TimeVisionEstimation.estimation_type == "time_v1",
                        TimeVisionEstimation.deleted_at.is_(None),
                    )
                    .order_by(TimeVisionEstimation.id.desc())
                    .limit(1)
                )
            else:
                existing_result = await db.execute(
                    select(TimeVisionEstimation)
                    .where(
                        TimeVisionEstimation.pdf_filename == filename,
                        TimeVisionEstimation.estimation_type == "time_v1",
                        TimeVisionEstimation.deleted_at.is_(None),
                    )
                    .order_by(TimeVisionEstimation.id.desc())
                    .limit(1)
                )
            record = existing_result.scalar_one_or_none()

            ai_data = {
                "pdf_path": str(pdf_path),
                "file_id": file_record_id,
                "part_id": request.part_id,
                "estimation_type": "time_v1",
                "ai_provider": "openai_ft" if is_fine_tuned_model() else "openai",
                "ai_model": OPENAI_MODEL,
                "part_type": raw_result.get("part_type"),
                "complexity": raw_result.get("complexity"),
                "material_detected": raw_result.get("material_detected"),
                "material_coefficient": 1.0,
                "max_diameter_mm": raw_result.get("max_diameter_mm"),
                "max_length_mm": raw_result.get("max_length_mm"),
                "max_width_mm": raw_result.get("max_width_mm"),
                "max_height_mm": raw_result.get("max_height_mm"),
                "manufacturing_description": raw_result.get("manufacturing_description"),
                "part_number_detected": raw_result.get("part_number_hint"),
                "operations_detected": operations_json,
                "vision_extraction_json": json.dumps(raw_result, ensure_ascii=False),
                "estimated_time_min": raw_result.get("estimated_time_min"),
                "estimation_reasoning": raw_result.get("reasoning"),
                "estimation_breakdown_json": breakdown_json,
                "confidence": raw_result.get("confidence"),
                "status": "estimated",
            }

            if record:
                # UPDATE existing — preserve calibration (actual_time_min, human_estimate_min)
                for key, value in ai_data.items():
                    setattr(record, key, value)
                # Restore status based on existing calibration data (don't reset to "estimated")
                if record.actual_time_min is not None:
                    record.status = "verified"
                elif record.human_estimate_min is not None:
                    record.status = "calibrated"
                # else stays "estimated" from ai_data
                record.updated_at = datetime.utcnow()
                logger.info(f"Updated existing estimation #{record.id} for {filename}")
            else:
                # INSERT new
                record = TimeVisionEstimation(pdf_filename=filename, **ai_data)
                db.add(record)
                logger.info(f"Created new estimation for {filename}")

            try:
                await db.commit()
                await db.refresh(record)
            except Exception as exc:
                await db.rollback()
                logger.error("Failed to save OpenAI estimation: %s", exc)
                yield {"event": "error", "data": json.dumps({"detail": str(exc)})}
                return

            # Return result
            result = TimeVisionResponse.model_validate(record)
            yield {"event": "result", "data": result.model_dump_json()}

        except Exception as exc:
            logger.error("OpenAI process error: %s", exc)
            yield {"event": "error", "data": json.dumps({"detail": str(exc)})}

    return EventSourceResponse(event_generator())


@router.post("/process-features")
async def process_features(
    request: ProcessRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Process a drawing for feature extraction using base GPT-4o vision.

    SSE stream with 2 steps:
      1. GPT-4o vision feature extraction
      2. Save to database
    """
    # Resolve file path - prefer file_id, fallback to filename
    pdf_path = None
    file_record_id = request.file_id
    filename = request.filename

    if request.file_id:
        # ADR-044: resolve via FileRecord
        fr_result = await db.execute(
            select(FileRecord).where(
                FileRecord.id == request.file_id,
                FileRecord.deleted_at.is_(None),
            )
        )
        fr = fr_result.scalar_one_or_none()
        if not fr:
            raise HTTPException(status_code=404, detail=f"FileRecord not found: {request.file_id}")
        # Resolve physical path
        uploads_dir = Path(__file__).resolve().parent.parent.parent / "uploads"
        pdf_path = uploads_dir / fr.file_path
        if not pdf_path.exists():
            pdf_path = DRAWINGS_DIR / fr.original_filename
        filename = fr.original_filename
        file_record_id = fr.id
    else:
        # Legacy: filename-based resolution
        if not filename:
            raise HTTPException(status_code=400, detail="Either filename or file_id is required")
        if ".." in filename or "/" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        pdf_path = DRAWINGS_DIR / filename

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            # Step 1: GPT-4o Vision feature extraction
            yield {"event": "step", "data": json.dumps({"step": 1, "total": 2, "label": "GPT-4o feature extraction..."})}

            raw_result = await extract_features_from_pdf_openai(pdf_path=str(pdf_path))

            # Step 2: Save to database
            yield {"event": "step", "data": json.dumps({"step": 2, "total": 2, "label": "Ukládám do databáze..."})}

            features_json_str = json.dumps(raw_result, ensure_ascii=False)

            # UPSERT: prefer part_id > file_id > filename match (ADR-045)
            if request.part_id:
                existing_result = await db.execute(
                    select(TimeVisionEstimation)
                    .where(
                        TimeVisionEstimation.part_id == request.part_id,
                        TimeVisionEstimation.estimation_type == "features_v2",
                        TimeVisionEstimation.deleted_at.is_(None),
                    )
                    .order_by(TimeVisionEstimation.id.desc())
                    .limit(1)
                )
            elif file_record_id:
                existing_result = await db.execute(
                    select(TimeVisionEstimation)
                    .where(
                        TimeVisionEstimation.file_id == file_record_id,
                        TimeVisionEstimation.estimation_type == "features_v2",
                        TimeVisionEstimation.deleted_at.is_(None),
                    )
                    .order_by(TimeVisionEstimation.id.desc())
                    .limit(1)
                )
            else:
                existing_result = await db.execute(
                    select(TimeVisionEstimation)
                    .where(
                        TimeVisionEstimation.pdf_filename == filename,
                        TimeVisionEstimation.estimation_type == "features_v2",
                        TimeVisionEstimation.deleted_at.is_(None),
                    )
                    .order_by(TimeVisionEstimation.id.desc())
                    .limit(1)
                )
            record = existing_result.scalar_one_or_none()

            # Extract basic fields from features result
            overall_dims = raw_result.get("overall_dimensions", {})

            features_data = {
                "pdf_path": str(pdf_path),
                "file_id": file_record_id,
                "part_id": request.part_id,
                "estimation_type": "features_v2",
                "ai_provider": "openai",
                "ai_model": "gpt-4o",
                "part_type": raw_result.get("part_type"),
                "material_detected": raw_result.get("material", {}).get("designation") if isinstance(raw_result.get("material"), dict) else None,
                "material_coefficient": 1.0,
                "max_diameter_mm": overall_dims.get("max_diameter_mm"),
                "max_length_mm": overall_dims.get("max_length_mm"),
                "max_width_mm": overall_dims.get("max_width_mm"),
                "max_height_mm": overall_dims.get("max_height_mm"),
                "manufacturing_description": raw_result.get("part_name"),
                "part_number_detected": raw_result.get("drawing_number"),
                "features_json": features_json_str,
                "vision_extraction_json": features_json_str,
                "confidence": "medium",
                "status": "estimated",
            }

            if record:
                for key, value in features_data.items():
                    setattr(record, key, value)
                # Restore status based on existing calibration data (don't reset to "estimated")
                if record.actual_time_min is not None:
                    record.status = "verified"
                elif record.human_estimate_min is not None:
                    record.status = "calibrated"
                # else stays "estimated" from features_data
                record.updated_at = datetime.utcnow()
                logger.info(f"Updated existing features estimation #{record.id} for {filename}")
            else:
                record = TimeVisionEstimation(pdf_filename=filename, **features_data)
                db.add(record)
                logger.info(f"Created new features estimation for {filename}")

            try:
                await db.commit()
                await db.refresh(record)
            except Exception as exc:
                await db.rollback()
                logger.error("Failed to save features estimation: %s", exc)
                yield {"event": "error", "data": json.dumps({"detail": str(exc)})}
                return

            result = TimeVisionResponse.model_validate(record)
            yield {"event": "result", "data": result.model_dump_json()}

        except Exception as exc:
            logger.error("Features process error: %s", exc)
            yield {"event": "error", "data": json.dumps({"detail": str(exc)})}

    return EventSourceResponse(event_generator())


class FeaturesUpdate(BaseModel):
    """Update corrected features for training data."""
    features_corrected_json: str = Field(min_length=2)
    version: int = Field(ge=0)


@router.put("/estimations/{estimation_id}/features", response_model=TimeVisionResponse)
async def save_corrected_features(
    estimation_id: int,
    data: FeaturesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save human-corrected features for fine-tuning training data."""
    try:
        stmt = select(TimeVisionEstimation).where(
            TimeVisionEstimation.id == estimation_id,
            TimeVisionEstimation.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
    except Exception as exc:
        logger.error("Failed to find estimation %d: %s", estimation_id, exc)
        raise HTTPException(status_code=500, detail="Database error")

    if not record:
        raise HTTPException(status_code=404, detail="Estimation not found")

    if record.version != data.version:
        raise HTTPException(status_code=409, detail="Data modified by another user")

    # Validate JSON
    try:
        json.loads(data.features_corrected_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in features_corrected_json")

    record.features_corrected_json = data.features_corrected_json
    record.updated_at = datetime.utcnow()

    try:
        await db.commit()
        await db.refresh(record)
        return TimeVisionResponse.model_validate(record)
    except Exception as exc:
        await db.rollback()
        logger.error("Failed to save corrected features for %d: %s", estimation_id, exc)
        raise HTTPException(status_code=500, detail="Failed to update")


class CalculateTimeRequest(BaseModel):
    """Request body for features-based time calculation."""
    cutting_mode: str = Field(default="mid", pattern="^(low|mid|high)$")


@router.post("/estimations/{estimation_id}/calculate-time")
async def calculate_time_from_features(
    estimation_id: int,
    data: CalculateTimeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Calculate machining time from extracted features using cutting conditions DB."""
    try:
        stmt = select(TimeVisionEstimation).where(
            TimeVisionEstimation.id == estimation_id,
            TimeVisionEstimation.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
    except Exception as exc:
        logger.error("Failed to find estimation %d: %s", estimation_id, exc)
        raise HTTPException(status_code=500, detail="Database error")

    if not record:
        raise HTTPException(status_code=404, detail="Estimation not found")

    # Parse features from corrected or original JSON
    features_str = record.features_corrected_json or record.features_json
    if not features_str:
        raise HTTPException(status_code=400, detail="No features data available")

    try:
        features_data = json.loads(features_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid features JSON")

    features_list = features_data.get("features", [])
    material_info = features_data.get("material", {})
    part_type = features_data.get("part_type", "PRI")

    # Resolve material group from material designation
    material_group = "20910004"  # Default: konstrukční ocel
    if material_info.get("group"):
        from app.services.cutting_conditions_catalog import MATERIAL_GROUP_MAP
        group_name = material_info["group"].lower()
        for code, meta in MATERIAL_GROUP_MAP.items():
            if group_name in meta.get("name", "").lower():
                material_group = code
                break

    # Calculate
    calc_result = calculate_features_time(
        features_json=features_list,
        material_group=material_group,
        cutting_mode=data.cutting_mode,
        part_type=part_type,
    )

    # Save calculated_time_min to DB
    try:
        record.calculated_time_min = calc_result["calculated_time_min"]
        record.updated_at = datetime.utcnow()
        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.error("Failed to save calculated time: %s", exc)

    return calc_result


@router.get("/export-features-training")
async def export_features_training_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """Export corrected features as JSONL for GPT-4o vision fine-tuning (features model v2).

    Format: OpenAI vision fine-tuning JSONL
    Each line = {messages: [system, user(image+text), assistant(corrected_features_json)]}

    Returns only records where:
    - estimation_type = "features_v2"
    - features_corrected_json IS NOT NULL
    - deleted_at IS NULL
    """
    from starlette.responses import Response
    from app.services.openai_vision_service import _pdf_to_base64_image
    from app.services.openai_vision_prompts import OPENAI_FEATURES_SYSTEM, build_features_prompt

    query = (
        select(TimeVisionEstimation)
        .where(
            TimeVisionEstimation.deleted_at.is_(None),
            TimeVisionEstimation.estimation_type == "features_v2",
            TimeVisionEstimation.features_corrected_json.isnot(None),
        )
        .order_by(TimeVisionEstimation.id)
    )
    result = await db.execute(query)
    records = result.scalars().all()

    lines = []
    skipped = []
    for record in records:
        pdf_path = _resolve_pdf_path(record.pdf_path, record.pdf_filename)
        if not pdf_path.exists():
            skipped.append(record.pdf_filename)
            continue

        try:
            img_b64 = _pdf_to_base64_image(str(pdf_path))
        except Exception:
            skipped.append(record.pdf_filename)
            continue

        training_example = {
            "messages": [
                {
                    "role": "system",
                    "content": OPENAI_FEATURES_SYSTEM,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_b64}",
                                "detail": "high",
                            },
                        },
                        {
                            "type": "text",
                            "text": build_features_prompt(),
                        },
                    ],
                },
                {
                    "role": "assistant",
                    "content": record.features_corrected_json,
                },
            ]
        }
        lines.append(json.dumps(training_example, ensure_ascii=False))

    if skipped:
        logger.warning(
            "Skipped %d records (missing PDF): %s", len(skipped), skipped
        )

    logger.info(
        "Exported %d features training examples (%d skipped)", len(lines), len(skipped)
    )

    jsonl_content = "\n".join(lines)
    return Response(
        content=jsonl_content,
        media_type="application/jsonl",
        headers={
            "Content-Disposition": (
                f"attachment; filename=gestima_features_ft_{len(lines)}_samples.jsonl"
            ),
        },
    )


@router.get("/export-training")
async def export_training_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """Export calibrated estimations as JSONL for GPT-4o vision fine-tuning.

    Format: OpenAI vision fine-tuning JSONL (gpt-4o-2024-08-06)
    Each line = {messages: [system, user(image+text), assistant(JSON)]}

    Ground truth priority:
    1. actual_time_min (real production time) — highest weight
    2. human_estimate_min (human estimate before manufacturing) — fallback

    Returns only records where:
    - ai_provider IN ('openai', 'openai_ft')
    - actual_time_min OR human_estimate_min IS NOT NULL
    - deleted_at IS NULL

    Uses _pdf_to_base64_image for consistent rendering (300 DPI, 4096px cap).
    """
    from starlette.responses import Response
    from app.services.openai_vision_service import _pdf_to_base64_image

    query = (
        select(TimeVisionEstimation)
        .where(
            TimeVisionEstimation.deleted_at.is_(None),
            TimeVisionEstimation.ai_provider.in_(["openai", "openai_ft"]),
            or_(
                TimeVisionEstimation.actual_time_min.isnot(None),
                TimeVisionEstimation.human_estimate_min.isnot(None),
            ),
        )
        .order_by(TimeVisionEstimation.id)
    )
    result = await db.execute(query)
    records = result.scalars().all()

    # Fine-tuning system prompt — same role as inference prompt
    # but without reference tables (model learns from examples)
    ft_system = (
        "Jsi CNC technolog s 20 lety praxe v zakázkové strojírenské výrobě. "
        "Podívej se na výrobní výkres a odhadni produkční strojní čas. "
        "POUZE produkční strojní čas (spindle time): řezání, posuvy, rychloposuvy. "
        "NE: upínání, kontrola, manipulace, seřízení. "
        "Odpověz POUZE validním JSON."
    )

    lines = []
    skipped = []
    for record in records:
        pdf_path = _resolve_pdf_path(record.pdf_path, record.pdf_filename)
        if not pdf_path.exists():
            skipped.append(record.pdf_filename)
            continue

        try:
            img_b64 = _pdf_to_base64_image(str(pdf_path))
        except Exception:
            skipped.append(record.pdf_filename)
            continue

        # Parse stored breakdown if available
        breakdown = []
        if record.estimation_breakdown_json:
            try:
                breakdown = json.loads(record.estimation_breakdown_json)
            except (json.JSONDecodeError, TypeError):
                pass

        # Ground truth: prefer actual production time, fallback to human estimate
        ground_truth_min = record.actual_time_min or record.human_estimate_min
        if ground_truth_min is None:
            skipped.append(record.pdf_filename)
            continue

        answer_dict = {
            "part_type": record.part_type,
            "complexity": record.complexity,
            "material_detected": record.material_detected,
            "estimated_time_min": ground_truth_min,
            "confidence": "high" if record.actual_time_min else "medium",
            "reasoning": record.estimation_reasoning or "",
            "breakdown": breakdown,
        }

        # Add dimension fields if available
        if record.max_diameter_mm is not None:
            answer_dict["max_diameter_mm"] = record.max_diameter_mm
        if record.max_length_mm is not None:
            answer_dict["max_length_mm"] = record.max_length_mm
        if record.max_width_mm is not None:
            answer_dict["max_width_mm"] = record.max_width_mm
        if record.max_height_mm is not None:
            answer_dict["max_height_mm"] = record.max_height_mm

        answer = json.dumps(answer_dict, ensure_ascii=False)

        training_example = {
            "messages": [
                {
                    "role": "system",
                    "content": ft_system,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_b64}",
                                "detail": "high",
                            },
                        },
                        {
                            "type": "text",
                            "text": "Odhadni produkční strojní čas v minutách.",
                        },
                    ],
                },
                {
                    "role": "assistant",
                    "content": answer,
                },
            ]
        }
        lines.append(json.dumps(training_example, ensure_ascii=False))

    if skipped:
        logger.warning(
            "Skipped %d records (missing PDF): %s", len(skipped), skipped
        )

    logger.info(
        "Exported %d training examples (%d skipped)", len(lines), len(skipped)
    )

    jsonl_content = "\n".join(lines)
    return Response(
        content=jsonl_content,
        media_type="application/jsonl",
        headers={
            "Content-Disposition": (
                f"attachment; filename=gestima_ft_{len(lines)}_samples.jsonl"
            ),
        },
    )


class FeatureTypeInfo(BaseModel):
    """Feature type metadata for frontend."""
    key: str = Field(min_length=1, max_length=100)
    label_cs: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=1000)
    example: str = Field(min_length=1, max_length=500)
    group: str = Field(min_length=1, max_length=50)
    has_time: bool


class FeatureTypesCatalogResponse(BaseModel):
    """Feature types catalog response."""
    types: List[FeatureTypeInfo]
    groups: Dict[str, str]


@router.get("/feature-types", response_model=FeatureTypesCatalogResponse)
async def get_feature_types():
    """Return feature types catalog for frontend.

    Returns all feature types with metadata (labels, descriptions, examples).
    Used by frontend to display correct Czech labels and group features.
    """
    from app.services.feature_types import FEATURE_TYPES, FEATURE_GROUPS

    result = []
    for key, meta in FEATURE_TYPES.items():
        result.append(FeatureTypeInfo(
            key=key,
            label_cs=meta["label_cs"],
            description=meta["description"],
            example=meta["example"],
            group=meta["group"],
            has_time=meta["has_time"],
        ))

    return FeatureTypesCatalogResponse(
        types=result,
        groups=FEATURE_GROUPS,
    )
