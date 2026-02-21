"""GESTIMA - Features API router

Refactored to use FeatureService (BaseCrudService pattern).
Locked field validation handled by FeatureService._validate_update().
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import User, UserRole
from app.models.feature import FeatureCreate, FeatureUpdate, FeatureResponse
from app.services.feature_service import FeatureService

router = APIRouter()


@router.get("/operation/{operation_id}", response_model=List[FeatureResponse])
async def get_features(
    operation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = FeatureService(db)
    return await service.list_active(parent_id=operation_id)


@router.get("/{feature_id}", response_model=FeatureResponse)
async def get_feature(
    feature_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = FeatureService(db)
    record = await service.get(feature_id)
    if not record:
        raise HTTPException(status_code=404, detail="Krok nenalezen")
    return record


@router.post("/", response_model=FeatureResponse)
async def create_feature(
    data: FeatureCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR])),
):
    service = FeatureService(db)
    return await service.create(data, current_user.username)


@router.put("/{feature_id}", response_model=FeatureResponse)
async def update_feature(
    feature_id: int,
    data: FeatureUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR])),
):
    service = FeatureService(db)
    try:
        return await service.update(feature_id, data, current_user.username)
    except ValueError as exc:
        msg = str(exc)
        if "nenalezen" in msg:
            raise HTTPException(status_code=404, detail=msg)
        if "změněna jiným" in msg:
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


@router.delete("/{feature_id}", status_code=204)
async def delete_feature(
    feature_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    service = FeatureService(db)
    deleted = await service.hard_delete(feature_id, current_user.username)
    if not deleted:
        raise HTTPException(status_code=404, detail="Krok nenalezen")
