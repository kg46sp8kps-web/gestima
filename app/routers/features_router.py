"""GESTIMA - Features API router"""

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
from app.models.feature import Feature, FeatureCreate, FeatureUpdate, FeatureResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/operation/{operation_id}", response_model=List[FeatureResponse])
async def get_features(
    operation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Feature)
        .where(Feature.operation_id == operation_id, Feature.deleted_at.is_(None))
        .order_by(Feature.seq)
    )
    return result.scalars().all()


@router.get("/{feature_id}", response_model=FeatureResponse)
async def get_feature(
    feature_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Feature).where(Feature.id == feature_id))
    feature = result.scalar_one_or_none()
    if not feature:
        raise HTTPException(status_code=404, detail="Krok nenalezen")
    return feature


@router.post("/", response_model=FeatureResponse)
async def create_feature(
    data: FeatureCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    feature = Feature(**data.model_dump())
    set_audit(feature, current_user.username)
    db.add(feature)

    try:
        await db.commit()
        await db.refresh(feature)
        logger.info(f"Created feature: {feature.feature_type}", extra={"feature_id": feature.id, "operation_id": feature.operation_id, "user": current_user.username})
        return feature
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Integrity error creating feature: {e}", exc_info=True)
        raise HTTPException(status_code=409, detail="Konflikt dat (neplatná reference na operaci)")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error creating feature: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při vytváření kroku")


@router.put("/{feature_id}", response_model=FeatureResponse)
async def update_feature(
    feature_id: int,
    data: FeatureUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    result = await db.execute(select(Feature).where(Feature.id == feature_id))
    feature = result.scalar_one_or_none()
    if not feature:
        raise HTTPException(status_code=404, detail="Krok nenalezen")

    # Optimistic locking check (ADR-008)
    if feature.version != data.version:
        logger.warning(f"Version conflict updating feature {feature_id}: expected {data.version}, got {feature.version}", extra={"feature_id": feature_id, "user": current_user.username})
        raise HTTPException(status_code=409, detail="Data byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu.")

    # Update fields (exclude version - it's auto-incremented by event listener)
    for key, value in data.model_dump(exclude_unset=True, exclude={'version'}).items():
        setattr(feature, key, value)

    set_audit(feature, current_user.username, is_update=True)

    try:
        await db.commit()
        await db.refresh(feature)
        logger.info(f"Updated feature: {feature.feature_type}", extra={"feature_id": feature.id, "user": current_user.username})
        return feature
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error updating feature {feature_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při aktualizaci kroku")


@router.delete("/{feature_id}", status_code=204)
async def delete_feature(
    feature_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    result = await db.execute(select(Feature).where(Feature.id == feature_id))
    feature = result.scalar_one_or_none()
    if not feature:
        raise HTTPException(status_code=404, detail="Krok nenalezen")

    feature_type = feature.feature_type
    await db.delete(feature)

    try:
        await db.commit()
        logger.info(f"Deleted feature: {feature_type}", extra={"feature_id": feature_id, "user": current_user.username})
        return {"message": "Krok smazán"}
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error deleting feature {feature_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při mazání kroku")
