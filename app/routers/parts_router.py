"""GESTIMA - Parts API router"""

import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
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
from app.models.material_input import MaterialInput
from app.services.price_calculator import (
    calculate_stock_cost_from_part,
    calculate_part_price,
    calculate_series_pricing,
    PriceBreakdown
)
from app.services.drawing_service import DrawingService
from app.schemas.upload import DrawingUploadResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()

# Drawing storage directory (kept for backwards compatibility)
DRAWINGS_DIR = Path("uploads/drawings")
DRAWINGS_DIR.mkdir(parents=True, exist_ok=True)

# Drawing service (security-focused file operations)
drawing_service = DrawingService()


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
        .options(
            selectinload(Part.material_inputs),
            selectinload(Part.operations),
            selectinload(Part.batches)
        )
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
    query = select(Part).options(
        selectinload(Part.material_inputs),
        selectinload(Part.operations),
        selectinload(Part.batches)
    ).where(Part.deleted_at.is_(None))

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

    # Auto-generate part_number (10XXXXXX)
    try:
        part_number = await NumberGenerator.generate_part_number(db)
    except NumberGenerationError as e:
        logger.error(f"Failed to generate part number: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Nepodařilo se vygenerovat číslo dílu. Zkuste to znovu.")

    # Handle temp_drawing_id if provided
    final_drawing_path = data.drawing_path  # Fallback to old field
    if data.temp_drawing_id:
        try:
            # Move temp file to permanent storage
            final_drawing_path = await drawing_service.move_temp_to_permanent(
                data.temp_drawing_id,
                part_number
            )
            logger.info(f"Moved temp drawing {data.temp_drawing_id} → {final_drawing_path}")
        except HTTPException as e:
            # If temp file not found, log warning but don't fail part creation
            logger.warning(f"Temp drawing {data.temp_drawing_id} not found, skipping: {e.detail}")
            final_drawing_path = None

    # Create part with auto-generated number + defaults
    part = Part(
        part_number=part_number,
        article_number=data.article_number,
        drawing_path=final_drawing_path,
        name=data.name,
        customer_revision=data.customer_revision,
        notes=data.notes,
        # Defaults from SQL schema
        revision="A",
        status="active",
        length=0.0
    )
    set_audit(part, current_user.username)  # Audit trail helper (db_helpers.py)
    db.add(part)

    part = await safe_commit(db, part, "vytváření dílu")
    logger.info(f"Created part: {part.part_number}", extra={
        "part_id": part.id,
        "user": current_user.username,
        "has_drawing": bool(final_drawing_path)
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


@router.post("/{part_number}/copy-material-geometry")
async def copy_material_geometry(
    part_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """Zkopíruje rozměry z MaterialItem do Part.stock_*"""
    result = await db.execute(
        select(Part)
        .options(joinedload(Part.material_inputs).joinedload(MaterialInput.material_item))
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


# ============================================================================
# DRAWING ENDPOINTS
# ============================================================================

@router.post("/{part_number}/drawing", response_model=DrawingUploadResponse, status_code=201)
async def upload_part_drawing(
    part_number: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """
    Upload PDF drawing to part.
    Replaces existing drawing if present.

    Security checks:
    - PDF validation via magic bytes (not just MIME type)
    - File size limit (10MB)
    - Path traversal prevention

    Returns:
        DrawingUploadResponse: part_number, filename, drawing_path, size, uploaded_at
    """
    # Find part first
    result = await db.execute(select(Part).where(Part.part_number == part_number))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")

    # SECURITY: Validate PDF using DrawingService (magic bytes check!)
    # This also validates file size and sanitizes part_number
    try:
        # Delete old drawing if exists
        if part.drawing_path:
            try:
                await drawing_service.delete_drawing(part_number)
            except HTTPException:
                # Old drawing missing - that's okay, continue
                pass

        # Save new drawing (with security validations)
        drawing_path, file_size = await drawing_service.save_permanent(file, part_number)

        # Update part in transaction
        part.drawing_path = drawing_path
        set_audit(part, current_user.username, is_update=True)

        part = await safe_commit(db, part, "nahrávání výkresu")
        logger.info(f"Drawing uploaded for part {part_number}", extra={
            "part_number": part_number,
            "user": current_user.username,
            "size": file_size
        })

        return DrawingUploadResponse(
            part_number=part_number,
            filename=file.filename or "drawing.pdf",
            drawing_path=drawing_path,
            size=file_size,
            uploaded_at=datetime.utcnow()
        )

    except HTTPException:
        # Re-raise validation errors from DrawingService
        raise
    except Exception as e:
        logger.error(f"Failed to upload drawing for part {part_number}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save drawing")
    finally:
        await file.close()


@router.get("/{part_number}/drawing")
async def get_part_drawing(
    part_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Serve PDF drawing for viewing/download.
    Returns FileResponse with proper Content-Type and filename.

    Security:
    - Path traversal prevention via DrawingService
    - File existence validation
    """
    # Verify part exists
    result = await db.execute(select(Part).where(Part.part_number == part_number))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")

    if not part.drawing_path:
        raise HTTPException(status_code=404, detail="Drawing not found for this part")

    # SECURITY: Use DrawingService to get validated path
    try:
        drawing_path = drawing_service.get_drawing_path(part_number)

        return FileResponse(
            path=str(drawing_path),
            media_type="application/pdf",
            filename=f"{part_number}_drawing.pdf",
            headers={
                "Content-Disposition": f'inline; filename="{part_number}_drawing.pdf"'
            }
        )

    except HTTPException:
        # DrawingService raises 404 if file not found
        logger.warning(f"Drawing file missing for part {part_number}: {part.drawing_path}")
        raise


@router.delete("/{part_number}/drawing", status_code=204)
async def delete_part_drawing(
    part_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.OPERATOR]))
):
    """
    Delete part drawing file.

    Security:
    - Path traversal prevention via DrawingService
    - Transaction handling (file + DB update)

    Returns:
        204 No Content on success
    """
    # Verify part exists
    result = await db.execute(select(Part).where(Part.part_number == part_number))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Díl nenalezen")

    if not part.drawing_path:
        raise HTTPException(status_code=404, detail="No drawing to delete")

    # SECURITY: Use DrawingService to delete file (validates path)
    try:
        await drawing_service.delete_drawing(part_number)

        # Update part in transaction
        part.drawing_path = None
        set_audit(part, current_user.username, is_update=True)

        part = await safe_commit(db, part, "mazání výkresu")
        logger.info(f"Drawing deleted for part {part_number}", extra={
            "part_number": part_number,
            "user": current_user.username
        })

        # 204 No Content (no response body needed)
        return None

    except HTTPException:
        # Re-raise DrawingService errors
        raise
    except Exception as e:
        logger.error(f"Failed to delete drawing for part {part_number}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete drawing")
