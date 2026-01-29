"""GESTIMA - Operations API router"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database import get_db
from app.db_helpers import set_audit, safe_commit
from app.dependencies import get_current_user, require_role
from app.models import User, UserRole
from app.models.operation import Operation, OperationCreate, OperationUpdate, OperationResponse, ChangeModeRequest

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

    # Update fields (exclude version - it's auto-incremented by event listener)
    for key, value in data.model_dump(exclude_unset=True, exclude={'version'}).items():
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
