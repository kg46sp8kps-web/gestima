"""GESTIMA - Operations API router

ADR-024: Added M:N linking endpoints (operation → material)
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database import get_db
from app.db_helpers import set_audit, safe_commit
from app.dependencies import get_current_user, require_role
from app.models import User, UserRole
from app.models.operation import Operation, OperationCreate, OperationUpdate, OperationResponse, ChangeModeRequest
from app.models.material_input import MaterialInput, material_operation_link, MaterialOperationLinkRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/part/{part_id}", response_model=List[OperationResponse])
async def get_operations(
    part_id: int,
    skip: int = Query(0, ge=0, description="Počet záznamů k přeskočení"),
    limit: int = Query(100, ge=1, le=500, description="Max počet záznamů"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Operation)
        .where(Operation.part_id == part_id, Operation.deleted_at.is_(None))
        .order_by(Operation.seq)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{operation_id}", response_model=OperationResponse)
async def get_operation(
    operation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Operation).where(Operation.id == operation_id))
    operation = result.scalar_one_or_none()
    if not operation:
        raise HTTPException(status_code=404, detail="Operace nenalezena")
    return operation


@router.post("/", response_model=OperationResponse)
async def create_operation(
    data: OperationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    operation = Operation(**data.model_dump())
    set_audit(operation, current_user.username)
    db.add(operation)

    operation = await safe_commit(db, operation, "vytváření operace", "Konflikt dat (neplatná reference na díl)")
    logger.info(f"Created operation: {operation.type}", extra={"operation_id": operation.id, "part_id": operation.part_id, "user": current_user.username})
    return operation


@router.put("/{operation_id}", response_model=OperationResponse)
async def update_operation(
    operation_id: int,
    data: OperationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    result = await db.execute(select(Operation).where(Operation.id == operation_id))
    operation = result.scalar_one_or_none()
    if not operation:
        raise HTTPException(status_code=404, detail="Operace nenalezena")

    # Optimistic locking check (ADR-008)
    if operation.version != data.version:
        logger.warning(f"Version conflict updating operation {operation_id}: expected {data.version}, got {operation.version}", extra={"operation_id": operation_id, "user": current_user.username})
        raise HTTPException(status_code=409, detail="Data byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu.")

    update_data = data.model_dump(exclude_unset=True, exclude={'version'})

    # Update fields (exclude version - it's auto-incremented by event listener)
    for key, value in update_data.items():
        setattr(operation, key, value)

    set_audit(operation, current_user.username, is_update=True)

    operation = await safe_commit(db, operation, "aktualizace operace", "Konflikt dat (neplatné reference)")
    logger.info(f"Updated operation: {operation.type}", extra={"operation_id": operation.id, "user": current_user.username})
    return operation


@router.delete("/{operation_id}", status_code=204)
async def delete_operation(
    operation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    result = await db.execute(select(Operation).where(Operation.id == operation_id))
    operation = result.scalar_one_or_none()
    if not operation:
        raise HTTPException(status_code=404, detail="Operace nenalezena")

    operation_type = operation.type
    await db.delete(operation)

    await safe_commit(db, action="mazání operace", integrity_error_msg="Nelze smazat operaci - existují závislé záznamy (features)")
    logger.info(f"Deleted operation: {operation_type}", extra={"operation_id": operation_id, "user": current_user.username})
    return {"message": "Operace smazána"}


@router.post("/{operation_id}/change-mode", response_model=OperationResponse)
async def change_mode(
    operation_id: int,
    data: ChangeModeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    result = await db.execute(select(Operation).where(Operation.id == operation_id))
    operation = result.scalar_one_or_none()
    if not operation:
        raise HTTPException(status_code=404, detail="Operace nenalezena")

    # Optimistic locking check (ADR-008)
    if operation.version != data.version:
        logger.warning(f"Version conflict changing mode for operation {operation_id}: expected {data.version}, got {operation.version}", extra={"operation_id": operation_id, "user": current_user.username})
        raise HTTPException(status_code=409, detail="Data byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu.")

    operation.cutting_mode = data.cutting_mode.value
    set_audit(operation, current_user.username, is_update=True)

    operation = await safe_commit(db, operation, "změna režimu")
    logger.info(f"Changed cutting mode to {data.cutting_mode.value}", extra={"operation_id": operation_id, "user": current_user.username})
    return operation


# ═══════════════════════════════════════════════════════════════
# M:N LINKING (Operation ↔ MaterialInput) - ADR-024
# ═══════════════════════════════════════════════════════════════

@router.post("/{operation_id}/link-material/{material_id}", status_code=201, response_model=dict)
async def link_material_to_operation(
    operation_id: int,
    material_id: int,
    request: Optional[MaterialOperationLinkRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.OPERATOR]))
):
    """Přiřadit materiál k operaci (M:N vztah) - operation-side endpoint"""

    # Verify Operation exists
    op_result = await db.execute(
        select(Operation).where(
            and_(
                Operation.id == operation_id,
                Operation.deleted_at.is_(None)
            )
        )
    )
    if not op_result.scalar_one_or_none():
        raise HTTPException(
            status_code=404,
            detail=f"Operation {operation_id} not found"
        )

    # Verify MaterialInput exists
    mat_result = await db.execute(
        select(MaterialInput).where(
            and_(
                MaterialInput.id == material_id,
                MaterialInput.deleted_at.is_(None)
            )
        )
    )
    if not mat_result.scalar_one_or_none():
        raise HTTPException(
            status_code=404,
            detail=f"MaterialInput {material_id} not found"
        )

    # Check if link already exists
    existing = await db.execute(
        select(material_operation_link).where(
            and_(
                material_operation_link.c.material_input_id == material_id,
                material_operation_link.c.operation_id == operation_id
            )
        )
    )
    if existing.first():
        raise HTTPException(
            status_code=409,
            detail="Link already exists"
        )

    # Create link
    try:
        consumed_quantity = request.consumed_quantity if request else None
        await db.execute(
            material_operation_link.insert().values(
                material_input_id=material_id,
                operation_id=operation_id,
                consumed_quantity=consumed_quantity
            )
        )

        await db.commit()
        logger.info(f"Linked material {material_id} to operation {operation_id}", extra={"operation_id": operation_id, "material_id": material_id, "user": current_user.username})

        return {"message": "Link created successfully"}
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Integrity error linking material {material_id} to operation {operation_id}: {e}")
        raise HTTPException(status_code=409, detail="Chyba při vytváření vazby - neplatná reference")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error linking material: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při vytváření vazby")


@router.delete("/{operation_id}/unlink-material/{material_id}", status_code=204)
async def unlink_material_from_operation(
    operation_id: int,
    material_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.OPERATOR]))
):
    """Odebrat vazbu operace → materiál"""

    try:
        result = await db.execute(
            delete(material_operation_link).where(
                and_(
                    material_operation_link.c.material_input_id == material_id,
                    material_operation_link.c.operation_id == operation_id
                )
            )
        )

        if result.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Link not found"
            )

        await db.commit()
        logger.info(f"Unlinked material {material_id} from operation {operation_id}", extra={"operation_id": operation_id, "material_id": material_id, "user": current_user.username})
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error unlinking material: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při odebírání vazby")
