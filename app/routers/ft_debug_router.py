"""GESTIMA - FT Debug router for fine-tuning data inspection."""

import io
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.user import UserRole
from app.schemas.ft_debug import (
    FtExportRequest,
    FtInferenceRequest,
    FtInferenceResult,
    FtPartsResponse,
)
from app.services.ft_debug_service import FtDebugService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ft/debug", tags=["FT Debug"])


@router.get("/parts", response_model=FtPartsResponse)
async def list_ft_parts(
    min_vp: int = Query(3, ge=1, le=20, description="Minimum VP count"),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_role([UserRole.ADMIN])),
) -> FtPartsResponse:
    """List all parts eligible for FT training with GT and CV data.

    Loads all candidate parts in two bulk SQL queries, computes ground truth
    per machine category (trimmed mean from VP production records), and returns
    eligibility status with skip reasons for excluded parts.
    """
    service = FtDebugService(db)
    try:
        return await service.list_eligible_parts(min_vp=min_vp)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("list_ft_parts failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/inference", response_model=FtInferenceResult)
async def run_inference(
    request: FtInferenceRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_role([UserRole.ADMIN])),
) -> FtInferenceResult:
    """Run GPT-4.1 few-shot inference on a part and compare with GT.

    Renders the part drawing PDF to PNG, sends it to GPT-4.1 with 6 few-shot
    examples (3 rotational + 3 prismatic), and compares the AI prediction with
    the ground truth computed from production records.

    Returns per-category time deltas and MAPE score.
    """
    service = FtDebugService(db)
    try:
        return await service.run_inference(request.part_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("run_inference failed for part_id=%d", request.part_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/export")
async def export_jsonl(
    request: FtExportRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_role([UserRole.ADMIN])),
) -> StreamingResponse:
    """Export selected parts as JSONL for FT training.

    Generates OpenAI-compatible fine-tuning JSONL where each line is a
    training example: system prompt + drawing image + ground truth JSON answer.

    Returns JSONL as a downloadable file attachment.
    """
    service = FtDebugService(db)
    try:
        jsonl_bytes = await service.export_jsonl(request.part_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("export_jsonl failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return StreamingResponse(
        io.BytesIO(jsonl_bytes),
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": "attachment; filename=ft_v2_debug_export.jsonl"
        },
    )
