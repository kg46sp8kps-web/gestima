"""GESTIMA - Batches API router"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.batch import Batch, BatchCreate, BatchResponse

router = APIRouter()


@router.get("/part/{part_id}", response_model=List[BatchResponse])
async def get_batches(part_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Batch).where(Batch.part_id == part_id).order_by(Batch.quantity)
    )
    return result.scalars().all()


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch(batch_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Dávka nenalezena")
    return batch


@router.post("/", response_model=BatchResponse)
async def create_batch(data: BatchCreate, db: AsyncSession = Depends(get_db)):
    batch = Batch(**data.model_dump())
    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    return batch


@router.delete("/{batch_id}")
async def delete_batch(batch_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Dávka nenalezena")
    
    await db.delete(batch)
    await db.commit()
    return {"message": "Dávka smazána"}
