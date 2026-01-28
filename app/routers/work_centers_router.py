"""GESTIMA - Work Centers API router (ADR-021)"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.db_helpers import set_audit, safe_commit
from app.dependencies import get_current_user, require_role
from app.models import User, UserRole
from app.models.enums import WorkCenterType
from app.models.work_center import (
    WorkCenter,
    WorkCenterCreate,
    WorkCenterUpdate,
    WorkCenterResponse
)
from app.services.number_generator import NumberGenerator

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[WorkCenterResponse])
async def get_work_centers(
    work_center_type: Optional[WorkCenterType] = Query(None, description="Filtr podle typu"),
    include_inactive: bool = Query(False, description="Zahrnout neaktivní pracoviště"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Seznam všech pracovišť"""
    query = select(WorkCenter)

    if not include_inactive:
        query = query.where(WorkCenter.is_active == True)

    if work_center_type:
        query = query.where(WorkCenter.work_center_type == work_center_type)

    query = query.order_by(WorkCenter.priority.asc(), WorkCenter.name.asc())

    result = await db.execute(query)
    work_centers = result.scalars().all()

    return [WorkCenterResponse.from_orm(wc) for wc in work_centers]


@router.get("/search")
async def search_work_centers(
    search: str = Query("", description="Hledat v čísle, názvu"),
    work_center_type: Optional[WorkCenterType] = Query(None, description="Filtr podle typu"),
    include_inactive: bool = Query(False, description="Zahrnout neaktivní"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Filtrování pracovišť s multi-field search"""
    query = select(WorkCenter)

    if not include_inactive:
        query = query.where(WorkCenter.is_active == True)

    if work_center_type:
        query = query.where(WorkCenter.work_center_type == work_center_type)

    if search.strip():
        search_term = f"%{search.strip()}%"
        filters = [
            WorkCenter.work_center_number.ilike(search_term),
            WorkCenter.name.ilike(search_term),
        ]

        # Pokud je search digit, přidat ID search
        if search.strip().isdigit():
            filters.append(WorkCenter.id == int(search.strip()))

        query = query.where(or_(*filters))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = query.order_by(WorkCenter.priority.asc(), WorkCenter.name.asc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    work_centers = result.scalars().all()

    return {
        "work_centers": [WorkCenterResponse.from_orm(wc) for wc in work_centers],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/types")
async def get_work_center_types(
    current_user: User = Depends(get_current_user)
):
    """Seznam všech typů pracovišť"""
    return [
        {"value": t.value, "name": t.name}
        for t in WorkCenterType
    ]


@router.get("/{work_center_number}", response_model=WorkCenterResponse)
async def get_work_center(
    work_center_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Detail pracoviště podle čísla"""
    result = await db.execute(
        select(WorkCenter).where(WorkCenter.work_center_number == work_center_number)
    )
    work_center = result.scalar_one_or_none()
    if not work_center:
        raise HTTPException(status_code=404, detail="Pracoviště nenalezeno")

    return WorkCenterResponse.from_orm(work_center)


@router.post("/", response_model=WorkCenterResponse)
async def create_work_center(
    data: WorkCenterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """Vytvoření nového pracoviště"""
    # Generate sequential number if not provided
    if data.work_center_number:
        # Check for duplicate number
        result = await db.execute(
            select(WorkCenter).where(WorkCenter.work_center_number == data.work_center_number)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Pracoviště s číslem '{data.work_center_number}' již existuje"
            )
        work_center_number = data.work_center_number
    else:
        work_center_number = await NumberGenerator.generate_work_center_number(db)

    # Create work center
    work_center_data = data.model_dump(exclude={'work_center_number'})
    work_center = WorkCenter(
        work_center_number=work_center_number,
        **work_center_data
    )
    set_audit(work_center, current_user.username)
    db.add(work_center)

    work_center = await safe_commit(
        db, work_center,
        "vytváření pracoviště",
        "Konflikt dat (duplicitní záznam)"
    )

    logger.info(
        f"Created work center: {work_center.name} ({work_center.work_center_number})",
        extra={"work_center_id": work_center.id, "user": current_user.username}
    )
    return WorkCenterResponse.from_orm(work_center)


@router.put("/{work_center_number}", response_model=WorkCenterResponse)
async def update_work_center(
    work_center_number: str,
    data: WorkCenterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """Aktualizace pracoviště"""
    result = await db.execute(
        select(WorkCenter).where(WorkCenter.work_center_number == work_center_number)
    )
    work_center = result.scalar_one_or_none()
    if not work_center:
        raise HTTPException(status_code=404, detail="Pracoviště nenalezeno")

    # Optimistic locking check (ADR-008)
    if work_center.version != data.version:
        logger.warning(
            f"Version conflict updating work center {work_center_number}: "
            f"expected {data.version}, got {work_center.version}",
            extra={"work_center_number": work_center_number, "user": current_user.username}
        )
        raise HTTPException(
            status_code=409,
            detail="Data byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu."
        )

    # Update fields (exclude version - auto-incremented by event listener)
    for key, value in data.model_dump(exclude_unset=True, exclude={'version'}).items():
        setattr(work_center, key, value)

    set_audit(work_center, current_user.username, is_update=True)

    work_center = await safe_commit(
        db, work_center,
        "aktualizace pracoviště",
        "Konflikt dat (duplicitní záznam)"
    )

    logger.info(
        f"Updated work center: {work_center.name} ({work_center.work_center_number})",
        extra={"work_center_id": work_center.id, "user": current_user.username}
    )
    return WorkCenterResponse.from_orm(work_center)


@router.delete("/{work_center_number}", status_code=204)
async def delete_work_center(
    work_center_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Smazání pracoviště (pouze admin)"""
    result = await db.execute(
        select(WorkCenter).where(WorkCenter.work_center_number == work_center_number)
    )
    work_center = result.scalar_one_or_none()
    if not work_center:
        raise HTTPException(status_code=404, detail="Pracoviště nenalezeno")

    work_center_name = work_center.name
    await db.delete(work_center)

    await safe_commit(
        db,
        action="mazání pracoviště",
        integrity_error_msg="Nelze smazat pracoviště - existují závislé záznamy"
    )

    logger.info(
        f"Deleted work center: {work_center_name} ({work_center_number})",
        extra={"work_center_number": work_center_number, "user": current_user.username}
    )
    return {"message": "Pracoviště smazáno"}
