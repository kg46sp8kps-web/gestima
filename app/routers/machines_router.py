"""GESTIMA - Machines API router (ADR-015, ADR-016)"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database import get_db
from app.db_helpers import set_audit, safe_commit
from app.dependencies import get_current_user, require_role
from app.models import User, UserRole
from app.models.machine import MachineDB, MachineCreate, MachineUpdate, MachineResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[MachineResponse])
async def get_machines(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Seznam všech strojů"""
    result = await db.execute(
        select(MachineDB)
        .where(MachineDB.active == True)
        .order_by(MachineDB.priority.asc(), MachineDB.name.asc())
    )
    machines = result.scalars().all()

    # Use custom from_orm to include computed fields
    return [MachineResponse.from_orm(m) for m in machines]


@router.get("/search")
async def search_machines(
    search: str = Query("", description="Hledat v kódu, názvu"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Filtrování strojů s multi-field search"""
    query = select(MachineDB).where(MachineDB.active == True)

    if search.strip():
        search_term = f"%{search.strip()}%"
        filters = [
            MachineDB.code.ilike(search_term),
            MachineDB.name.ilike(search_term),
            MachineDB.type.ilike(search_term)
        ]

        # Pokud je search digit, přidat ID search
        if search.strip().isdigit():
            filters.append(MachineDB.id == int(search.strip()))

        query = query.where(or_(*filters))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = query.order_by(MachineDB.priority.asc()).offset(skip).limit(limit)
    result = await db.execute(query)
    machines = result.scalars().all()

    # Convert to response models with computed fields
    machines_response = [MachineResponse.from_orm(m) for m in machines]

    return {
        "machines": machines_response,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{machine_id}", response_model=MachineResponse)
async def get_machine(
    machine_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Detail stroje"""
    result = await db.execute(
        select(MachineDB).where(MachineDB.id == machine_id)
    )
    machine = result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Stroj nenalezen")

    return MachineResponse.from_orm(machine)


@router.post("/", response_model=MachineResponse)
async def create_machine(
    data: MachineCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """Vytvoření nového stroje"""
    # Kontrola duplicitního kódu
    result = await db.execute(select(MachineDB).where(MachineDB.code == data.code))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"Stroj s kódem '{data.code}' již existuje")

    machine = MachineDB(**data.model_dump())
    set_audit(machine, current_user.username)
    db.add(machine)

    machine = await safe_commit(db, machine, "vytváření stroje", "Konflikt dat (duplicitní záznam)")

    # Clear cache after successful create
    from app.services.reference_loader import clear_cache
    clear_cache()

    logger.info(f"Created machine: {machine.code}", extra={"machine_id": machine.id, "user": current_user.username})
    return MachineResponse.from_orm(machine)


@router.put("/{machine_id}", response_model=MachineResponse)
async def update_machine(
    machine_id: int,
    data: MachineUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """Aktualizace stroje"""
    result = await db.execute(select(MachineDB).where(MachineDB.id == machine_id))
    machine = result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Stroj nenalezen")

    # Optimistic locking check (ADR-008)
    if machine.version != data.version:
        logger.warning(
            f"Version conflict updating machine {machine_id}: expected {data.version}, got {machine.version}",
            extra={"machine_id": machine_id, "user": current_user.username}
        )
        raise HTTPException(status_code=409, detail="Data byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu.")

    # Update fields (exclude version - it's auto-incremented by event listener)
    for key, value in data.model_dump(exclude_unset=True, exclude={'version'}).items():
        setattr(machine, key, value)

    set_audit(machine, current_user.username, is_update=True)

    machine = await safe_commit(db, machine, "aktualizace stroje", "Konflikt dat (duplicitní záznam)")

    # Clear cache after successful update
    from app.services.reference_loader import clear_cache
    clear_cache()

    logger.info(f"Updated machine: {machine.code}", extra={"machine_id": machine.id, "user": current_user.username})
    return MachineResponse.from_orm(machine)


@router.delete("/{machine_id}", status_code=204)
async def delete_machine(
    machine_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Smazání stroje (pouze admin)"""
    result = await db.execute(select(MachineDB).where(MachineDB.id == machine_id))
    machine = result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Stroj nenalezen")

    machine_code = machine.code
    await db.delete(machine)

    await safe_commit(db, action="mazání stroje", integrity_error_msg="Nelze smazat stroj - existují závislé záznamy (operace používají tento stroj)")

    # Clear cache after successful delete
    from app.services.reference_loader import clear_cache
    clear_cache()

    logger.info(f"Deleted machine: {machine_code}", extra={"machine_id": machine_id, "user": current_user.username})
    return {"message": "Stroj smazán"}
