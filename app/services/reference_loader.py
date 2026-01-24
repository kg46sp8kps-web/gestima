"""GESTIMA - Referenční data (stroje, materiály, typy kroků)"""

from typing import List, Dict, Any
from sqlalchemy import select

from app.database import async_session
from app.models.machine import MachineDB
from app.models import MaterialDB  # Backward compatibility alias → MaterialGroup
from app.services.feature_definitions import FEATURE_FIELDS


_machines_cache: List[Dict[str, Any]] = []
_materials_cache: List[Dict[str, Any]] = []


async def get_machines() -> List[Dict[str, Any]]:
    """Load active machines from DB (cached)"""
    global _machines_cache
    
    # Return cached if available
    if _machines_cache:
        return _machines_cache
    
    # Load from DB
    async with async_session() as session:
        result = await session.execute(
            select(MachineDB)
            .where(MachineDB.active == True)
            .where(MachineDB.deleted_at.is_(None))
            .order_by(MachineDB.priority)
        )
        machines = result.scalars().all()
        
        # Convert to dict
        _machines_cache = [
            {
                "id": m.id,
                "code": m.code,
                "name": m.name,
                "type": m.type,
                "subtype": m.subtype,
                "hourly_rate": m.hourly_rate,
                "max_bar_dia": m.max_bar_dia,
                "has_bar_feeder": m.has_bar_feeder,
                "has_milling": m.has_milling,
                "has_sub_spindle": m.has_sub_spindle,
                "setup_base_min": m.setup_base_min,
                "setup_per_tool_min": m.setup_per_tool_min,
            }
            for m in machines
        ]
        
        return _machines_cache


async def get_material_groups() -> List[Dict[str, Any]]:
    """Load materials from DB (cached)"""
    global _materials_cache
    
    # Return cached if available
    if _materials_cache:
        return _materials_cache
    
    # Load from DB
    async with async_session() as session:
        result = await session.execute(
            select(MaterialDB)
            .where(MaterialDB.deleted_at.is_(None))
            .order_by(MaterialDB.name)
        )
        materials = result.scalars().all()
        
        # Convert to dict
        # NOTE: MaterialGroup doesn't have price_per_kg or color anymore (ADR-011)
        # These are on MaterialItem now. For backward compatibility with deprecated
        # calculate_material_cost(), we provide fallback values here.
        _materials_cache = [
            {
                "code": m.code,
                "name": m.name,
                "density": m.density,
                "price_per_kg": 30.0,  # Fallback - price is now on MaterialItem
                "color": "#999999",     # Fallback - color removed in ADR-011
            }
            for m in materials
        ]
        
        return _materials_cache


async def get_material_properties(material_group: str) -> Dict[str, float]:
    """Get density and price for material group"""
    materials = await get_material_groups()
    
    for mat in materials:
        if mat["code"] == material_group:
            return {"density": mat["density"], "price_per_kg": mat["price_per_kg"]}
    
    # Fallback
    return {"density": 7.85, "price_per_kg": 30}


def get_feature_types() -> List[Dict[str, Any]]:
    result = []
    for code, config in FEATURE_FIELDS.items():
        result.append({
            "code": code,
            "name": config.get("name", code),
            "icon": config.get("icon", "🔧"),
            "category": config.get("category", "other"),
            "fields": config.get("fields", []),
            "cutting": config.get("cutting", []),
        })
    return result


def clear_cache():
    """Clear reference data cache"""
    global _machines_cache, _materials_cache
    _machines_cache = []
    _materials_cache = []
