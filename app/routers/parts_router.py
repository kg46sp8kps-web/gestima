"""GESTIMA - Parts API router"""

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
from app.models.part import Part, PartCreate, PartUpdate, PartResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[PartResponse])
async def get_parts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Part).order_by(Part.updated_at.desc()))
    return result.scalars().all()


@router.get("/{part_id}", response_model=PartResponse)
async def get_part(
    part_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Part).where(Part.id == part_id))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")
    return part


@router.post("/", response_model=PartResponse)
async def create_part(
    data: PartCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    # Kontrola duplicitního čísla dílu
    result = await db.execute(select(Part).where(Part.part_number == data.part_number))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"Díl s číslem '{data.part_number}' již existuje")

    part = Part(**data.model_dump())
    set_audit(part, current_user.username)  # Audit trail helper (db_helpers.py)
    db.add(part)

    try:
        await db.commit()
        await db.refresh(part)
        logger.info(f"Created part: {part.part_number}", extra={"part_id": part.id, "user": current_user.username})
        return part
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Integrity error creating part: {e}", exc_info=True)
        raise HTTPException(status_code=409, detail="Konflikt dat (duplicitní záznam nebo neplatné reference)")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error creating part: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při vytváření dílu")


@router.put("/{part_id}", response_model=PartResponse)
async def update_part(
    part_id: int,
    data: PartUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    result = await db.execute(select(Part).where(Part.id == part_id))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")

    # Optimistic locking check (ADR-008)
    if part.version != data.version:
        logger.warning(f"Version conflict updating part {part_id}: expected {data.version}, got {part.version}", extra={"part_id": part_id, "user": current_user.username})
        raise HTTPException(status_code=409, detail="Data byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu.")

    # Update fields (exclude version - it's auto-incremented by event listener)
    for key, value in data.model_dump(exclude_unset=True, exclude={'version'}).items():
        setattr(part, key, value)

    set_audit(part, current_user.username, is_update=True)  # Audit trail helper

    try:
        await db.commit()
        await db.refresh(part)
        logger.info(f"Updated part: {part.part_number}", extra={"part_id": part.id, "user": current_user.username})
        return part
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Integrity error updating part {part_id}: {e}", exc_info=True)
        raise HTTPException(status_code=409, detail="Konflikt dat (duplicitní záznam nebo neplatné reference)")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error updating part {part_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při aktualizaci dílu")


@router.delete("/{part_id}")
async def delete_part(
    part_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    result = await db.execute(select(Part).where(Part.id == part_id))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")

    part_number = part.part_number
    await db.delete(part)

    try:
        await db.commit()
        logger.info(f"Deleted part: {part_number}", extra={"part_id": part_id, "user": current_user.username})
        return {"message": "Díl smazán"}
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Integrity error deleting part {part_id}: {e}", exc_info=True)
        raise HTTPException(status_code=409, detail="Nelze smazat díl - existují závislé záznamy (operace, dávky)")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error deleting part {part_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při mazání dílu")
