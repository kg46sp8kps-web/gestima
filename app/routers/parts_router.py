"""GESTIMA - Parts API router"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.part import Part, PartCreate, PartUpdate, PartResponse

router = APIRouter()


@router.get("/", response_model=List[PartResponse])
async def get_parts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Part).order_by(Part.updated_at.desc()))
    return result.scalars().all()


@router.get("/{part_id}", response_model=PartResponse)
async def get_part(part_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Part).where(Part.id == part_id))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")
    return part


@router.post("/", response_model=PartResponse)
async def create_part(data: PartCreate, db: AsyncSession = Depends(get_db)):
    part = Part(**data.model_dump())
    db.add(part)
    await db.commit()
    await db.refresh(part)
    return part


@router.put("/{part_id}", response_model=PartResponse)
async def update_part(part_id: int, data: PartUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Part).where(Part.id == part_id))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")
    
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(part, key, value)
    
    await db.commit()
    await db.refresh(part)
    return part


@router.delete("/{part_id}")
async def delete_part(part_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Part).where(Part.id == part_id))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")
    
    await db.delete(part)
    await db.commit()
    return {"message": "Díl smazán"}
