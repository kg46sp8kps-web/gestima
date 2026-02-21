"""GESTIMA - Technology Builder Router

POST /api/technology/generate — Generate complete technology plan from AI estimation.
Wraps AI Vision output with deterministic logic (cutting, QC, machine selection).

AI Vision endpoints are NOT modified — this is a separate post-processing layer.
"""

import logging
from typing import Optional, List

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import User
from app.models.enums import UserRole
from app.models.operation import Operation, OperationResponse
from app.models.material_input import MaterialInput
from app.models.time_vision import TimeVisionEstimation
from app.db_helpers import set_audit, safe_commit
from app.services.technology_builder import build_technology

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/technology", tags=["Technology Builder"])


class GenerateTechnologyRequest(BaseModel):
    """Request pro generování technologického postupu."""
    estimation_id: int = Field(..., gt=0, description="ID AI odhadu z TimeVision")
    part_id: int = Field(..., gt=0, description="ID dílu")
    material_input_id: Optional[int] = Field(
        None, gt=0, description="ID materiálového vstupu (volitelné, použije první)"
    )
    cutting_mode: str = Field(
        "mid", pattern="^(low|mid|high)$", description="Řezný režim pro pilu"
    )


class GenerateTechnologyResponse(BaseModel):
    """Response s vygenerovanými operacemi."""
    operations: List[OperationResponse] = Field(
        ..., description="Seznam vygenerovaných operací"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Varování (chybějící data apod.)"
    )


@router.post("/generate", response_model=GenerateTechnologyResponse)
async def generate_technology(
    request: GenerateTechnologyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR])),
):
    """
    Generate complete technology plan from AI estimation.

    Creates 3 operations via UPSERT (by seq number):
    - OP 10: Řezání materiálu (calculated from stock cross-section × material coefficient)
    - OP 20: Strojní operace (AI estimated_time_min)
    - OP 100: Kontrola (setup_time based on complexity)
    """

    # 1. Load estimation
    est_result = await db.execute(
        select(TimeVisionEstimation).where(
            TimeVisionEstimation.id == request.estimation_id,
            TimeVisionEstimation.deleted_at.is_(None),
        )
    )
    estimation = est_result.scalar_one_or_none()
    if not estimation:
        raise HTTPException(404, "AI odhad nenalezen")

    # 2. Load material input (optional)
    material_input = None
    if request.material_input_id:
        mi_result = await db.execute(
            select(MaterialInput).where(
                MaterialInput.id == request.material_input_id,
                MaterialInput.part_id == request.part_id,
                MaterialInput.deleted_at.is_(None),
            )
        )
        material_input = mi_result.scalar_one_or_none()
    else:
        # Use first material input for the part
        mi_result = await db.execute(
            select(MaterialInput)
            .where(
                MaterialInput.part_id == request.part_id,
                MaterialInput.deleted_at.is_(None),
            )
            .order_by(MaterialInput.seq)
            .limit(1)
        )
        material_input = mi_result.scalar_one_or_none()

    # 3. Build technology plan
    plan = await build_technology(
        estimation=estimation,
        material_input=material_input,
        part_id=request.part_id,
        db=db,
        cutting_mode=request.cutting_mode,
    )

    # 4. UPSERT operations (by seq number)
    existing_ops_result = await db.execute(
        select(Operation).where(
            Operation.part_id == request.part_id,
            Operation.deleted_at.is_(None),
        )
    )
    existing_ops = list(existing_ops_result.scalars().all())

    created_operations = []
    try:
        for op_create in plan.operations:
            # Find existing operation with same seq
            existing = next(
                (op for op in existing_ops if op.seq == op_create.seq),
                None,
            )

            if existing:
                # UPDATE existing operation
                existing.name = op_create.name
                existing.type = op_create.type
                existing.icon = op_create.icon
                existing.work_center_id = op_create.work_center_id
                existing.setup_time_min = op_create.setup_time_min
                existing.operation_time_min = op_create.operation_time_min
                existing.cutting_mode = op_create.cutting_mode
                existing.ai_estimation_id = op_create.ai_estimation_id
                set_audit(existing, current_user.username, is_update=True)
                created_operations.append(existing)
            else:
                # CREATE new operation
                operation = Operation(**op_create.model_dump())
                set_audit(operation, current_user.username)
                db.add(operation)
                created_operations.append(operation)

        await safe_commit(db, action="generování technologie")

        # Refresh all operations to get IDs and versions
        for op in created_operations:
            await db.refresh(op)

    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        logger.error(f"Failed to generate technology: {exc}", exc_info=True)
        raise HTTPException(500, f"Chyba při generování technologie: {exc}")

    return GenerateTechnologyResponse(
        operations=[
            OperationResponse.model_validate(op) for op in created_operations
        ],
        warnings=plan.warnings,
    )
