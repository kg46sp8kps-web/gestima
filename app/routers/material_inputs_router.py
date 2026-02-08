"""GESTIMA - Material Inputs Router

ADR-024: MaterialInput refactor (v1.8.0)

Endpoints:
- CRUD operations for MaterialInput
- Link/unlink MaterialInput ↔ Operation (M:N relationship)
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.material_input import (
    MaterialInput,
    MaterialInputCreate,
    MaterialInputUpdate,
    MaterialInputResponse,
    MaterialInputWithOperationsResponse,
    MaterialOperationLinkRequest,
    material_operation_link,
)
from app.models.operation import Operation
from app.models.part import Part
from app.models.enums import UserRole, StockShape
from app.models.user import User
from app.models.material import MaterialPriceCategory
from app.services.material_calculator import calculate_material_weight_and_price

router = APIRouter(prefix="/api/material-inputs", tags=["material-inputs"])


# ═══════════════════════════════════════════════════════════════
# PYDANTIC SCHEMAS
# ═══════════════════════════════════════════════════════════════

class MaterialSummaryRequest(BaseModel):
    """Request schema for calculating material weight and price without saving to DB"""
    price_category_id: int = Field(..., gt=0, description="ID cenové kategorie")
    stock_shape: StockShape = Field(..., description="Tvar polotovaru")
    stock_diameter: Optional[float] = Field(None, ge=0, description="Průměr v mm")
    stock_length: Optional[float] = Field(None, ge=0, description="Délka v mm")
    stock_width: Optional[float] = Field(None, ge=0, description="Šířka v mm")
    stock_height: Optional[float] = Field(None, ge=0, description="Výška v mm")
    stock_thickness: Optional[float] = Field(None, ge=0, description="Tloušťka v mm (pro plate)")
    stock_wall_thickness: Optional[float] = Field(None, ge=0, description="Tloušťka stěny v mm (pro tube)")
    quantity: int = Field(1, ge=1, description="Počet kusů")


class MaterialSummaryResponse(BaseModel):
    """Response schema with calculated material weight and price"""
    weight_kg: float = Field(..., description="Hmotnost za kus v kg")
    total_weight_kg: float = Field(..., description="Celková hmotnost v kg")
    price_category: Dict[str, str] = Field(..., description="Cenová kategorie (code, name)")
    price_tier: Optional[Dict[str, Any]] = Field(None, description="Cenový tier (min_weight, max_weight, price_per_kg)")
    price_per_kg: float = Field(..., description="Cena za kg v Kč")
    cost_per_piece: float = Field(..., description="Cena za kus v Kč")
    total_cost: float = Field(..., description="Celková cena v Kč")
    tier_range: str = Field(..., description="Rozsah tieru (např. '0-15kg')")
    tier_id: Optional[int] = Field(None, description="ID vybraného tieru (pro zvýraznění)")


# ═══════════════════════════════════════════════════════════════
# CRUD OPERATIONS
# ═══════════════════════════════════════════════════════════════

@router.get("/parts/{part_id}", response_model=List[MaterialInputWithOperationsResponse])
async def list_material_inputs(
    part_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VIEWER]))
):
    """Seznam materiálových vstupů pro díl (seřazeno podle seq)"""

    result = await db.execute(
        select(MaterialInput)
        .options(selectinload(MaterialInput.operations))
        .where(
            and_(
                MaterialInput.part_id == part_id,
                MaterialInput.deleted_at.is_(None)
            )
        )
        .order_by(MaterialInput.seq)
    )

    materials = result.scalars().all()

    # Calculate weight and cost for each material
    enriched_materials = []
    for mat in materials:
        mat_dict = MaterialInputWithOperationsResponse.model_validate(mat).model_dump()

        # Calculate weight and cost if shape and category are present
        if mat.stock_shape and mat.price_category_id:
            try:
                dimensions = {
                    'diameter': mat.stock_diameter,
                    'length': mat.stock_length,
                    'width': mat.stock_width,
                    'height': mat.stock_height,
                    'wall_thickness': mat.stock_wall_thickness
                }

                calc = await calculate_material_weight_and_price(
                    stock_shape=mat.stock_shape,
                    dimensions=dimensions,
                    price_category_id=mat.price_category_id,
                    quantity=mat.quantity,
                    db=db
                )

                mat_dict['weight_kg'] = calc.weight_kg
                mat_dict['cost_per_piece'] = calc.total_cost / mat.quantity if mat.quantity > 0 else 0
                mat_dict['price_per_kg'] = calc.price_per_kg
            except Exception as e:
                # If calculation fails, leave as None
                print(f"[MaterialInputs] Failed to calculate for material {mat.id}: {e}")
                mat_dict['weight_kg'] = None
                mat_dict['cost_per_piece'] = None
                mat_dict['price_per_kg'] = None

        enriched_materials.append(mat_dict)

    return enriched_materials


@router.get("/{material_id}", response_model=MaterialInputWithOperationsResponse)
async def get_material_input(
    material_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VIEWER]))
):
    """Detail materiálového vstupu"""

    result = await db.execute(
        select(MaterialInput)
        .options(selectinload(MaterialInput.operations))
        .where(
            and_(
                MaterialInput.id == material_id,
                MaterialInput.deleted_at.is_(None)
            )
        )
    )

    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MaterialInput {material_id} not found"
        )

    return material


@router.post("", response_model=MaterialInputResponse, status_code=status.HTTP_201_CREATED)
async def create_material_input(
    data: MaterialInputCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.OPERATOR]))
):
    """Vytvoření nového materiálového vstupu"""

    # Verify part exists
    part_result = await db.execute(
        select(Part).where(
            and_(
                Part.id == data.part_id,
                Part.deleted_at.is_(None)
            )
        )
    )
    if not part_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Part {data.part_id} not found"
        )

    # Create MaterialInput
    material = MaterialInput(
        **data.model_dump(),
        created_by=current_user.username,
        updated_by=current_user.username
    )

    try:
        db.add(material)
        await db.commit()
        await db.refresh(material)
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to create MaterialInput: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create material input"
        )

    return material


@router.put("/{material_id}", response_model=MaterialInputWithOperationsResponse)
async def update_material_input(
    material_id: int,
    data: MaterialInputUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.OPERATOR]))
):
    """Aktualizace materiálového vstupu (optimistic locking)"""

    # Get current material with operations
    result = await db.execute(
        select(MaterialInput)
        .options(selectinload(MaterialInput.operations))
        .where(
            and_(
                MaterialInput.id == material_id,
                MaterialInput.deleted_at.is_(None)
            )
        )
    )
    material = result.scalar_one_or_none()

    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MaterialInput {material_id} not found"
        )

    # Optimistic locking check
    if material.version != data.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Data změněna jiným uživatelem. Načtěte znovu."
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True, exclude={"version"})
    update_data["updated_by"] = current_user.username
    update_data["version"] = material.version + 1

    result = await db.execute(
        update(MaterialInput)
        .where(
            and_(
                MaterialInput.id == material_id,
                MaterialInput.version == data.version
            )
        )
        .values(**update_data)
        .returning(MaterialInput)
    )

    updated_material = result.scalar_one_or_none()
    if not updated_material:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Optimistic lock failed"
        )

    try:
        await db.commit()
        await db.refresh(updated_material, ["operations"])
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to update MaterialInput {material_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update material input"
        )

    # Calculate weight and price (same logic as list endpoint)
    mat_dict = {
        **MaterialInputWithOperationsResponse.model_validate(updated_material).model_dump(),
        'weight_kg': None,
        'cost_per_piece': None,
        'price_per_kg': None
    }

    if updated_material.stock_shape and updated_material.price_category_id:
        try:
            dimensions = {
                'diameter': updated_material.stock_diameter,
                'length': updated_material.stock_length,
                'width': updated_material.stock_width,
                'height': updated_material.stock_height,
                'wall_thickness': updated_material.stock_wall_thickness
            }

            calc = await calculate_material_weight_and_price(
                stock_shape=updated_material.stock_shape,
                dimensions=dimensions,
                price_category_id=updated_material.price_category_id,
                quantity=updated_material.quantity,
                db=db
            )

            mat_dict['weight_kg'] = calc.weight_kg
            mat_dict['cost_per_piece'] = calc.total_cost / updated_material.quantity if updated_material.quantity > 0 else 0
            mat_dict['price_per_kg'] = calc.price_per_kg
        except Exception as e:
            print(f"[MaterialInputs] Failed to calculate for material {material_id}: {e}")

    return mat_dict


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material_input(
    material_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.OPERATOR]))
):
    """Smazání materiálového vstupu (soft delete)"""

    from datetime import datetime as dt

    result = await db.execute(
        update(MaterialInput)
        .where(
            and_(
                MaterialInput.id == material_id,
                MaterialInput.deleted_at.is_(None)
            )
        )
        .values(
            deleted_at=dt.utcnow(),
            deleted_by=current_user.username
        )
        .returning(MaterialInput.id)
    )

    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MaterialInput {material_id} not found"
        )

    try:
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to delete MaterialInput {material_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete material input"
        )


# ═══════════════════════════════════════════════════════════════
# M:N LINKING (MaterialInput ↔ Operation)
# ═══════════════════════════════════════════════════════════════

@router.post("/{material_id}/link-operation/{operation_id}", status_code=status.HTTP_201_CREATED)
async def link_material_to_operation(
    material_id: int,
    operation_id: int,
    request: Optional[MaterialOperationLinkRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.OPERATOR]))
):
    """Přiřadit materiál k operaci (M:N vztah)"""

    # Verify MaterialInput exists
    mat_result = await db.execute(
        select(MaterialInput).where(
            and_(
                MaterialInput.id == material_id,
                MaterialInput.deleted_at.is_(None)
            )
        )
    )
    if not mat_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MaterialInput {material_id} not found"
        )

    # Verify Operation exists
    op_result = await db.execute(
        select(Operation).where(
            and_(
                Operation.id == operation_id,
                Operation.deleted_at.is_(None)
            )
        )
    )
    if not op_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Operation {operation_id} not found"
        )

    # Check if link already exists
    existing = await db.execute(
        select(material_operation_link).where(
            and_(
                material_operation_link.c.material_input_id == material_id,
                material_operation_link.c.operation_id == operation_id
            )
        )
    )
    if existing.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Link already exists"
        )

    # Create link
    consumed_quantity = request.consumed_quantity if request else None
    try:
        await db.execute(
            material_operation_link.insert().values(
                material_input_id=material_id,
                operation_id=operation_id,
                consumed_quantity=consumed_quantity
            )
        )
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to link MaterialInput {material_id} to Operation {operation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create link"
        )

    return {"message": "Link created successfully"}


@router.delete("/{material_id}/unlink-operation/{operation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_material_from_operation(
    material_id: int,
    operation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.OPERATOR]))
):
    """Odebrat vazbu materiál → operace"""

    result = await db.execute(
        delete(material_operation_link).where(
            and_(
                material_operation_link.c.material_input_id == material_id,
                material_operation_link.c.operation_id == operation_id
            )
        )
    )

    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found"
        )

    try:
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to unlink MaterialInput {material_id} from Operation {operation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove link"
        )


@router.get("/operations/{operation_id}/materials", response_model=List[MaterialInputResponse])
async def get_operation_materials(
    operation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VIEWER]))
):
    """Materiály spotřebované v operaci"""

    result = await db.execute(
        select(MaterialInput)
        .join(
            material_operation_link,
            MaterialInput.id == material_operation_link.c.material_input_id
        )
        .where(
            and_(
                material_operation_link.c.operation_id == operation_id,
                MaterialInput.deleted_at.is_(None)
            )
        )
        .order_by(MaterialInput.seq)
    )

    return result.scalars().all()


# ═══════════════════════════════════════════════════════════════
# MATERIAL CALCULATION (PREVIEW WITHOUT SAVING)
# ═══════════════════════════════════════════════════════════════

@router.post("/calculate-summary", response_model=MaterialSummaryResponse)
async def calculate_material_summary(
    request: MaterialSummaryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calculate material weight and price WITHOUT saving to database (for live preview in UI).

    This endpoint provides real-time calculation of material costs based on:
    - Stock shape and dimensions
    - Price category (with tiers)
    - Quantity

    Returns calculated weight, price tier, and total cost.
    """

    # Build dimensions dict from request fields
    dimensions = {}
    if request.stock_diameter is not None:
        dimensions['diameter'] = request.stock_diameter
    if request.stock_length is not None:
        dimensions['length'] = request.stock_length
    if request.stock_width is not None:
        dimensions['width'] = request.stock_width
    if request.stock_height is not None:
        dimensions['height'] = request.stock_height
    if request.stock_thickness is not None:
        dimensions['thickness'] = request.stock_thickness
    if request.stock_wall_thickness is not None:
        dimensions['wall_thickness'] = request.stock_wall_thickness

    # Call calculator service
    try:
        calculation = await calculate_material_weight_and_price(
            stock_shape=request.stock_shape,
            dimensions=dimensions,
            price_category_id=request.price_category_id,
            quantity=request.quantity,
            db=db
        )
    except HTTPException:
        # Re-raise HTTP exceptions from calculator service
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Calculation failed: {str(e)}"
        )

    # Load MaterialPriceCategory for response (code, name)
    result = await db.execute(
        select(MaterialPriceCategory).where(
            MaterialPriceCategory.id == request.price_category_id
        )
    )
    price_category = result.scalar_one_or_none()

    if not price_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MaterialPriceCategory {request.price_category_id} not found"
        )

    # Build price_tier dict if tier was found
    price_tier = None
    if calculation.tier_id:
        # Fetch tier details from DB
        from app.models.material import MaterialPriceTier
        tier_result = await db.execute(
            select(MaterialPriceTier).where(MaterialPriceTier.id == calculation.tier_id)
        )
        tier = tier_result.scalar_one_or_none()
        if tier:
            price_tier = {
                "min_weight": tier.min_weight,
                "max_weight": tier.max_weight,
                "price_per_kg": tier.price_per_kg
            }

    # Return formatted response
    return MaterialSummaryResponse(
        weight_kg=calculation.weight_kg,
        total_weight_kg=calculation.total_weight_kg,
        price_category={
            "code": price_category.code,
            "name": price_category.name
        },
        price_tier=price_tier,
        price_per_kg=calculation.price_per_kg,
        cost_per_piece=calculation.cost_per_piece,
        total_cost=calculation.total_cost,
        tier_range=calculation.tier_range,
        tier_id=calculation.tier_id
    )
