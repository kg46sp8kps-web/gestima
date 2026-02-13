"""TimeVision - API router for AI machining time estimation"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.database import async_session
from app.models.time_vision import (
    TimeVisionEstimation,
    TimeVisionResponse,
    TimeVisionListItem,
    TimeVisionActualTimeUpdate,
)
from app.services.openai_vision_service import estimate_from_pdf_openai, is_fine_tuned_model, OPENAI_MODEL

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/time-vision", tags=["TimeVision"])

DRAWINGS_DIR = Path("uploads/drawings")


@router.get("/model-info")
async def get_model_info():
    """Return currently configured OpenAI model info."""
    return {
        "model": OPENAI_MODEL,
        "is_fine_tuned": is_fine_tuned_model(),
        "provider": "openai_ft" if is_fine_tuned_model() else "openai",
    }


async def get_db():
    """Database session dependency."""
    async with async_session() as session:
        yield session


class DrawingFileInfo(BaseModel):
    """Info about a drawing file in uploads/drawings"""
    filename: str = Field(min_length=1, max_length=500)
    size_bytes: int = Field(ge=0)
    has_estimation: bool = Field(default=False)
    estimation_id: Optional[int] = Field(default=None)
    status: Optional[str] = Field(default=None)
    has_openai_estimation: bool = Field(default=False)
    ai_provider: Optional[str] = Field(default=None)
    ai_model: Optional[str] = Field(default=None)


class CalibrationUpdate(BaseModel):
    """Update estimation fields for calibration."""
    part_type: Optional[str] = Field(None, pattern="^(ROT|PRI|COMBINED)$")
    complexity: Optional[str] = Field(None, pattern="^(simple|medium|complex)$")
    actual_time_min: Optional[float] = Field(None, gt=0, lt=10000)
    actual_notes: Optional[str] = Field(None, max_length=2000)
    human_estimate_min: Optional[float] = Field(None, gt=0, lt=10000)
    version: int = Field(ge=0)


@router.get("/drawings", response_model=List[DrawingFileInfo])
async def list_drawings(db: AsyncSession = Depends(get_db)):
    """List PDF files in uploads/drawings directory."""
    if not DRAWINGS_DIR.exists():
        return []

    pdf_files = sorted(DRAWINGS_DIR.glob("*.pdf"), key=lambda p: p.name)

    # Check which files already have estimations (take NEWEST per file)
    try:
        from sqlalchemy import func
        # Subquery: max id per filename = newest estimation
        newest_ids = (
            select(
                func.max(TimeVisionEstimation.id).label("max_id"),
            )
            .where(TimeVisionEstimation.deleted_at.is_(None))
            .group_by(TimeVisionEstimation.pdf_filename)
            .subquery()
        )
        stmt = (
            select(
                TimeVisionEstimation.pdf_filename,
                TimeVisionEstimation.id,
                TimeVisionEstimation.status,
                TimeVisionEstimation.ai_provider,
                TimeVisionEstimation.ai_model,
            )
            .where(
                TimeVisionEstimation.deleted_at.is_(None),
                TimeVisionEstimation.id.in_(select(newest_ids.c.max_id)),
            )
        )
        result = await db.execute(stmt)
        estimation_map = {row[0]: (row[1], row[2], row[3], row[4]) for row in result.all()}
    except Exception as exc:
        logger.warning("Failed to query estimations: %s", exc)
        estimation_map = {}

    # Check which files have OpenAI estimations (base or fine-tuned)
    try:
        openai_stmt = (
            select(TimeVisionEstimation.pdf_filename)
            .where(
                TimeVisionEstimation.deleted_at.is_(None),
                TimeVisionEstimation.ai_provider.in_(["openai", "openai_ft"]),
            )
            .distinct()
        )
        openai_result = await db.execute(openai_stmt)
        openai_filenames = {row[0] for row in openai_result.all()}
    except Exception as exc:
        logger.warning("Failed to query OpenAI estimations: %s", exc)
        openai_filenames = set()

    files = []
    for pdf_path in pdf_files:
        est_info = estimation_map.get(pdf_path.name)
        files.append(DrawingFileInfo(
            filename=pdf_path.name,
            size_bytes=pdf_path.stat().st_size,
            has_estimation=est_info is not None,
            estimation_id=est_info[0] if est_info else None,
            status=est_info[1] if est_info else None,
            has_openai_estimation=pdf_path.name in openai_filenames,
            ai_provider=est_info[2] if est_info else None,
            ai_model=est_info[3] if est_info else None,
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

    return FileResponse(str(pdf_path), media_type="application/pdf")


class ProcessRequest(BaseModel):
    """Request to process a PDF drawing."""
    filename: str = Field(min_length=1, max_length=500)


@router.get("/estimations", response_model=List[TimeVisionListItem])
async def list_estimations(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
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

        result = await db.execute(stmt)
        records = result.scalars().all()
        return [TimeVisionListItem.model_validate(r) for r in records]
    except Exception as exc:
        logger.error("Failed to list estimations: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list estimations")


@router.get("/estimations/{estimation_id}", response_model=TimeVisionResponse)
async def get_estimation(
    estimation_id: int,
    db: AsyncSession = Depends(get_db),
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
async def get_batch_test_results():
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
):
    """Process a drawing using OpenAI GPT-4o vision (single-call estimation).

    SSE stream with 2 steps:
      1. OpenAI vision estimation
      2. Save to database
    """
    if ".." in request.filename or "/" in request.filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    pdf_path = DRAWINGS_DIR / request.filename
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {request.filename}")

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

            # UPSERT: reuse existing record per filename (preserves calibration data)
            existing_result = await db.execute(
                select(TimeVisionEstimation)
                .where(
                    TimeVisionEstimation.pdf_filename == request.filename,
                    TimeVisionEstimation.deleted_at.is_(None),
                )
                .order_by(TimeVisionEstimation.id.desc())
                .limit(1)
            )
            record = existing_result.scalar_one_or_none()

            ai_data = {
                "pdf_path": str(pdf_path),
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
                record.updated_at = datetime.utcnow()
                logger.info(f"Updated existing estimation #{record.id} for {request.filename}")
            else:
                # INSERT new
                record = TimeVisionEstimation(pdf_filename=request.filename, **ai_data)
                db.add(record)
                logger.info(f"Created new estimation for {request.filename}")

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


@router.get("/export-training")
async def export_training_data(
    db: AsyncSession = Depends(get_db),
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

    from sqlalchemy import or_
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
        pdf_path = Path(record.pdf_path)
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
