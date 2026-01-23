"""GESTIMA - Batches API router"""

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
from app.models.batch import Batch, BatchCreate, BatchResponse

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
