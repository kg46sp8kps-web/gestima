"""GESTIMA - Features API router"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database import get_db
from app.db_helpers import set_audit, safe_commit
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
    try:
        result = await db.execute(
            select(Feature)
            .where(Feature.operation_id == operation_id, Feature.deleted_at.is_(None))
            .order_by(Feature.seq)
        )
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching features for operation {operation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při načítání kroků")


@router.get("/{feature_id}", response_model=FeatureResponse)
async def get_feature(
    feature_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        result = await db.execute(select(Feature).where(Feature.id == feature_id))
        feature = result.scalar_one_or_none()
        if not feature:
            raise HTTPException(status_code=404, detail="Krok nenalezen")
        return feature
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching feature {feature_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při načítání kroku")


@router.post("/", response_model=FeatureResponse)
async def create_feature(
    data: FeatureCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    feature = Feature(**data.model_dump())
    set_audit(feature, current_user.username)
    db.add(feature)

    feature = await safe_commit(db, feature, "vytváření kroku", "Konflikt dat (neplatná reference na operaci)")
    logger.info(f"Created feature: {feature.feature_type}", extra={"feature_id": feature.id, "operation_id": feature.operation_id, "user": current_user.username})
    return feature


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

    # Locked field validation - nelze měnit zamčené řezné podmínky
    update_data = data.model_dump(exclude_unset=True, exclude={'version'})
    if feature.Vc_locked and 'Vc' in update_data:
        raise HTTPException(status_code=400, detail="Řezná rychlost (Vc) je uzamčena a nelze ji změnit")
    if feature.f_locked and 'f' in update_data:
        raise HTTPException(status_code=400, detail="Posuv (f) je uzamčen a nelze jej změnit")
    if feature.Ap_locked and 'Ap' in update_data:
        raise HTTPException(status_code=400, detail="Hloubka řezu (Ap) je uzamčena a nelze ji změnit")

    # Update fields (exclude version - it's auto-incremented by event listener)
    for key, value in update_data.items():
        setattr(feature, key, value)

    set_audit(feature, current_user.username, is_update=True)

    feature = await safe_commit(db, feature, "aktualizace kroku")
    logger.info(f"Updated feature: {feature.feature_type}", extra={"feature_id": feature.id, "user": current_user.username})
    return feature


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

    await safe_commit(db, action="mazání kroku")
    logger.info(f"Deleted feature: {feature_type}", extra={"feature_id": feature_id, "user": current_user.username})
    return  # 204 No Content
