"""GESTIMA - Batches API router"""

import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database import get_db
from app.db_helpers import set_audit, safe_commit, soft_delete
from app.dependencies import get_current_user, require_role
from app.models import User, UserRole
from app.models.batch import Batch, BatchCreate, BatchResponse
from app.models.part import Part
from app.models.material import MaterialItem
from app.models.material_input import MaterialInput  # ADR-024
from app.services.snapshot_service import create_batch_snapshot
from app.services.batch_service import recalculate_batch_costs

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/part/{part_id}", response_model=List[BatchResponse])
async def get_batches(
    part_id: int,
    skip: int = Query(0, ge=0, description="Počet záznamů k přeskočení"),
    limit: int = Query(100, ge=1, le=500, description="Max počet záznamů"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Batch)
        .options(selectinload(Batch.part))
        .where(Batch.part_id == part_id, Batch.deleted_at.is_(None))
        .order_by(Batch.quantity)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{batch_number}", response_model=BatchResponse)
async def get_batch(
    batch_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Batch).where(Batch.batch_number == batch_number))
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
    from app.services.number_generator import NumberGenerator, NumberGenerationError

    # Auto-generate batch_number if not provided
    if not data.batch_number:
        try:
            batch_number = await NumberGenerator.generate_batch_number(db)
        except NumberGenerationError as e:
            logger.error(f"Failed to generate batch number: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Nepodařilo se vygenerovat číslo šarže. Zkuste to znovu.")
    else:
        batch_number = data.batch_number
        # Kontrola duplicity (pokud zadáno ručně)
        result = await db.execute(select(Batch).where(Batch.batch_number == batch_number))
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail=f"Šarže s číslem '{batch_number}' již existuje")

    # Create batch with generated/provided number
    batch_data = data.model_dump(exclude={'batch_number'})
    batch = Batch(batch_number=batch_number, **batch_data)
    set_audit(batch, current_user.username)
    db.add(batch)

    try:
        # Auto-calculate costs před commitem
        await recalculate_batch_costs(batch, db)
    except ValueError as e:
        # Chyba z recalculate (Part not found, missing material, atd.)
        await db.rollback()
        logger.error(f"Validation error creating batch: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

    batch = await safe_commit(db, batch, "vytváření dávky", "Konflikt dat (neplatná reference na díl)")
    logger.info(
        f"Created batch: quantity={batch.quantity}, unit_cost={batch.unit_cost} Kč",
        extra={"batch_id": batch.id, "part_id": batch.part_id, "user": current_user.username}
    )
    return batch


@router.delete("/{batch_number}", status_code=204)
async def delete_batch(
    batch_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    result = await db.execute(select(Batch).where(Batch.batch_number == batch_number))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Dávka nenalezena")

    # ADR-012: Frozen batch lze smazat pouze soft delete
    if batch.is_frozen:
        batch.deleted_at = datetime.utcnow()
        batch.deleted_by = current_user.username
        await safe_commit(db, action="soft delete dávky")
        logger.info(f"Soft deleted frozen batch: quantity={batch.quantity}", extra={"batch_number": batch_number, "user": current_user.username})
        return  # 204 No Content

    quantity = batch.quantity
    await soft_delete(db, batch, deleted_by=current_user.username)

    await safe_commit(db, action="mazání dávky")
    logger.info(f"Deleted batch: quantity={quantity}", extra={"batch_number": batch_number, "user": current_user.username})
    return  # 204 No Content


@router.post("/{batch_number}/freeze", response_model=BatchResponse)
async def freeze_batch(
    batch_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """
    Zmrazí ceny batche (ADR-012: Minimal Snapshot).

    Vytvoří snapshot s aktuálními cenami a zmrazí batch (is_frozen=True).
    Zmrazený batch nelze editovat.
    """
    # Načíst batch s part + material_inputs + material_item + group + price_category (eager loading)
    stmt = select(Batch).where(Batch.batch_number == batch_number).options(
        selectinload(Batch.part).selectinload(Part.material_inputs).selectinload(MaterialInput.material_item).selectinload(MaterialItem.group),
        selectinload(Batch.part).selectinload(Part.material_inputs).selectinload(MaterialInput.material_item).selectinload(MaterialItem.price_category)
    )
    result = await db.execute(stmt)
    batch = result.scalar_one_or_none()

    if not batch:
        raise HTTPException(status_code=404, detail="Dávka nenalezena")

    if batch.is_frozen:
        raise HTTPException(status_code=409, detail="Dávka je již zmrazena")

    # Atomická operace: snapshot + freeze metadata + commit
    try:
        # Vytvořit snapshot
        snapshot = await create_batch_snapshot(batch, current_user.username, db)

        # Nastavit freeze metadata
        batch.is_frozen = True
        batch.frozen_at = datetime.utcnow()
        batch.frozen_by_id = current_user.id
        batch.snapshot_data = snapshot
        batch.unit_price_frozen = batch.unit_cost  # Redundantní pro reporty
        batch.total_price_frozen = batch.total_cost

        batch = await safe_commit(db, batch, "zmrazení dávky")
        logger.info(f"Frozen batch: quantity={batch.quantity}", extra={"batch_number": batch_number, "user": current_user.username})
        return batch
    except Exception as e:
        await db.rollback()
        logger.error(f"Freeze batch {batch_number} failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Zmrazení dávky selhalo")


@router.post("/{batch_number}/clone", response_model=BatchResponse)
async def clone_batch(
    batch_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """
    Naklonuje batch (vytvoří nový, nezmrazený batch se stejnými parametry).

    Užitečné když uživatel chce upravit zmrazenou nabídku - naklonuje ji
    a pracuje s novou verzí (která má LIVE ceny).
    """
    from app.services.number_generator import NumberGenerator, NumberGenerationError

    result = await db.execute(select(Batch).where(Batch.batch_number == batch_number))
    original = result.scalar_one_or_none()

    if not original:
        raise HTTPException(status_code=404, detail="Dávka nenalezena")

    original_batch_number = batch_number  # Uložit před přepsáním pro logging

    # Generate new batch_number for clone
    try:
        new_batch_number = await NumberGenerator.generate_batch_number(db)
    except NumberGenerationError as e:
        logger.error(f"Failed to generate batch number for clone: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Nepodařilo se vygenerovat číslo šarže pro klon.")

    # Vytvořit nový batch (bez freeze dat)
    new_batch = Batch(
        batch_number=new_batch_number,
        part_id=original.part_id,
        quantity=original.quantity,
        is_default=False,  # Klony nejsou default
        # Náklady zkopírujeme (budou přepočítány při dalším update)
        unit_time_min=original.unit_time_min,
        material_cost=original.material_cost,
        machining_cost=original.machining_cost,
        setup_cost=original.setup_cost,
        coop_cost=original.coop_cost,
        unit_cost=original.unit_cost,
        total_cost=original.total_cost,
        # Freeze fields zůstanou default (False, None)
    )

    set_audit(new_batch, current_user.username)
    db.add(new_batch)

    new_batch = await safe_commit(db, new_batch, "klonování dávky")
    logger.info(
        f"Cloned batch {original_batch_number} -> {new_batch.batch_number}: quantity={new_batch.quantity}",
        extra={"original_number": original_batch_number, "new_number": new_batch.batch_number, "user": current_user.username}
    )
    return new_batch


@router.post("/{batch_number}/recalculate", response_model=BatchResponse)
async def recalculate_batch(
    batch_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """
    Přepočítá náklady batche podle aktuálních hodnot Part + Operations + Machines.

    Použití:
    - Po změně materiálu Part
    - Po změně/přidání/smazání Operation
    - Po změně machine hourly rates
    - Po změně tp/tj hodnot

    Zamrznutý batch nelze přepočítat (409 Conflict).
    """
    result = await db.execute(select(Batch).where(Batch.batch_number == batch_number))
    batch = result.scalar_one_or_none()

    if not batch:
        raise HTTPException(status_code=404, detail="Dávka nenalezena")

    if batch.is_frozen:
        raise HTTPException(
            status_code=409,
            detail="Zamrznutý batch nelze přepočítat (použij Clone)"
        )

    try:
        # Přepočítat náklady
        await recalculate_batch_costs(batch, db)
    except ValueError as e:
        # Chyba z recalculate (Part not found, missing material, atd.)
        await db.rollback()
        logger.error(f"Validation error recalculating batch {batch_number}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

    batch = await safe_commit(db, batch, "přepočítání dávky")
    logger.info(
        f"Recalculated batch {batch_number}: unit_cost={batch.unit_cost} Kč",
        extra={"batch_number": batch_number, "user": current_user.username}
    )
    return batch


@router.post("/part/{part_id}/recalculate", status_code=204)
async def recalculate_part_batches(
    part_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """
    Bulk přepočítání všech unfrozen batches pro daný part.

    Použití:
    - Po změně materiálu Part (workspace link: materialChanged)
    - Po změně operací (workspace link: operationsChanged)
    - Automaticky voláno z workspace part-pricing modulu
    """
    result = await db.execute(
        select(Batch)
        .where(Batch.part_id == part_id, Batch.is_frozen == False, Batch.deleted_at.is_(None))
        .order_by(Batch.quantity)
    )
    batches = result.scalars().all()

    if not batches:
        # Žádné unfrozen batches - OK
        return

    try:
        for batch in batches:
            await recalculate_batch_costs(batch, db)
    except ValueError as e:
        await db.rollback()
        logger.error(f"Validation error recalculating batches for part {part_id}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

    await safe_commit(db, action="přepočítání dávek")
    logger.info(
        f"Recalculated {len(batches)} batches for part {part_id}",
        extra={"part_id": part_id, "batch_count": len(batches), "user": current_user.username}
    )
