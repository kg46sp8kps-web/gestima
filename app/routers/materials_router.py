"""GESTIMA - Materials API router (ADR-011: Material Hierarchy)"""

import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.db_helpers import set_audit
from app.dependencies import get_current_user, require_role
from app.models import User, UserRole
from app.models.material import (
    MaterialGroup,
    MaterialGroupCreate,
    MaterialGroupUpdate,
    MaterialGroupResponse,
    MaterialItem,
    MaterialItemCreate,
    MaterialItemUpdate,
    MaterialItemResponse,
    MaterialItemWithGroupResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ========== MATERIAL GROUPS ==========

@router.get("/groups", response_model=List[MaterialGroupResponse])
async def get_material_groups(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Seznam kategorií materiálů (pro výpočty: hustota, řezné podmínky)"""
    result = await db.execute(select(MaterialGroup).order_by(MaterialGroup.code))
    return result.scalars().all()


@router.get("/groups/{group_id}", response_model=MaterialGroupResponse)
async def get_material_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Detail kategorie materiálu"""
    result = await db.execute(select(MaterialGroup).where(MaterialGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Skupina materiálu nenalezena")
    return group


@router.post("/groups", response_model=MaterialGroupResponse)
async def create_material_group(
    data: MaterialGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Vytvoření nové kategorie materiálu (pouze admin)"""
    group = MaterialGroup(**data.model_dump())
    set_audit(group, current_user.username)
    db.add(group)

    try:
        await db.commit()
        await db.refresh(group)
        logger.info(f"Created material group: {group.code}", extra={"group_id": group.id, "user": current_user.username})
        return group
    except IntegrityError:
        await db.rollback()
        logger.error(f"Duplicate material group code: {data.code}")
        raise HTTPException(status_code=409, detail=f"Skupina s kódem '{data.code}' již existuje")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error creating material group: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při vytváření skupiny materiálu")


@router.put("/groups/{group_id}", response_model=MaterialGroupResponse)
async def update_material_group(
    group_id: int,
    data: MaterialGroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Aktualizace kategorie materiálu (pouze admin)"""
    result = await db.execute(select(MaterialGroup).where(MaterialGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Skupina materiálu nenalezena")

    # Optimistic locking check (ADR-008)
    if group.version != data.version:
        logger.warning(f"Version conflict updating material group {group_id}", extra={"user": current_user.username})
        raise HTTPException(status_code=409, detail="Data byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu.")

    for key, value in data.model_dump(exclude_unset=True, exclude={'version'}).items():
        setattr(group, key, value)

    set_audit(group, current_user.username, is_update=True)

    try:
        await db.commit()
        await db.refresh(group)
        logger.info(f"Updated material group: {group.code}", extra={"group_id": group.id, "user": current_user.username})
        return group
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Konflikt dat (duplicitní kód)")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error updating material group: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při aktualizaci skupiny materiálu")


# ========== MATERIAL ITEMS ==========

@router.get("/items", response_model=List[MaterialItemWithGroupResponse])
async def get_material_items(
    group_id: int = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Seznam polotovarů (filtrovatelné dle skupiny)"""
    query = select(MaterialItem).options(selectinload(MaterialItem.group)).order_by(MaterialItem.code)

    if group_id:
        query = query.where(MaterialItem.material_group_id == group_id)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/items/{item_id}", response_model=MaterialItemWithGroupResponse)
async def get_material_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Detail polotovaru"""
    result = await db.execute(
        select(MaterialItem)
        .options(selectinload(MaterialItem.group))
        .where(MaterialItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Polotovar nenalezen")
    return item


@router.post("/items", response_model=MaterialItemResponse)
async def create_material_item(
    data: MaterialItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Vytvoření nové skladové položky (pouze admin)"""
    # Ověřit existenci material_group
    result = await db.execute(select(MaterialGroup).where(MaterialGroup.id == data.material_group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=400, detail=f"Skupina materiálu s ID {data.material_group_id} neexistuje")

    item = MaterialItem(**data.model_dump())
    set_audit(item, current_user.username)
    db.add(item)

    try:
        await db.commit()
        await db.refresh(item)
        logger.info(f"Created material item: {item.code}", extra={"item_id": item.id, "user": current_user.username})
        return item
    except IntegrityError:
        await db.rollback()
        logger.error(f"Duplicate material item code: {data.code}")
        raise HTTPException(status_code=409, detail=f"Polotovar s kódem '{data.code}' již existuje")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error creating material item: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při vytváření polotovaru")


@router.put("/items/{item_id}", response_model=MaterialItemResponse)
async def update_material_item(
    item_id: int,
    data: MaterialItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """Aktualizace polotovaru (admin nebo operator)"""
    result = await db.execute(select(MaterialItem).where(MaterialItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Polotovar nenalezen")

    # Optimistic locking check (ADR-008)
    if item.version != data.version:
        logger.warning(f"Version conflict updating material item {item_id}", extra={"user": current_user.username})
        raise HTTPException(status_code=409, detail="Data byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu.")

    # Ověřit existenci material_group pokud se mění
    if data.material_group_id and data.material_group_id != item.material_group_id:
        result = await db.execute(select(MaterialGroup).where(MaterialGroup.id == data.material_group_id))
        group = result.scalar_one_or_none()
        if not group:
            raise HTTPException(status_code=400, detail=f"Skupina materiálu s ID {data.material_group_id} neexistuje")

    for key, value in data.model_dump(exclude_unset=True, exclude={'version'}).items():
        setattr(item, key, value)

    set_audit(item, current_user.username, is_update=True)

    try:
        await db.commit()
        await db.refresh(item)
        logger.info(f"Updated material item: {item.code}", extra={"item_id": item.id, "user": current_user.username})
        return item
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Konflikt dat (duplicitní kód)")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error updating material item: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při aktualizaci polotovaru")


@router.delete("/items/{item_id}")
async def delete_material_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Smazání polotovaru (pouze admin) - soft delete"""
    result = await db.execute(select(MaterialItem).where(MaterialItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Polotovar nenalezen")

    # Soft delete (ADR-001)
    item.deleted_at = datetime.utcnow()
    item.deleted_by = current_user.username

    try:
        await db.commit()
        logger.info(f"Deleted material item: {item.code}", extra={"item_id": item.id, "user": current_user.username})
        return {"message": f"Polotovar '{item.code}' byl smazán"}
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error deleting material item: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při mazání polotovaru")
