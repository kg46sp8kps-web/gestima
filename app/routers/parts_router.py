"""GESTIMA - Parts API router"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.database import get_db
from app.db_helpers import set_audit, safe_commit
from app.dependencies import get_current_user, require_role
from app.models import User, UserRole
from app.models.part import Part, PartCreate, PartUpdate, PartResponse, PartFullResponse, StockCostResponse
from app.models.material import MaterialItem, MaterialPriceCategory
from app.models.material_input import MaterialInput
from app.models.operation import Operation
from app.models.batch import Batch
from app.models.quote import QuoteItem
from app.services.price_calculator import (
    calculate_stock_cost_from_part,
    calculate_part_price,
    calculate_series_pricing,
    PriceBreakdown
)
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


async def copy_part_relations(
    db: AsyncSession,
    source_part_number: str,
    target_part: Part,
    copy_operations: bool,
    copy_material: bool,
    copy_batches: bool,
    current_user: User
):
    """
    Copy relations from source part to newly created target part.

    Args:
        db: Database session
        source_part_number: Source part number to copy from
        target_part: Newly created target part
        copy_operations: Whether to copy operations
        copy_material: Whether to copy material_item_id
        copy_batches: Whether to copy batches
        current_user: Current user for audit trail
    """
    from app.services.number_generator import NumberGenerator

    # Get source part
    result = await db.execute(
        select(Part).where(Part.part_number == source_part_number, Part.deleted_at.is_(None))
    )
    source_part = result.scalar_one_or_none()
    if not source_part:
        logger.warning(f"Source part {source_part_number} not found for copying")
        return

    # Copy material inputs if requested
    if copy_material:
        result = await db.execute(
            select(MaterialInput).where(MaterialInput.part_id == source_part.id)
        )
        source_material_inputs = result.scalars().all()

        for src_mat in source_material_inputs:
            new_mat = MaterialInput(
                part_id=target_part.id,
                seq=src_mat.seq,
                price_category_id=src_mat.price_category_id,
                material_item_id=src_mat.material_item_id,
                stock_shape=src_mat.stock_shape,
                stock_diameter=src_mat.stock_diameter,
                stock_length=src_mat.stock_length,
                stock_width=src_mat.stock_width,
                stock_height=src_mat.stock_height,
                stock_wall_thickness=src_mat.stock_wall_thickness,
                quantity=src_mat.quantity,
                notes=src_mat.notes
            )
            set_audit(new_mat, current_user.username)
            db.add(new_mat)

    # Copy operations if requested
    if copy_operations:
        result = await db.execute(
            select(Operation).where(Operation.part_id == source_part.id).order_by(Operation.seq)
        )
        source_operations = result.scalars().all()

        # Renumber operations to clean 10, 20, 30... sequence
        new_seq = 10
        for src_op in source_operations:
            # Operations use auto-increment ID, no custom number needed
            new_op = Operation(
                part_id=target_part.id,
                seq=new_seq,  # Clean sequence: 10, 20, 30...
                name=src_op.name,
                type=src_op.type,
                icon=src_op.icon,
                work_center_id=src_op.work_center_id,
                cutting_mode=src_op.cutting_mode,
                setup_time_min=src_op.setup_time_min,
                operation_time_min=src_op.operation_time_min,
                setup_time_locked=src_op.setup_time_locked,
                operation_time_locked=src_op.operation_time_locked,
                manning_coefficient=src_op.manning_coefficient,
                machine_utilization_coefficient=src_op.machine_utilization_coefficient,
                is_coop=src_op.is_coop,
                coop_type=src_op.coop_type,
                coop_price=src_op.coop_price,
                coop_min_price=src_op.coop_min_price,
                coop_days=src_op.coop_days
            )
            set_audit(new_op, current_user.username)
            db.add(new_op)
            new_seq += 10  # Increment by 10 for next operation

    # Copy batches if requested
    if copy_batches:
        result = await db.execute(
            select(Batch).where(Batch.part_id == source_part.id)
        )
        source_batches = result.scalars().all()

        for src_batch in source_batches:
            # Generate new batch number
            batch_number = await NumberGenerator.generate_batch_number(db)

            new_batch = Batch(
                batch_number=batch_number,
                part_id=target_part.id,
                quantity=src_batch.quantity,
                is_default=src_batch.is_default,
                # Don't copy frozen costs/prices - let them be recalculated
                is_frozen=False
            )
            set_audit(new_batch, current_user.username)
            db.add(new_batch)

    # Commit the copied relations
    await safe_commit(db, target_part, "kopírování relací dílu")


@router.get("/", response_model=dict)
async def get_parts(
    skip: int = Query(0, ge=0, description="Počet záznamů k přeskočení"),
    limit: int = Query(100, ge=1, le=500, description="Max počet záznamů"),
    status: Optional[str] = Query(None, description="Filtr statusu (draft, active, archived, quote)"),
    source: Optional[str] = Query(None, description="Filtr zdroje (manual, infor_import, quote_request)"),
    search: Optional[str] = Query(None, description="Hledat v article_number, name, part_number"),
    has_drawing: Optional[bool] = Query(None, description="Filtr: pouze díly s výkresem (file_id IS NOT NULL)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List dílů s pagination, status filtrem a vyhledáváním. Vrací {parts, total}."""
    query = (
        select(Part)
        .where(Part.deleted_at.is_(None))
    )

    # Status filter
    if status:
        query = query.where(Part.status == status)

    # Source filter
    if source:
        query = query.where(Part.source == source)

    # Search filter
    if search and search.strip():
        search_term = f"%{search.strip()}%"
        search_filters = [
            Part.part_number.ilike(search_term),
            Part.name.ilike(search_term),
            Part.article_number.ilike(search_term),
            Part.drawing_number.ilike(search_term),
        ]
        if search.strip().isdigit():
            search_filters.append(Part.id == int(search.strip()))
        query = query.where(or_(*search_filters))

    # Drawing filter (file_id IS NOT NULL)
    if has_drawing is True:
        query = query.where(Part.file_id.isnot(None))

    # Count total (before pagination)
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results — stable sort by article_number ASC for smooth infinite scroll
    # (NULLs last so items without article_number appear at the end)
    result = await db.execute(
        query.order_by(
            func.coalesce(Part.article_number, 'zzz').asc(),
            Part.id.asc()
        )
        .offset(skip)
        .limit(limit)
    )
    parts = result.scalars().all()

    # Get creator usernames for all parts
    creator_usernames = {p.created_by for p in parts if p.created_by}
    if creator_usernames:
        users_result = await db.execute(
            select(User).where(User.username.in_(creator_usernames))
        )
        users_map = {u.username: u.username for u in users_result.scalars().all()}
    else:
        users_map = {}

    # Build response with created_by_name
    parts_response = []
    for part in parts:
        part_dict = PartResponse.model_validate(part).model_dump()
        part_dict['created_by_name'] = users_map.get(part.created_by) if part.created_by else None
        parts_response.append(PartResponse(**part_dict))

    return {
        "parts": parts_response,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{part_number}", response_model=PartResponse)
async def get_part(
    part_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Part).where(Part.part_number == part_number, Part.deleted_at.is_(None))
    )
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")
    return part


@router.post("/", response_model=PartResponse)
async def create_part(
    data: PartCreate,
    copy_from: Optional[str] = None,  # Source part number to copy from
    copy_operations: bool = False,
    copy_material: bool = False,
    copy_batches: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    from app.services.number_generator import NumberGenerator, NumberGenerationError

    # Auto-generate part_number (10XXXXXX)
    try:
        part_number = await NumberGenerator.generate_part_number(db)
    except NumberGenerationError as e:
        logger.error(f"Failed to generate part number: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Nepodařilo se vygenerovat číslo dílu. Zkuste to znovu.")

    # Create part with auto-generated number + defaults
    # NOTE: Drawings are added via POST /api/parts/{part_number}/drawings/ (drawings_router)
    part = Part(
        part_number=part_number,
        article_number=data.article_number,
        name=data.name,
        drawing_number=data.drawing_number,
        customer_revision=data.customer_revision,
        notes=data.notes,
        revision="A",
        status="active",
        length=0.0
    )
    set_audit(part, current_user.username)
    db.add(part)

    part = await safe_commit(
        db, part, "vytváření dílu",
        integrity_error_msg="Díl s tímto artiklem již existuje (duplicitní article_number)"
    )
    logger.info(f"Created part: {part.part_number}", extra={
        "part_id": part.id,
        "user": current_user.username,
    })

    # Copy relations from source part if requested
    if copy_from:
        await copy_part_relations(
            db=db,
            source_part_number=copy_from,
            target_part=part,
            copy_operations=copy_operations,
            copy_material=copy_material,
            copy_batches=copy_batches,
            current_user=current_user
        )
        logger.info(f"Copied relations from {copy_from} to {part.part_number}", extra={
            "copy_operations": copy_operations,
            "copy_material": copy_material,
            "copy_batches": copy_batches
        })

    return part


@router.put("/{part_number}", response_model=PartResponse)
async def update_part(
    part_number: str,
    data: PartUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    result = await db.execute(select(Part).where(Part.part_number == part_number))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")

    # Optimistic locking check (ADR-008)
    if part.version != data.version:
        logger.warning(f"Version conflict updating part {part_number}: expected {data.version}, got {part.version}", extra={"part_number": part_number, "user": current_user.username})
        raise HTTPException(status_code=409, detail="Data byla změněna jiným uživatelem. Obnovte stránku a zkuste znovu.")

    # Update fields (exclude version - it's auto-incremented by event listener)
    for key, value in data.model_dump(exclude_unset=True, exclude={'version'}).items():
        setattr(part, key, value)

    set_audit(part, current_user.username, is_update=True)  # Audit trail helper

    part = await safe_commit(db, part, "aktualizace dílu")
    logger.info(f"Updated part: {part.part_number}", extra={"part_number": part_number, "user": current_user.username})
    return part


@router.post("/{part_number}/duplicate", response_model=PartResponse)
async def duplicate_part(
    part_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """Duplikovat díl s novým part_number (generuje nové 8-digit číslo dle ADR-017 v2.0)"""
    from app.services.number_generator import NumberGenerator, NumberGenerationError

    result = await db.execute(select(Part).where(Part.part_number == part_number))
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="Díl nenalezen")

    # Generate new valid 8-digit part_number (ADR-017 v2.0: 10XXXXXX format)
    try:
        new_part_number = await NumberGenerator.generate_part_number(db)
    except NumberGenerationError as e:
        logger.error(f"Failed to generate part number for duplicate: {e}")
        raise HTTPException(status_code=500, detail="Nepodařilo se vygenerovat číslo dílu")

    # Create duplicate with new part_number (ADR-024: material fields are in MaterialInput)
    new_part = Part(
        part_number=new_part_number,
        article_number=original.article_number,
        name=f"{original.name} (kopie)" if original.name else None,
        revision=original.revision,
        customer_revision=original.customer_revision,
        drawing_number=original.drawing_number,
        length=original.length,
        notes=original.notes,
        status="draft",
    )
    set_audit(new_part, current_user.username)
    db.add(new_part)

    new_part = await safe_commit(db, new_part, "duplikace dílu", "Nepodařilo se vytvořit duplikát dílu")
    logger.info(f"Duplicated part {part_number} → {new_part.part_number}", extra={"part_number": new_part.part_number, "user": current_user.username})
    return new_part


@router.delete("/{part_number}", status_code=204)
async def delete_part(
    part_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Soft delete dílu a všech závislých entit.

    Kaskáduje soft delete na:
    - Operations (a jejich Features)
    - MaterialInputs
    - Batches
    - Drawings

    ADR-001: Soft delete pro audit trail a referenční integritu.
    """
    from datetime import datetime

    # Načíst Part s všemi child entitami pro kaskádu
    result = await db.execute(
        select(Part)
        .options(
            selectinload(Part.operations).selectinload(Operation.features),
            selectinload(Part.material_inputs),
            selectinload(Part.batches),
        )
        .where(
            Part.part_number == part_number,
            Part.deleted_at.is_(None)  # Pouze aktivní
        )
    )
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")

    # Check: Part nesmí být v aktivní (DRAFT/SENT) nabídce
    quote_check = await db.execute(
        select(QuoteItem).where(
            QuoteItem.part_id == part.id,
            QuoteItem.deleted_at.is_(None)
        )
    )
    active_quote_items = quote_check.scalars().all()
    if active_quote_items:
        raise HTTPException(
            status_code=409,
            detail=f"Nelze smazat díl - je použit v {len(active_quote_items)} aktivních položkách nabídek"
        )

    # Soft delete timestamp
    now = datetime.utcnow()
    username = current_user.username

    # Kaskáda soft delete na všechny child entity
    for operation in part.operations:
        if operation.deleted_at is None:
            operation.deleted_at = now
            operation.deleted_by = username
            # Kaskáda na features
            for feature in operation.features:
                if feature.deleted_at is None:
                    feature.deleted_at = now
                    feature.deleted_by = username

    for material_input in part.material_inputs:
        if material_input.deleted_at is None:
            material_input.deleted_at = now
            material_input.deleted_by = username

    for batch in part.batches:
        if batch.deleted_at is None:
            batch.deleted_at = now
            batch.deleted_by = username

    # Soft delete samotného Part
    part.deleted_at = now
    part.deleted_by = username

    await safe_commit(db, action="mazání dílu")
    logger.info(
        f"Soft deleted part: {part_number} with {len(part.operations)} operations, "
        f"{len(part.material_inputs)} material_inputs, {len(part.batches)} batches",
        extra={"part_number": part_number, "user": username}
    )
    return {"message": "Díl smazán"}


@router.get("/{part_number}/full", response_model=dict)
async def get_part_full(
    part_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Vrátí Part s eager-loaded MaterialInputs (ADR-024)"""
    result = await db.execute(
        select(Part)
        .options(
            selectinload(Part.material_inputs).joinedload(MaterialInput.material_item).joinedload(MaterialItem.group),
            selectinload(Part.material_inputs).joinedload(MaterialInput.price_category).joinedload(MaterialPriceCategory.material_group),
        )
        .where(Part.part_number == part_number)
    )
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")

    # ADR-024: Material data is in material_inputs, not Part
    def serialize_material_input(mi):
        return {
            "id": mi.id,
            "seq": mi.seq,
            "stock_shape": mi.stock_shape.value if mi.stock_shape else None,
            "stock_diameter": mi.stock_diameter,
            "stock_length": mi.stock_length,
            "stock_width": mi.stock_width,
            "stock_height": mi.stock_height,
            "stock_wall_thickness": mi.stock_wall_thickness,
            "quantity": mi.quantity,
            "notes": mi.notes,
            "price_category": {
                "id": mi.price_category.id,
                "code": mi.price_category.code,
                "name": mi.price_category.name,
                "material_group": {
                    "id": mi.price_category.material_group.id,
                    "code": mi.price_category.material_group.code,
                    "name": mi.price_category.material_group.name,
                    "density": mi.price_category.material_group.density,
                } if mi.price_category.material_group else None
            } if mi.price_category else None,
            "material_item": {
                "id": mi.material_item.id,
                "code": mi.material_item.code,
                "name": mi.material_item.name,
                "shape": mi.material_item.shape.value if mi.material_item.shape else None,
                "diameter": mi.material_item.diameter,
                "group": {
                    "id": mi.material_item.group.id,
                    "code": mi.material_item.group.code,
                    "name": mi.material_item.group.name,
                    "density": mi.material_item.group.density,
                } if mi.material_item.group else None
            } if mi.material_item else None,
        }

    return {
        "id": part.id,
        "part_number": part.part_number,
        "article_number": part.article_number,
        "name": part.name,
        "length": part.length,
        "notes": part.notes,
        "version": part.version,
        "created_at": part.created_at.isoformat(),
        "updated_at": part.updated_at.isoformat(),
        "material_inputs": [serialize_material_input(mi) for mi in part.material_inputs] if part.material_inputs else [],
    }


@router.get("/{part_number}/stock-cost", response_model=StockCostResponse)
async def get_stock_cost(
    part_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Výpočet ceny polotovaru (Python, ne JS) - L-001 compliant
    ADR-024: MaterialInput refactor - používá Part.material_inputs
    """
    result = await db.execute(
        select(Part)
        .options(
            # ADR-024: MaterialInput → price_category → material_group + tiers
            selectinload(Part.material_inputs).joinedload(MaterialInput.price_category).joinedload(MaterialPriceCategory.material_group),
            selectinload(Part.material_inputs).joinedload(MaterialInput.price_category).selectinload(MaterialPriceCategory.tiers),
            # MaterialInput → material_item (optional) → group
            selectinload(Part.material_inputs).joinedload(MaterialInput.material_item).joinedload(MaterialItem.group),
        )
        .where(Part.part_number == part_number)
    )
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")

    # ADR-024: Check material_inputs instead of old Part.price_category
    if not part.material_inputs:
        return StockCostResponse(volume_mm3=0, weight_kg=0, price_per_kg=0, cost=0, density=0)

    cost = await calculate_stock_cost_from_part(part, quantity=1, db=db)
    return cost


# ============================================================================
# PRICING ENDPOINTS (ADR-016)
# ============================================================================

class PriceBreakdownResponse(BaseModel):
    """Response model for price breakdown (ADR-016)"""
    # Stroje
    machine_amortization: float
    machine_labor: float
    machine_tools: float
    machine_overhead: float
    machine_total: float
    machine_setup_time_min: float
    machine_setup_cost: float
    machine_operation_time_min: float
    machine_operation_cost: float

    # Režie + Marže
    overhead_coefficient: float
    work_with_overhead: float
    overhead_markup: float
    overhead_percent: float
    margin_coefficient: float
    work_with_margin: float
    margin_markup: float
    margin_percent: float

    # Kooperace
    coop_cost_raw: float
    coop_coefficient: float
    coop_cost: float

    # Materiál
    material_cost_raw: float
    stock_coefficient: float
    material_cost: float

    # Celkem
    total_cost: float
    quantity: int
    cost_per_piece: float

    @classmethod
    def from_breakdown(cls, breakdown: PriceBreakdown):
        """Convert PriceBreakdown dataclass to Pydantic model"""
        return cls(
            machine_amortization=breakdown.machine_amortization,
            machine_labor=breakdown.machine_labor,
            machine_tools=breakdown.machine_tools,
            machine_overhead=breakdown.machine_overhead,
            machine_total=breakdown.machine_total,
            machine_setup_time_min=breakdown.machine_setup_time_min,
            machine_setup_cost=breakdown.machine_setup_cost,
            machine_operation_time_min=breakdown.machine_operation_time_min,
            machine_operation_cost=breakdown.machine_operation_cost,
            overhead_coefficient=breakdown.overhead_coefficient,
            work_with_overhead=breakdown.work_with_overhead,
            overhead_markup=breakdown.overhead_markup,
            overhead_percent=breakdown.overhead_percent,
            margin_coefficient=breakdown.margin_coefficient,
            work_with_margin=breakdown.work_with_margin,
            margin_markup=breakdown.margin_markup,
            margin_percent=breakdown.margin_percent,
            coop_cost_raw=breakdown.coop_cost_raw,
            coop_coefficient=breakdown.coop_coefficient,
            coop_cost=breakdown.coop_cost,
            material_cost_raw=breakdown.material_cost_raw,
            stock_coefficient=breakdown.stock_coefficient,
            material_cost=breakdown.material_cost,
            total_cost=breakdown.total_cost,
            quantity=breakdown.quantity,
            cost_per_piece=breakdown.cost_per_piece
        )


@router.get("/{part_number}/pricing", response_model=PriceBreakdownResponse)
async def get_part_pricing(
    part_number: str,
    quantity: int = Query(1, ge=1, description="Množství kusů"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Výpočet ceny dílu s rozpadem nákladů (ADR-016).

    Vrací detailní rozpad:
    - Stroje (rozpad na amortizaci, mzdy, nástroje, provoz)
    - Režie (administrativní overhead)
    - Marže (zisk)
    - Kooperace (externí služby)
    - Materiál (polotovar)
    """
    result = await db.execute(
        select(Part)
        .options(
            joinedload(Part.operations),
            # ADR-024: MaterialInput → price_category → material_group + tiers
            selectinload(Part.material_inputs).joinedload(MaterialInput.price_category).joinedload(MaterialPriceCategory.material_group),
            selectinload(Part.material_inputs).joinedload(MaterialInput.price_category).selectinload(MaterialPriceCategory.tiers),
            # MaterialInput → material_item (optional) → group
            selectinload(Part.material_inputs).joinedload(MaterialInput.material_item).joinedload(MaterialItem.group),
        )
        .where(Part.part_number == part_number)
    )
    # unique() required when using joinedload with collections (tiers)
    part = result.unique().scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")

    try:
        breakdown = await calculate_part_price(part, quantity, db)
        return PriceBreakdownResponse.from_breakdown(breakdown)
    except Exception as e:
        import traceback
        logger.error(f"PRICING ERROR for part {part_number}, quantity {quantity}: {e}")
        logger.error(f"Stack trace:\n{traceback.format_exc()}")
        logger.error(f"Part data: id={part.id}, material_inputs={len(part.material_inputs) if part.material_inputs else 0}")
        raise HTTPException(status_code=500, detail=f"Pricing calculation failed: {str(e)}")


@router.get("/{part_number}/pricing/series", response_model=List[PriceBreakdownResponse])
async def get_series_pricing(
    part_number: str,
    quantities: str = Query("1,10,50,100,500", description="CSV seznam množství"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Porovnání cen pro různé série (setup distribuce).

    Vrací kalkulace pro zadaná množství - ukazuje jak se cena na kus
    snižuje s růstem série díky rozložení setupu.
    """
    result = await db.execute(
        select(Part)
        .options(
            joinedload(Part.operations),
            # ADR-024: MaterialInput → price_category → material_group + tiers
            selectinload(Part.material_inputs).joinedload(MaterialInput.price_category).joinedload(MaterialPriceCategory.material_group),
            selectinload(Part.material_inputs).joinedload(MaterialInput.price_category).selectinload(MaterialPriceCategory.tiers),
            # MaterialInput → material_item (optional) → group
            selectinload(Part.material_inputs).joinedload(MaterialInput.material_item).joinedload(MaterialItem.group),
        )
        .where(Part.part_number == part_number)
    )
    # unique() required when using joinedload with collections (tiers)
    part = result.unique().scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")

    # Parse quantities CSV
    try:
        qty_list = [int(q.strip()) for q in quantities.split(',')]
    except ValueError:
        raise HTTPException(status_code=400, detail="Neplatný formát množství (použij CSV: 1,10,50)")

    breakdowns = await calculate_series_pricing(part, qty_list, db)
    return [PriceBreakdownResponse.from_breakdown(b) for b in breakdowns]


    # NOTE: Drawing endpoints moved to drawings_router.py
    # Legacy single-drawing endpoints removed — use /api/parts/{part_number}/drawings/ instead
