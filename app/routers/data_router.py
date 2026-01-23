"""GESTIMA - Reference data API router"""

from typing import List, Dict, Any
from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.services.reference_loader import get_machines, get_material_groups, get_feature_types
from app.services.price_calculator import calculate_material_cost

router = APIRouter()


@router.get("/machines")
async def list_machines() -> List[Dict[str, Any]]:
    return await get_machines()


@router.get("/materials")
async def list_materials() -> List[Dict[str, Any]]:
    return await get_material_groups()


@router.get("/feature-types")
async def list_feature_types() -> List[Dict[str, Any]]:
    return get_feature_types()


class StockPriceResponse(BaseModel):
    volume_mm3: float
    weight_kg: float
    price_per_kg: float
    cost: float


@router.get("/stock-price", response_model=StockPriceResponse)
async def calculate_stock_price(
    stock_type: str = Query(..., description="tyc, trubka, prizez, plech, odlitek"),
    material_group: str = Query(..., description="konstrukcni_ocel, nerez_austeniticka, ..."),
    stock_diameter: float = Query(0, ge=0),
    stock_length: float = Query(0, ge=0),
    stock_diameter_inner: float = Query(0, ge=0),
    stock_width: float = Query(0, ge=0),
    stock_height: float = Query(0, ge=0),
):
    """
    Live výpočet ceny polotovaru.
    
    Příklad:
    GET /api/data/stock-price?stock_type=tyc&material_group=nerez_austeniticka&stock_diameter=50&stock_length=100
    """
    result = await calculate_material_cost(
        stock_diameter=stock_diameter,
        stock_length=stock_length,
        material_group=material_group,
        stock_diameter_inner=stock_diameter_inner,
        stock_type=stock_type,
        stock_width=stock_width,
        stock_height=stock_height,
    )
    
    return StockPriceResponse(
        volume_mm3=result.volume_mm3,
        weight_kg=result.weight_kg,
        price_per_kg=result.price_per_kg,
        cost=result.cost,
    )
