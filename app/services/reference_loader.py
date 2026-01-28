"""GESTIMA - Referenční data (stroje, materiály, typy kroků)"""

import asyncio
import logging
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.database import async_session
from app.models.work_center import WorkCenter
from app.models import MaterialGroup
from app.services.feature_definitions import FEATURE_FIELDS

logger = logging.getLogger(__name__)


_work_centers_cache: List[Dict[str, Any]] = []
_materials_cache: List[Dict[str, Any]] = []
_cache_lock = asyncio.Lock()


async def get_work_centers() -> List[Dict[str, Any]]:
    """Load active work centers from DB (cached, thread-safe)"""
    global _work_centers_cache

    async with _cache_lock:
        # Return cached if available
        if _work_centers_cache:
            return _work_centers_cache

        # Load from DB
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(WorkCenter)
                    .where(WorkCenter.is_active == True)
                    .where(WorkCenter.deleted_at.is_(None))
                    .order_by(WorkCenter.priority)
                )
                work_centers = result.scalars().all()

                # Convert to dict
                _work_centers_cache = [
                    {
                        "id": wc.id,
                        "work_center_number": wc.work_center_number,
                        "name": wc.name,
                        "work_center_type": wc.work_center_type.value if wc.work_center_type else None,
                        "subtype": wc.subtype,
                        "hourly_rate": wc.hourly_rate_operation or 0,  # Use computed property (operation rate with tools)
                        "max_bar_diameter": wc.max_bar_diameter,
                        "has_bar_feeder": wc.has_bar_feeder,
                        "has_milling": wc.has_milling,
                        "has_sub_spindle": wc.has_sub_spindle,
                        "setup_base_min": wc.setup_base_min,
                        "setup_per_tool_min": wc.setup_per_tool_min,
                    }
                    for wc in work_centers
                ]

                return _work_centers_cache
        except SQLAlchemyError as e:
            logger.error(f"Database error loading work centers: {e}", exc_info=True)
            return []  # Return empty list on error


async def get_material_groups() -> List[Dict[str, Any]]:
    """Load materials from DB (cached, thread-safe)"""
    global _materials_cache

    async with _cache_lock:
        # Return cached if available
        if _materials_cache:
            return _materials_cache

        # Load from DB
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(MaterialGroup)
                    .where(MaterialGroup.deleted_at.is_(None))
                    .order_by(MaterialGroup.name)
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
        except SQLAlchemyError as e:
            logger.error(f"Database error loading materials: {e}", exc_info=True)
            return []  # Return empty list on error


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
    global _work_centers_cache, _materials_cache
    _work_centers_cache = []
    _materials_cache = []
