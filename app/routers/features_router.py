"""GESTIMA - Features API router"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.feature import Feature, FeatureCreate, FeatureUpdate, FeatureResponse

router = APIRouter()


@router.get("/operation/{operation_id}", response_model=List[FeatureResponse])
async def get_features(operation_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Feature).where(Feature.operation_id == operation_id).order_by(Feature.seq)
    )
    return result.scalars().all()


@router.get("/{feature_id}", response_model=FeatureResponse)
async def get_feature(feature_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Feature).where(Feature.id == feature_id))
    feature = result.scalar_one_or_none()
    if not feature:
        raise HTTPException(status_code=404, detail="Krok nenalezen")
    return feature


@router.post("/", response_model=FeatureResponse)
async def create_feature(data: FeatureCreate, db: AsyncSession = Depends(get_db)):
    feature = Feature(**data.model_dump())
    db.add(feature)
    await db.commit()
    await db.refresh(feature)
    return feature


@router.put("/{feature_id}", response_model=FeatureResponse)
async def update_feature(feature_id: int, data: FeatureUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Feature).where(Feature.id == feature_id))
    feature = result.scalar_one_or_none()
    if not feature:
        raise HTTPException(status_code=404, detail="Krok nenalezen")
    
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(feature, key, value)
    
    await db.commit()
    await db.refresh(feature)
    return feature


@router.delete("/{feature_id}")
async def delete_feature(feature_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Feature).where(Feature.id == feature_id))
    feature = result.scalar_one_or_none()
    if not feature:
        raise HTTPException(status_code=404, detail="Krok nenalezen")
    
    await db.delete(feature)
    await db.commit()
    return {"message": "Krok smazán"}
