"""GESTIMA - Řezné podmínky"""

import logging
from typing import Dict, Any, Optional, List
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.database import async_session
from app.models.cutting_condition import CuttingConditionDB
from app.services.feature_definitions import FEATURE_FIELDS

logger = logging.getLogger(__name__)


async def get_conditions(
    feature_type: str,
    material_group: str,
    mode: str = "mid",
    diameter: Optional[float] = None,
    pitch: Optional[float] = None,
) -> Dict[str, Any]:
    """Get cutting conditions from DB"""
    result = {"Vc": None, "f": None, "Ap": None, "fz": None}
    
    # Get DB operation mapping from feature definition
    feature_def = FEATURE_FIELDS.get(feature_type)
    if not feature_def or "db_operation" not in feature_def:
        return result
    
    operation_type, operation = feature_def["db_operation"]
    
    # Query DB
    try:
        async with async_session() as session:
            query = select(CuttingConditionDB).where(
                CuttingConditionDB.material_group == material_group,
                CuttingConditionDB.operation_type == operation_type,
                CuttingConditionDB.operation == operation,
                CuttingConditionDB.mode == mode,
                CuttingConditionDB.deleted_at.is_(None)
            )

            db_result = await session.execute(query)
            condition = db_result.scalar_one_or_none()

            if not condition:
                return result

            result["Vc"] = condition.Vc
            result["f"] = condition.f
            result["Ap"] = condition.Ap if condition.Ap else None

            # Drilling-specific adjustments
            if operation_type == "drilling" and diameter:
                result = _apply_drilling_coefficients(result, diameter)

            return result
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_conditions: {e}", exc_info=True)
        return result  # Return empty result on error


def _apply_drilling_coefficients(conditions: Dict, diameter: float) -> Dict:
    coefficients = [
        (3,   0.60, 0.25),
        (6,   0.70, 0.40),
        (10,  0.85, 0.60),
        (16,  1.00, 0.80),
        (25,  1.00, 1.00),
        (40,  0.95, 1.15),
        (999, 0.85, 1.25),
    ]
    
    k_vc, k_f = 1.0, 1.0
    for max_dia, kvc, kf in coefficients:
        if diameter <= max_dia:
            k_vc, k_f = kvc, kf
            break
    
    if conditions.get("Vc"):
        conditions["Vc"] = round(conditions["Vc"] * k_vc, 0)
    if conditions.get("f"):
        conditions["f"] = round(conditions["f"] * k_f, 3)
    
    return conditions


# get_threading_passes() was removed - not used anywhere in codebase
