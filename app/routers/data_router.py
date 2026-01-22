"""GESTIMA - Reference data API router"""

from typing import List, Dict, Any
from fastapi import APIRouter
from app.services.reference_loader import get_machines, get_material_groups, get_feature_types

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
