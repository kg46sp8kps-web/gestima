"""GESTIMA - Parts API router"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import joinedload, selectinload

from app.database import get_db
from app.db_helpers import set_audit, safe_commit
from app.dependencies import get_current_user, require_role
from app.models import User, UserRole
from app.models.part import Part, PartCreate, PartUpdate, PartResponse, PartFullResponse, StockCostResponse
from app.models.material import MaterialItem, MaterialPriceCategory
from app.services.price_calculator import (
    calculate_stock_cost_from_part,
    calculate_part_price,
    calculate_series_pricing,
    PriceBreakdown
)
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[PartResponse])
async def get_parts(
    skip: int = Query(0, ge=0, description="Počet záznamů k přeskočení"),
    limit: int = Query(100, ge=1, le=500, description="Max počet záznamů"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List všech dílů s pagination (default limit=100, max=500)"""
    result = await db.execute(
        select(Part)
        .where(Part.deleted_at.is_(None))
        .order_by(Part.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/search")
async def search_parts(
    search: str = Query("", description="Hledat v ID, číslo výkresu, article number"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Filtrování dílů s multi-field search"""
    query = select(Part).where(Part.deleted_at.is_(None))

    if search.strip():
        search_term = f"%{search.strip()}%"
        filters = [
            Part.part_number.ilike(search_term),
            Part.name.ilike(search_term),
            Part.article_number.ilike(search_term)
        ]

        # Pokud je search digit, přidat ID search
        if search.strip().isdigit():
            filters.append(Part.id == int(search.strip()))

        query = query.where(or_(*filters))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = query.order_by(Part.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    parts = result.scalars().all()

    # Convert to Pydantic models for proper JSON serialization
    parts_response = [PartResponse.model_validate(part) for part in parts]

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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    from app.services.number_generator import NumberGenerator, NumberGenerationError

    # Auto-generate part_number if not provided
    if not data.part_number:
        try:
            part_number = await NumberGenerator.generate_part_number(db)
        except NumberGenerationError as e:
            logger.error(f"Failed to generate part number: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Nepodařilo se vygenerovat číslo dílu. Zkuste to znovu.")
    else:
        part_number = data.part_number
        # Kontrola duplicitního čísla dílu (pokud zadáno ručně)
        result = await db.execute(select(Part).where(Part.part_number == part_number))
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail=f"Díl s číslem '{part_number}' již existuje")

    # Create part with generated/provided number
    part_data = data.model_dump(exclude={'part_number'})
    part = Part(part_number=part_number, **part_data)
    set_audit(part, current_user.username)  # Audit trail helper (db_helpers.py)
    db.add(part)

    part = await safe_commit(db, part, "vytváření dílu")
    logger.info(f"Created part: {part.part_number}", extra={"part_id": part.id, "user": current_user.username})
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
    """Duplikovat díl s novým part_number (generuje nové 7-digit číslo dle ADR-017)"""
    from app.services.number_generator import NumberGenerator, NumberGenerationError

    result = await db.execute(select(Part).where(Part.part_number == part_number))
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="Díl nenalezen")

    # Generate new valid 7-digit part_number (ADR-017: 1XXXXXX format)
    try:
        new_part_number = await NumberGenerator.generate_part_number(db)
    except NumberGenerationError as e:
        logger.error(f"Failed to generate part number for duplicate: {e}")
        raise HTTPException(status_code=500, detail="Nepodařilo se vygenerovat číslo dílu")

    # Create duplicate with new part_number
    new_part = Part(
        part_number=new_part_number,
        article_number=original.article_number,
        name=f"{original.name} (kopie)" if original.name else None,
        material_item_id=original.material_item_id,
        price_category_id=original.price_category_id,
        stock_shape=original.stock_shape,
        length=original.length,
        notes=original.notes,
        drawing_path=original.drawing_path,
        stock_diameter=original.stock_diameter,
        stock_length=original.stock_length,
        stock_width=original.stock_width,
        stock_height=original.stock_height,
        stock_wall_thickness=original.stock_wall_thickness
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
    result = await db.execute(select(Part).where(Part.part_number == part_number))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")

    await db.delete(part)

    await safe_commit(db, action="mazání dílu", integrity_error_msg="Nelze smazat díl - existují závislé záznamy (operace, dávky)")
    logger.info(f"Deleted part: {part_number}", extra={"part_number": part_number, "user": current_user.username})
    return {"message": "Díl smazán"}


@router.get("/{part_number}/full")
async def get_part_full(
    part_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Vrátí Part s eager-loaded MaterialPriceCategory + MaterialGroup (Migration 2026-01-26)"""
    result = await db.execute(
        select(Part)
        .options(
            joinedload(Part.material_item).joinedload(MaterialItem.group),
            joinedload(Part.material_item).joinedload(MaterialItem.price_category),
            joinedload(Part.price_category).joinedload(MaterialPriceCategory.material_group)
        )
        .where(Part.part_number == part_number)
    )
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")

    # Manual serialization to include nested objects (Migration 2026-01-26: + price_category + stock_shape)
    return {
        "id": part.id,
        "part_number": part.part_number,
        "article_number": part.article_number,
        "name": part.name,
        "material_item_id": part.material_item_id,
        "price_category_id": part.price_category_id,
        "length": part.length,
        "notes": part.notes,
        "stock_shape": part.stock_shape.value if part.stock_shape else None,
        "stock_diameter": part.stock_diameter,
        "stock_length": part.stock_length,
        "stock_width": part.stock_width,
        "stock_height": part.stock_height,
        "stock_wall_thickness": part.stock_wall_thickness,
        "version": part.version,
        "created_at": part.created_at.isoformat(),
        "updated_at": part.updated_at.isoformat(),
        "material_item": {
            "id": part.material_item.id,
            "code": part.material_item.code,
            "name": part.material_item.name,
            "shape": part.material_item.shape.value if part.material_item.shape else None,
            "diameter": part.material_item.diameter,
            "width": part.material_item.width,
            "thickness": part.material_item.thickness,
            "wall_thickness": part.material_item.wall_thickness,
            "supplier": part.material_item.supplier,
            "material_group_id": part.material_item.material_group_id,
            "price_category_id": part.material_item.price_category_id,
            "group": {
                "id": part.material_item.group.id,
                "code": part.material_item.group.code,
                "name": part.material_item.group.name,
                "density": part.material_item.group.density,
            }
        } if part.material_item else None,
        "price_category": {
            "id": part.price_category.id,
            "code": part.price_category.code,
            "name": part.price_category.name,
            "material_group_id": part.price_category.material_group_id,
            "material_group": {
                "id": part.price_category.material_group.id,
                "code": part.price_category.material_group.code,
                "name": part.price_category.material_group.name,
                "density": part.price_category.material_group.density,
            } if part.price_category.material_group else None
        } if part.price_category else None
    }


@router.get("/{part_number}/stock-cost", response_model=StockCostResponse)
async def get_stock_cost(
    part_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Výpočet ceny polotovaru (Python, ne JS) - L-001 compliant
    Migration 2026-01-26: Podporuje Part.price_category (+ fallback na Part.material_item)
    """
    result = await db.execute(
        select(Part)
        .options(
            # Nové: Part.price_category.material_group + tiers
            joinedload(Part.price_category).joinedload(MaterialPriceCategory.material_group),
            joinedload(Part.price_category).selectinload(MaterialPriceCategory.tiers),
            # Fallback: Part.material_item.price_category + group + tiers
            joinedload(Part.material_item).joinedload(MaterialItem.group),
            joinedload(Part.material_item).joinedload(MaterialItem.price_category).selectinload(MaterialPriceCategory.tiers)
        )
        .where(Part.part_number == part_number)
    )
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")

    # Migration 2026-01-26: Part může mít price_category místo material_item
    if not part.price_category and not part.material_item:
        return StockCostResponse(volume_mm3=0, weight_kg=0, price_per_kg=0, cost=0, density=0)

    cost = await calculate_stock_cost_from_part(part, quantity=1, db=db)
    return cost


@router.post("/{part_number}/copy-material-geometry")
async def copy_material_geometry(
    part_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """Zkopíruje rozměry z MaterialItem do Part.stock_*"""
    result = await db.execute(
        select(Part)
        .options(joinedload(Part.material_item))
        .where(Part.part_number == part_number)
    )
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")

    if not part.material_item:
        raise HTTPException(status_code=400, detail="Díl nemá přiřazený materiál")

    mi = part.material_item
    part.stock_diameter = mi.diameter
    part.stock_width = mi.width
    part.stock_height = mi.thickness
    part.stock_wall_thickness = mi.wall_thickness
    # stock_length se nekopíruje - uživatel musí zadat délku polotovaru

    set_audit(part, current_user.username, is_update=True)

    part = await safe_commit(db, part, "kopírování geometrie")
    logger.info(f"Copied material geometry for part {part_number}", extra={"part_number": part_number, "user": current_user.username})
    return {"message": "Geometrie zkopírována", "version": part.version}


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
            # Nová cesta (Migration 2026-01-26): Part.price_category
            joinedload(Part.price_category).joinedload(MaterialPriceCategory.material_group),
            joinedload(Part.price_category).joinedload(MaterialPriceCategory.tiers),
            # Fallback cesta: Part.material_item (pro staré parts)
            joinedload(Part.material_item).joinedload(MaterialItem.group),
            joinedload(Part.material_item).joinedload(MaterialItem.price_category).joinedload(MaterialPriceCategory.material_group),
            joinedload(Part.material_item).joinedload(MaterialItem.price_category).joinedload(MaterialPriceCategory.tiers)
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
        logger.error(f"Part data: id={part.id}, material_item_id={part.material_item_id}, price_category_id={part.price_category_id}")
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
            # Nová cesta (Migration 2026-01-26): Part.price_category
            joinedload(Part.price_category).joinedload(MaterialPriceCategory.material_group),
            joinedload(Part.price_category).joinedload(MaterialPriceCategory.tiers),
            # Fallback cesta: Part.material_item (pro staré parts)
            joinedload(Part.material_item).joinedload(MaterialItem.group),
            joinedload(Part.material_item).joinedload(MaterialItem.price_category).joinedload(MaterialPriceCategory.material_group),
            joinedload(Part.material_item).joinedload(MaterialItem.price_category).joinedload(MaterialPriceCategory.tiers)
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
