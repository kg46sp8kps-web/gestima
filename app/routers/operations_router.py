"""GESTIMA - Operations API router"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database import get_db
from app.db_helpers import set_audit
from app.dependencies import get_current_user, require_role
from app.models import User, UserRole
from app.models.operation import Operation, OperationCreate, OperationUpdate, OperationResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/part/{part_id}", response_model=List[OperationResponse])
async def get_operations(
    part_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Operation).where(Operation.part_id == part_id).order_by(Operation.seq)
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

    try:
        await db.commit()
        await db.refresh(operation)
        logger.info(f"Created operation: {operation.operation_type}", extra={"operation_id": operation.id, "part_id": operation.part_id, "user": current_user.username})
        return operation
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Integrity error creating operation: {e}", exc_info=True)
        raise HTTPException(status_code=409, detail="Konflikt dat (neplatná reference na díl)")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error creating operation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při vytváření operace")


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

    try:
        await db.commit()
        await db.refresh(operation)
        logger.info(f"Updated operation: {operation.type}", extra={"operation_id": operation.id, "user": current_user.username})
        return operation
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Integrity error updating operation {operation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=409, detail="Konflikt dat (neplatné reference)")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error updating operation {operation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při aktualizaci operace")


@router.delete("/{operation_id}")
async def delete_operation(
    operation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    result = await db.execute(select(Operation).where(Operation.id == operation_id))
    operation = result.scalar_one_or_none()
    if not operation:
        raise HTTPException(status_code=404, detail="Operace nenalezena")

    operation_type = operation.operation_type
    await db.delete(operation)

    try:
        await db.commit()
        logger.info(f"Deleted operation: {operation_type}", extra={"operation_id": operation_id, "user": current_user.username})
        return {"message": "Operace smazána"}
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Integrity error deleting operation {operation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=409, detail="Nelze smazat operaci - existují závislé záznamy (features)")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error deleting operation {operation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při mazání operace")


@router.post("/{operation_id}/change-mode", response_model=OperationResponse)
async def change_mode(
    operation_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    result = await db.execute(select(Operation).where(Operation.id == operation_id))
    operation = result.scalar_one_or_none()
    if not operation:
        raise HTTPException(status_code=404, detail="Operace nenalezena")

    # Optimistic locking check (ADR-008)
    version = data.get("version")
    if version is None:
        raise HTTPException(status_code=400, detail="Version je povinná")
    if operation.version != version:
        logger.warning(f"Version conflict changing mode for operation {operation_id}: expected {version}, got {operation.version}", extra={"operation_id": operation_id, "user": current_user.username})
        raise HTTPException(status_code=409, detail="Data byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu.")

    cutting_mode = data.get("cutting_mode")
    if cutting_mode not in ["low", "mid", "high"]:
        raise HTTPException(status_code=400, detail="Neplatný režim")

    operation.cutting_mode = cutting_mode
    set_audit(operation, current_user.username, is_update=True)

    try:
        await db.commit()
        await db.refresh(operation)
        logger.info(f"Changed cutting mode to {cutting_mode}", extra={"operation_id": operation_id, "user": current_user.username})
        return operation
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error changing mode for operation {operation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při změně režimu")
