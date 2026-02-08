"""GESTIMA - Reference data API router"""

import logging
import math
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel, Field
from app.services.reference_loader import get_work_centers, get_material_groups, get_feature_types, get_material_properties
from app.dependencies import get_current_user
from app.models import User

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class WorkCenterRefResponse(BaseModel):
    """Reference data pro pracoviště (zjednodušené pro dropdown)"""
    id: int
    work_center_number: str
    name: str
    work_center_type: Optional[str] = None
    subtype: Optional[str] = None
    hourly_rate: float = Field(0, ge=0)
    max_bar_diameter: Optional[float] = Field(None, ge=0)
    has_bar_feeder: bool = False
    has_milling: bool = False
    has_sub_spindle: bool = False
    setup_base_min: float = Field(30.0, ge=0)
    setup_per_tool_min: float = Field(3.0, ge=0)


class MaterialRefResponse(BaseModel):
    """Reference data pro materiál"""
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=200)
    density: float = Field(..., gt=0)
    price_per_kg: float = Field(..., ge=0)
    color: str = Field(..., max_length=20)


class FeatureTypeResponse(BaseModel):
    """Reference data pro typ operace"""
    code: str
    name: str
    icon: str
    category: str
    fields: List[str]
    cutting: List[str]


# ============================================================================
# ENDPOINTS (chráněné autentizací)
# ============================================================================

@router.get("/work-centers", response_model=List[WorkCenterRefResponse])
async def list_work_centers(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Seznam pracovišť (vyžaduje přihlášení)"""
    try:
        return await get_work_centers()
    except Exception as e:
        logger.error(f"Error fetching work centers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba při načítání pracovišť")


@router.get("/materials", response_model=List[MaterialRefResponse])
async def list_materials(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Seznam materiálů (vyžaduje přihlášení)"""
    try:
        return await get_material_groups()
    except Exception as e:
        logger.error(f"Error fetching materials: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba při načítání materiálů")


@router.get("/feature-types", response_model=List[FeatureTypeResponse])
async def list_feature_types(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Seznam typů operací (vyžaduje přihlášení)"""
    try:
        return get_feature_types()
    except Exception as e:
        logger.error(f"Error fetching feature types: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba při načítání typů operací")


class StockPriceResponse(BaseModel):
    """Výpočet ceny polotovaru"""
    volume_mm3: float = Field(..., ge=0, description="Objem v mm³")
    weight_kg: float = Field(..., ge=0, description="Hmotnost v kg")
    price_per_kg: float = Field(..., ge=0, description="Cena za kg")
    cost: float = Field(..., ge=0, description="Celková cena")


@router.get("/stock-price", response_model=StockPriceResponse)
async def calculate_stock_price(
    stock_type: str = Query(..., description="tyc, trubka, prizez, plech, odlitek"),
    material_group: str = Query(..., description="konstrukcni_ocel, nerez_austeniticka, ..."),
    stock_diameter: float = Query(0, ge=0),
    stock_length: float = Query(0, ge=0),
    stock_diameter_inner: float = Query(0, ge=0),
    stock_width: float = Query(0, ge=0),
    stock_height: float = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
):
    """
    Live výpočet ceny polotovaru (pro preview při vytváření dílu).

    AUDIT-2026-01-27: Refactored to use inline calculation instead of deprecated function.
    This is a simplified estimate - actual pricing uses Part.price_category with dynamic tiers.

    Příklad:
    GET /api/data/stock-price?stock_type=tyc&material_group=nerez_austeniticka&stock_diameter=50&stock_length=100
    """
    try:
        # Get material properties (density, fallback price)
        props = await get_material_properties(material_group)
        density = props["density"]
        price_per_kg = props["price_per_kg"]

        # Calculate volume based on stock type
        volume_mm3 = 0.0

        if stock_type in ["tyc", "odlitek"]:
            if stock_diameter > 0 and stock_length > 0:
                r = stock_diameter / 2
                volume_mm3 = math.pi * r**2 * stock_length

        elif stock_type == "trubka":
            if stock_diameter > 0 and stock_length > 0:
                r_outer = stock_diameter / 2
                r_inner = stock_diameter_inner / 2 if stock_diameter_inner > 0 else 0
                volume_mm3 = math.pi * (r_outer**2 - r_inner**2) * stock_length

        elif stock_type in ["prizez", "plech"]:
            if stock_length > 0 and stock_width > 0 and stock_height > 0:
                volume_mm3 = stock_length * stock_width * stock_height

        # Calculate weight and cost
        volume_dm3 = volume_mm3 / 1_000_000
        weight_kg = volume_dm3 * density
        cost = weight_kg * price_per_kg

        return StockPriceResponse(
            volume_mm3=round(volume_mm3, 0),
            weight_kg=round(weight_kg, 3),
            price_per_kg=price_per_kg,
            cost=round(cost, 2),
        )
    except Exception as e:
        logger.error(f"Error calculating stock price: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba při výpočtu ceny polotovaru")
