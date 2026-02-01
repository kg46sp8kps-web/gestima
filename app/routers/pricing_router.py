"""GESTIMA - Pricing API router (ADR-022: BatchSets)

Manages BatchSets - groups of Batches for pricing.
Standalone module prepared for Workspace integration (ADR-023).
"""

import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database import get_db
from app.db_helpers import set_audit, safe_commit
from app.dependencies import get_current_user, require_role
from app.models import User, UserRole
from app.models.batch import Batch, BatchCreate, BatchResponse
from app.models.batch_set import (
    BatchSet,
    BatchSetCreate,
    BatchSetUpdate,
    BatchSetResponse,
    BatchSetWithBatchesResponse,
    BatchSetListResponse,
    generate_batch_set_name
)
from app.models.part import Part
from app.models.material import MaterialItem
from app.models.material_input import MaterialInput
from app.services.snapshot_service import create_batch_snapshot
from app.services.batch_service import recalculate_batch_costs
from app.services.number_generator import NumberGenerator, NumberGenerationError

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# BatchSet CRUD
# =============================================================================

@router.get("/batch-sets", response_model=List[BatchSetListResponse])
async def list_all_batch_sets(
    status: Optional[str] = Query(None, description="Filter by status (draft|frozen)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all batch sets (for standalone module view)."""
    query = select(BatchSet).where(BatchSet.deleted_at.is_(None))

    if status:
        query = query.where(BatchSet.status == status)

    query = query.order_by(BatchSet.created_at.desc())

    result = await db.execute(query)
    batch_sets = result.scalars().all()

    # Add batch_count for each set
    response = []
    for bs in batch_sets:
        count_result = await db.execute(
            select(func.count(Batch.id)).where(
                Batch.batch_set_id == bs.id,
                Batch.deleted_at.is_(None)
            )
        )
        batch_count = count_result.scalar() or 0

        response.append(BatchSetListResponse(
            id=bs.id,
            set_number=bs.set_number,
            part_id=bs.part_id,
            name=bs.name,
            status=bs.status,
            frozen_at=bs.frozen_at,
            created_at=bs.created_at,
            version=bs.version,
            batch_count=batch_count
        ))

    return response


@router.get("/part/{part_id}/batch-sets", response_model=List[BatchSetListResponse])
async def list_batch_sets_for_part(
    part_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all batch sets for a specific part."""
    query = select(BatchSet).where(
        BatchSet.part_id == part_id,
        BatchSet.deleted_at.is_(None)
    ).order_by(BatchSet.created_at.desc())

    result = await db.execute(query)
    batch_sets = result.scalars().all()

    # Add batch_count for each set
    response = []
    for bs in batch_sets:
        count_result = await db.execute(
            select(func.count(Batch.id)).where(
                Batch.batch_set_id == bs.id,
                Batch.deleted_at.is_(None)
            )
        )
        batch_count = count_result.scalar() or 0

        response.append(BatchSetListResponse(
            id=bs.id,
            set_number=bs.set_number,
            part_id=bs.part_id,
            name=bs.name,
            status=bs.status,
            frozen_at=bs.frozen_at,
            created_at=bs.created_at,
            version=bs.version,
            batch_count=batch_count
        ))

    return response


@router.get("/batch-sets/{set_id}", response_model=BatchSetWithBatchesResponse)
async def get_batch_set(
    set_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get batch set with all its batches."""
    query = select(BatchSet).where(
        BatchSet.id == set_id,
        BatchSet.deleted_at.is_(None)
    ).options(selectinload(BatchSet.batches))

    result = await db.execute(query)
    batch_set = result.scalar_one_or_none()

    if not batch_set:
        raise HTTPException(status_code=404, detail="Sada nenalezena")

    # Filter out deleted batches
    active_batches = [b for b in batch_set.batches if b.deleted_at is None]

    return BatchSetWithBatchesResponse(
        id=batch_set.id,
        set_number=batch_set.set_number,
        part_id=batch_set.part_id,
        name=batch_set.name,
        status=batch_set.status,
        frozen_at=batch_set.frozen_at,
        frozen_by_id=batch_set.frozen_by_id,
        created_at=batch_set.created_at,
        updated_at=batch_set.updated_at,
        version=batch_set.version,
        batches=[BatchResponse.model_validate(b) for b in sorted(active_batches, key=lambda x: x.quantity)]
    )


@router.post("/batch-sets", response_model=BatchSetResponse)
async def create_batch_set(
    data: BatchSetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """Create new empty batch set for a part."""
    # Verify part exists
    result = await db.execute(select(Part).where(Part.id == data.part_id))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")

    # Generate set_number
    try:
        set_number = await NumberGenerator.generate_batch_set_number(db)
    except NumberGenerationError as e:
        logger.error(f"Failed to generate batch set number: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Nepodařilo se vygenerovat číslo sady.")

    # Create batch set with auto-generated name
    batch_set = BatchSet(
        set_number=set_number,
        part_id=data.part_id,
        name=generate_batch_set_name(),
        status="draft"
    )
    set_audit(batch_set, current_user.username)
    db.add(batch_set)

    batch_set = await safe_commit(db, batch_set, "vytváření sady")
    logger.info(
        f"Created batch set: {batch_set.set_number} for part {data.part_id}",
        extra={"batch_set_id": batch_set.id, "part_id": data.part_id, "user": current_user.username}
    )
    return batch_set


@router.put("/batch-sets/{set_id}", response_model=BatchSetResponse)
async def update_batch_set(
    set_id: int,
    data: BatchSetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """Update batch set (only name can be changed)."""
    result = await db.execute(select(BatchSet).where(BatchSet.id == set_id))
    batch_set = result.scalar_one_or_none()

    if not batch_set:
        raise HTTPException(status_code=404, detail="Sada nenalezena")

    if batch_set.deleted_at:
        raise HTTPException(status_code=410, detail="Sada byla smazána")

    # Optimistic locking check
    if batch_set.version != data.version:
        raise HTTPException(status_code=409, detail="Data byla změněna jiným uživatelem")

    # Only update name if provided
    if data.name is not None:
        batch_set.name = data.name

    batch_set.updated_by = current_user.username
    batch_set.updated_at = datetime.utcnow()

    return await safe_commit(db, batch_set, "aktualizace sady")


@router.delete("/batch-sets/{set_id}", status_code=204)
async def delete_batch_set(
    set_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))  # ADMIN only!
):
    """Soft delete batch set and all its batches (ADMIN only)."""
    result = await db.execute(
        select(BatchSet).where(BatchSet.id == set_id).options(selectinload(BatchSet.batches))
    )
    batch_set = result.scalar_one_or_none()

    if not batch_set:
        raise HTTPException(status_code=404, detail="Sada nenalezena")

    if batch_set.deleted_at:
        raise HTTPException(status_code=410, detail="Sada již byla smazána")

    now = datetime.utcnow()

    # Soft delete the set
    batch_set.deleted_at = now
    batch_set.deleted_by = current_user.username

    # Soft delete all batches in the set
    for batch in batch_set.batches:
        if batch.deleted_at is None:
            batch.deleted_at = now
            batch.deleted_by = current_user.username

    await safe_commit(db, action="soft delete sady")
    logger.info(
        f"Soft deleted batch set {set_id} with {len(batch_set.batches)} batches",
        extra={"batch_set_id": set_id, "user": current_user.username}
    )


# =============================================================================
# BatchSet Operations
# =============================================================================

@router.post("/batch-sets/{set_id}/freeze", response_model=BatchSetWithBatchesResponse)
async def freeze_batch_set(
    set_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """
    Freeze entire batch set atomically.

    All batches in the set get frozen with their current prices snapshotted.
    Once frozen, the set and its batches cannot be modified.
    """
    # Load batch set with batches and related data for snapshot
    query = select(BatchSet).where(
        BatchSet.id == set_id,
        BatchSet.deleted_at.is_(None)
    ).options(
        selectinload(BatchSet.batches).selectinload(Batch.part).selectinload(Part.material_inputs).selectinload(MaterialInput.material_item).selectinload(MaterialItem.group),
        selectinload(BatchSet.batches).selectinload(Batch.part).selectinload(Part.material_inputs).selectinload(MaterialInput.price_category)
    )
    result = await db.execute(query)
    batch_set = result.scalar_one_or_none()

    if not batch_set:
        raise HTTPException(status_code=404, detail="Sada nenalezena")

    if batch_set.status == "frozen":
        raise HTTPException(status_code=409, detail="Sada je již zmrazena")

    # Filter active batches
    active_batches = [b for b in batch_set.batches if b.deleted_at is None]

    if len(active_batches) == 0:
        raise HTTPException(status_code=400, detail="Nelze zmrazit prázdnou sadu")

    now = datetime.utcnow()

    try:
        # Atomically freeze all batches
        for batch in active_batches:
            snapshot = await create_batch_snapshot(batch, current_user.username, db)
            batch.is_frozen = True
            batch.frozen_at = now
            batch.frozen_by_id = current_user.id
            batch.snapshot_data = snapshot
            batch.unit_price_frozen = batch.unit_cost
            batch.total_price_frozen = batch.total_cost

        # Freeze the set itself
        batch_set.status = "frozen"
        batch_set.frozen_at = now
        batch_set.frozen_by_id = current_user.id
        batch_set.updated_by = current_user.username
        batch_set.updated_at = now

        await safe_commit(db, batch_set, "zmrazení sady")

        logger.info(
            f"Frozen batch set {set_id} with {len(active_batches)} batches",
            extra={"batch_set_id": set_id, "user": current_user.username}
        )

        return BatchSetWithBatchesResponse(
            id=batch_set.id,
            set_number=batch_set.set_number,
            part_id=batch_set.part_id,
            name=batch_set.name,
            status=batch_set.status,
            frozen_at=batch_set.frozen_at,
            frozen_by_id=batch_set.frozen_by_id,
            created_at=batch_set.created_at,
            updated_at=batch_set.updated_at,
            version=batch_set.version,
            batches=[BatchResponse.model_validate(b) for b in sorted(active_batches, key=lambda x: x.quantity)]
        )
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error freezing batch set {set_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při zmrazování sady")


@router.post("/batch-sets/{set_id}/recalculate", response_model=BatchSetWithBatchesResponse)
async def recalculate_batch_set(
    set_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """
    Recalculate all batches in the set.

    Useful after material price changes, operation updates, or work center rate changes.
    Cannot recalculate frozen sets.
    """
    result = await db.execute(
        select(BatchSet).where(BatchSet.id == set_id).options(selectinload(BatchSet.batches))
    )
    batch_set = result.scalar_one_or_none()

    if not batch_set:
        raise HTTPException(status_code=404, detail="Sada nenalezena")

    if batch_set.deleted_at:
        raise HTTPException(status_code=410, detail="Sada byla smazána")

    if batch_set.status == "frozen":
        raise HTTPException(status_code=409, detail="Nelze přepočítat zmrazenou sadu")

    active_batches = [b for b in batch_set.batches if b.deleted_at is None]

    try:
        for batch in active_batches:
            await recalculate_batch_costs(batch, db)

        batch_set.updated_by = current_user.username
        batch_set.updated_at = datetime.utcnow()

        await safe_commit(db, batch_set, "přepočet sady")

        logger.info(
            f"Recalculated batch set {set_id} with {len(active_batches)} batches",
            extra={"batch_set_id": set_id, "user": current_user.username}
        )

        return BatchSetWithBatchesResponse(
            id=batch_set.id,
            set_number=batch_set.set_number,
            part_id=batch_set.part_id,
            name=batch_set.name,
            status=batch_set.status,
            frozen_at=batch_set.frozen_at,
            frozen_by_id=batch_set.frozen_by_id,
            created_at=batch_set.created_at,
            updated_at=batch_set.updated_at,
            version=batch_set.version,
            batches=[BatchResponse.model_validate(b) for b in sorted(active_batches, key=lambda x: x.quantity)]
        )
    except ValueError as e:
        await db.rollback()
        logger.error(f"Validation error recalculating batch set {set_id}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error recalculating batch set {set_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze")


@router.post("/batch-sets/{set_id}/clone", response_model=BatchSetResponse)
async def clone_batch_set(
    set_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """
    Clone a batch set (creates new draft set with same batches).

    Useful for creating new pricing variations from frozen sets.
    """
    result = await db.execute(
        select(BatchSet).where(BatchSet.id == set_id).options(selectinload(BatchSet.batches))
    )
    original = result.scalar_one_or_none()

    if not original:
        raise HTTPException(status_code=404, detail="Sada nenalezena")

    # Generate new set_number
    try:
        set_number = await NumberGenerator.generate_batch_set_number(db)
    except NumberGenerationError as e:
        logger.error(f"Failed to generate batch set number for clone: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Nepodařilo se vygenerovat číslo sady.")

    # Create new batch set
    new_set = BatchSet(
        set_number=set_number,
        part_id=original.part_id,
        name=generate_batch_set_name(),  # New timestamp
        status="draft"
    )
    set_audit(new_set, current_user.username)
    db.add(new_set)

    # Flush to get the new set ID
    await db.flush()

    # Clone all active batches
    active_batches = [b for b in original.batches if b.deleted_at is None]
    for batch in active_batches:
        try:
            batch_number = await NumberGenerator.generate_batch_number(db)
        except NumberGenerationError as e:
            await db.rollback()
            logger.error(f"Failed to generate batch number for clone: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Nepodařilo se vygenerovat číslo šarže.")

        new_batch = Batch(
            batch_number=batch_number,
            part_id=batch.part_id,
            batch_set_id=new_set.id,
            quantity=batch.quantity,
            is_default=False,
            unit_time_min=batch.unit_time_min,
            material_cost=batch.material_cost,
            machining_cost=batch.machining_cost,
            setup_cost=batch.setup_cost,
            overhead_cost=batch.overhead_cost,
            margin_cost=batch.margin_cost,
            coop_cost=batch.coop_cost,
            unit_cost=batch.unit_cost,
            total_cost=batch.total_cost,
            material_weight_kg=batch.material_weight_kg,
            material_price_per_kg=batch.material_price_per_kg,
            # NOT frozen
        )
        set_audit(new_batch, current_user.username)
        db.add(new_batch)

    new_set = await safe_commit(db, new_set, "klonování sady")

    logger.info(
        f"Cloned batch set {set_id} -> {new_set.id} with {len(active_batches)} batches",
        extra={"original_id": set_id, "new_id": new_set.id, "user": current_user.username}
    )
    return new_set


# =============================================================================
# Batch Operations within BatchSet
# =============================================================================

@router.post("/batch-sets/{set_id}/batches", response_model=BatchResponse)
async def add_batch_to_set(
    set_id: int,
    quantity: int = Query(..., gt=0, description="Množství kusů"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """Add a new batch to a batch set."""
    result = await db.execute(select(BatchSet).where(BatchSet.id == set_id))
    batch_set = result.scalar_one_or_none()

    if not batch_set:
        raise HTTPException(status_code=404, detail="Sada nenalezena")

    if batch_set.deleted_at:
        raise HTTPException(status_code=410, detail="Sada byla smazána")

    if batch_set.status == "frozen":
        raise HTTPException(status_code=409, detail="Nelze přidávat do zmrazené sady")

    if not batch_set.part_id:
        raise HTTPException(status_code=400, detail="Sada nemá přiřazený díl")

    # Generate batch_number
    try:
        batch_number = await NumberGenerator.generate_batch_number(db)
    except NumberGenerationError as e:
        logger.error(f"Failed to generate batch number: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Nepodařilo se vygenerovat číslo šarže.")

    # Create batch
    batch = Batch(
        batch_number=batch_number,
        part_id=batch_set.part_id,
        batch_set_id=set_id,
        quantity=quantity,
        is_default=False
    )
    set_audit(batch, current_user.username)
    db.add(batch)

    try:
        # Auto-calculate costs
        await recalculate_batch_costs(batch, db)
    except ValueError as e:
        await db.rollback()
        logger.error(f"Validation error adding batch: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

    batch = await safe_commit(db, batch, "přidání batche do sady")

    logger.info(
        f"Added batch to set {set_id}: quantity={quantity}, unit_cost={batch.unit_cost}",
        extra={"batch_set_id": set_id, "batch_id": batch.id, "user": current_user.username}
    )
    return batch


@router.delete("/batch-sets/{set_id}/batches/{batch_id}", status_code=204)
async def remove_batch_from_set(
    set_id: int,
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """Remove a batch from a batch set."""
    result = await db.execute(select(BatchSet).where(BatchSet.id == set_id))
    batch_set = result.scalar_one_or_none()

    if not batch_set:
        raise HTTPException(status_code=404, detail="Sada nenalezena")

    if batch_set.status == "frozen":
        raise HTTPException(status_code=409, detail="Nelze mazat ze zmrazené sady")

    result = await db.execute(
        select(Batch).where(Batch.id == batch_id, Batch.batch_set_id == set_id)
    )
    batch = result.scalar_one_or_none()

    if not batch:
        raise HTTPException(status_code=404, detail="Dávka nenalezena v této sadě")

    # Hard delete for non-frozen batches
    await db.delete(batch)

    await safe_commit(db, action="odebrání batche ze sady")
    logger.info(
        f"Removed batch {batch_id} from set {set_id}",
        extra={"batch_set_id": set_id, "batch_id": batch_id, "user": current_user.username}
    )


# =============================================================================
# Freeze ALL Loose Batches Workflow
# =============================================================================

@router.post("/parts/{part_id}/freeze-batches-as-set", response_model=BatchSetWithBatchesResponse)
async def freeze_loose_batches_as_set(
    part_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """
    Freeze all loose batches (batch_set_id IS NULL) for a part into a new BatchSet.

    Workflow:
    1. Find all batches where part_id=X AND batch_set_id IS NULL
    2. Create new BatchSet with auto-generated name
    3. Assign all loose batches to the new set
    4. Freeze the set + all batches atomically
    5. Return the created set with batches
    """
    # Verify part exists
    result = await db.execute(select(Part).where(Part.id == part_id))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")

    # Find all loose batches for this part (with eager loading for snapshot)
    query = select(Batch).where(
        Batch.part_id == part_id,
        Batch.batch_set_id.is_(None),
        Batch.deleted_at.is_(None)
    ).options(
        selectinload(Batch.part).selectinload(Part.material_inputs).selectinload(MaterialInput.material_item).selectinload(MaterialItem.group),
        selectinload(Batch.part).selectinload(Part.material_inputs).selectinload(MaterialInput.price_category),
        selectinload(Batch.part).selectinload(Part.material_inputs)
    )
    result = await db.execute(query)
    loose_batches = result.scalars().all()

    if len(loose_batches) == 0:
        raise HTTPException(status_code=400, detail="Žádné volné šarže k zmrazení")

    # Generate set_number
    try:
        set_number = await NumberGenerator.generate_batch_set_number(db)
    except NumberGenerationError as e:
        logger.error(f"Failed to generate batch set number: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Nepodařilo se vygenerovat číslo sady.")

    # Create BatchSet
    batch_set = BatchSet(
        set_number=set_number,
        part_id=part_id,
        name=generate_batch_set_name(),
        status="frozen"  # Immediately frozen
    )
    set_audit(batch_set, current_user.username)
    db.add(batch_set)

    # Flush to get batch_set.id
    await db.flush()
    await db.refresh(batch_set)

    now = datetime.utcnow()

    try:
        # Assign all loose batches to the set and freeze them
        for batch in loose_batches:
            # Refresh batch to ensure relations are loaded after flush
            await db.refresh(batch, ['part'])
            snapshot = await create_batch_snapshot(batch, current_user.username, db)
            batch.batch_set_id = batch_set.id
            batch.is_frozen = True
            batch.frozen_at = now
            batch.frozen_by_id = current_user.id
            batch.snapshot_data = snapshot
            batch.unit_price_frozen = batch.unit_cost
            batch.total_price_frozen = batch.total_cost

        # Freeze the set
        batch_set.frozen_at = now
        batch_set.frozen_by_id = current_user.id

        await safe_commit(db, batch_set, "zmrazení volných batchí do sady")

        logger.info(
            f"Froze {len(loose_batches)} loose batches into new set {batch_set.set_number}",
            extra={"batch_set_id": batch_set.id, "part_id": part_id, "batch_count": len(loose_batches), "user": current_user.username}
        )

        return BatchSetWithBatchesResponse(
            id=batch_set.id,
            set_number=batch_set.set_number,
            part_id=batch_set.part_id,
            name=batch_set.name,
            status=batch_set.status,
            frozen_at=batch_set.frozen_at,
            frozen_by_id=batch_set.frozen_by_id,
            created_at=batch_set.created_at,
            updated_at=batch_set.updated_at,
            version=batch_set.version,
            batches=[BatchResponse.model_validate(b) for b in sorted(loose_batches, key=lambda x: x.quantity)]
        )
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error freezing loose batches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při zmrazování")
