"""GESTIMA - Batches API router"""

import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database import get_db
from app.db_helpers import set_audit
from app.dependencies import get_current_user, require_role
from app.models import User, UserRole
from app.models.batch import Batch, BatchCreate, BatchResponse
from app.models.part import Part
from app.models.material import MaterialItem
from app.services.snapshot_service import create_batch_snapshot

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/part/{part_id}", response_model=List[BatchResponse])
async def get_batches(
    part_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Batch).where(Batch.part_id == part_id).order_by(Batch.quantity)
    )
    return result.scalars().all()


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Dávka nenalezena")
    return batch


@router.post("/", response_model=BatchResponse)
async def create_batch(
    data: BatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    batch = Batch(**data.model_dump())
    set_audit(batch, current_user.username)
    db.add(batch)

    try:
        await db.commit()
        await db.refresh(batch)
        logger.info(f"Created batch: quantity={batch.quantity}", extra={"batch_id": batch.id, "part_id": batch.part_id, "user": current_user.username})
        return batch
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Integrity error creating batch: {e}", exc_info=True)
        raise HTTPException(status_code=409, detail="Konflikt dat (neplatná reference na díl)")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error creating batch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při vytváření dávky")


@router.delete("/{batch_id}")
async def delete_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    result = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Dávka nenalezena")

    # ADR-012: Frozen batch lze smazat pouze soft delete
    if batch.is_frozen:
        batch.deleted_at = datetime.utcnow()
        batch.deleted_by = current_user.username
        try:
            await db.commit()
            logger.info(f"Soft deleted frozen batch: quantity={batch.quantity}", extra={"batch_id": batch_id, "user": current_user.username})
            return {"message": "Zmrazená dávka smazána (soft delete)"}
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Database error soft deleting batch {batch_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Chyba databáze při mazání dávky")

    quantity = batch.quantity
    await db.delete(batch)

    try:
        await db.commit()
        logger.info(f"Deleted batch: quantity={quantity}", extra={"batch_id": batch_id, "user": current_user.username})
        return {"message": "Dávka smazána"}
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error deleting batch {batch_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při mazání dávky")


@router.post("/{batch_id}/freeze", response_model=BatchResponse)
async def freeze_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """
    Zmrazí ceny batche (ADR-012: Minimal Snapshot).

    Vytvoří snapshot s aktuálními cenami a zmrazí batch (is_frozen=True).
    Zmrazený batch nelze editovat.
    """
    # Načíst batch s part + material_item + group (eager loading)
    stmt = select(Batch).where(Batch.id == batch_id).options(
        selectinload(Batch.part).selectinload(Part.material_item).selectinload(MaterialItem.group)
    )
    result = await db.execute(stmt)
    batch = result.scalar_one_or_none()

    if not batch:
        raise HTTPException(status_code=404, detail="Dávka nenalezena")

    if batch.is_frozen:
        raise HTTPException(status_code=409, detail="Dávka je již zmrazena")

    # Vytvořit snapshot
    snapshot = await create_batch_snapshot(batch, current_user.username, db)

    # Nastavit freeze metadata
    batch.is_frozen = True
    batch.frozen_at = datetime.utcnow()
    batch.frozen_by_id = current_user.id
    batch.snapshot_data = snapshot
    batch.unit_price_frozen = batch.unit_cost  # Redundantní pro reporty
    batch.total_price_frozen = batch.total_cost

    try:
        await db.commit()
        await db.refresh(batch)
        logger.info(f"Frozen batch: quantity={batch.quantity}", extra={"batch_id": batch_id, "user": current_user.username})
        return batch
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error freezing batch {batch_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při zmrazování dávky")


@router.post("/{batch_id}/clone", response_model=BatchResponse)
async def clone_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """
    Naklonuje batch (vytvoří nový, nezmrazený batch se stejnými parametry).

    Užitečné když uživatel chce upravit zmrazenou nabídku - naklonuje ji
    a pracuje s novou verzí (která má LIVE ceny).
    """
    result = await db.execute(select(Batch).where(Batch.id == batch_id))
    original = result.scalar_one_or_none()

    if not original:
        raise HTTPException(status_code=404, detail="Dávka nenalezena")

    # Vytvořit nový batch (bez freeze dat)
    new_batch = Batch(
        part_id=original.part_id,
        quantity=original.quantity,
        is_default=False,  # Klony nejsou default
        # Náklady zkopírujeme (budou přepočítány při dalším update)
        unit_time_min=original.unit_time_min,
        material_cost=original.material_cost,
        machining_cost=original.machining_cost,
        setup_cost=original.setup_cost,
        coop_cost=original.coop_cost,
        unit_cost=original.unit_cost,
        total_cost=original.total_cost,
        # Freeze fields zůstanou default (False, None)
    )

    set_audit(new_batch, current_user.username)
    db.add(new_batch)

    try:
        await db.commit()
        await db.refresh(new_batch)
        logger.info(
            f"Cloned batch {batch_id} -> {new_batch.id}: quantity={new_batch.quantity}",
            extra={"original_id": batch_id, "new_id": new_batch.id, "user": current_user.username}
        )
        return new_batch
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error cloning batch {batch_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při klonování dávky")
