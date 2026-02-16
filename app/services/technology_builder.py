"""GESTIMA - Technology Builder Service (Phase 1)

Deterministic logic that wraps AI estimation output to generate
a complete manufacturing technology plan (set of operations).

Phase 1 generates:
- OP 10: Řezání materiálu (saw cutting from stock cross-section × material coefficient)
- OP 20: Main machining (AI estimated_time_min, 1 operation as-is)
- OP 100: Kontrola (quality control, setup_time based on complexity)

AI Vision output is NOT modified — this is a post-processing layer only.
"""

import logging
import math
from dataclasses import dataclass, field as dc_field
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import StockShape, WorkCenterType
from app.models.work_center import WorkCenter
from app.models.material_input import MaterialInput
from app.models.material import MaterialPriceCategory, MaterialGroup
from app.models.time_vision import TimeVisionEstimation
from app.models.cutting_condition import CuttingConditionDB
from app.models.operation import OperationCreate

logger = logging.getLogger(__name__)


# Complexity → QC setup time mapping (minutes)
COMPLEXITY_QC_TIME = {
    "simple": 10.0,
    "medium": 15.0,
    "complex": 20.0,
}


@dataclass
class TechnologyPlan:
    """Result of technology building."""
    operations: list = dc_field(default_factory=list)
    warnings: list = dc_field(default_factory=list)


def calculate_cut_height_mm(
    stock_shape: StockShape,
    stock_diameter: Optional[float] = None,
    stock_width: Optional[float] = None,
    stock_height: Optional[float] = None,
    stock_wall_thickness: Optional[float] = None,
) -> float:
    """
    Calculate cut height in mm — the distance the saw blade must travel
    vertically through the workpiece cross-section.

    For round bar: cut height = diameter
    For square bar: cut height = side
    For flat bar: cut height = height (shorter dimension)
    For tube: cut height = outer diameter
    For hex bar: cut height = across-flats dimension
    """
    if stock_shape == StockShape.ROUND_BAR:
        return stock_diameter or 0.0

    elif stock_shape == StockShape.SQUARE_BAR:
        return stock_width or stock_diameter or 0.0

    elif stock_shape == StockShape.FLAT_BAR:
        # Pila řeže přes výšku (kratší rozměr)
        h = stock_height or 0
        w = stock_width or 0
        return min(h, w) if (h > 0 and w > 0) else max(h, w)

    elif stock_shape == StockShape.HEXAGONAL_BAR:
        return stock_diameter or stock_width or 0.0

    elif stock_shape == StockShape.TUBE:
        return stock_diameter or 0.0

    elif stock_shape == StockShape.PLATE:
        # Plate: řeže se přes tloušťku (height)
        return stock_height or 0.0

    else:
        # CASTING, FORGING — approximate as round
        return stock_diameter or 0.0


def select_work_center(
    work_centers: list[WorkCenter],
    wc_type: WorkCenterType,
    min_diameter: Optional[float] = None,
    min_length: Optional[float] = None,
) -> Optional[WorkCenter]:
    """Select smallest suitable active work center by type and capacity."""
    candidates = [
        wc for wc in work_centers
        if wc.work_center_type == wc_type
        and wc.is_active
        and (min_diameter is None or (wc.max_workpiece_diameter or 0) >= min_diameter)
        and (min_length is None or (wc.max_workpiece_length or 0) >= min_length)
    ]
    # Sort by priority, then by smallest suitable machine
    candidates.sort(key=lambda wc: (wc.priority, wc.max_workpiece_diameter or 9999))
    return candidates[0] if candidates else None


async def _resolve_material_group_code(
    material_input: MaterialInput,
    db: AsyncSession,
) -> Optional[str]:
    """Navigate MaterialInput → PriceCategory → MaterialGroup → code."""
    try:
        if not material_input.price_category_id:
            return None

        pc_result = await db.execute(
            select(MaterialPriceCategory).where(
                MaterialPriceCategory.id == material_input.price_category_id
            )
        )
        price_category = pc_result.scalar_one_or_none()
        if not price_category or not price_category.material_group_id:
            return None

        mg_result = await db.execute(
            select(MaterialGroup).where(
                MaterialGroup.id == price_category.material_group_id
            )
        )
        material_group = mg_result.scalar_one_or_none()
        return material_group.code if material_group else None

    except Exception as e:
        logger.warning(f"Failed to resolve material group: {e}")
        return None


async def _get_sawing_feed_rate(
    material_group_code: str,
    mode: str,
    db: AsyncSession,
) -> Optional[float]:
    """Get sawing feed rate (mm/min) from cutting_conditions DB."""
    try:
        result = await db.execute(
            select(CuttingConditionDB).where(
                CuttingConditionDB.material_group == material_group_code,
                CuttingConditionDB.operation_type == "sawing",
                CuttingConditionDB.operation == "rezani",
                CuttingConditionDB.mode == mode,
            )
        )
        record = result.scalar_one_or_none()
        if record and record.f:
            return record.f
        return None
    except Exception as e:
        logger.warning(f"Failed to get sawing feed rate: {e}")
        return None


async def _build_op_cutting(
    part_id: int,
    material_input: Optional[MaterialInput],
    material_group_code: Optional[str],
    work_centers: list[WorkCenter],
    cutting_mode: str,
    db: AsyncSession,
    warnings: list[str],
) -> OperationCreate:
    """Build OP 10 - Řezání materiálu. ALWAYS generated (even without material)."""

    # Always use BOMAR STG240A (work_center_number 80000011)
    saw_wc = next(
        (wc for wc in work_centers
         if wc.work_center_number == "80000011" and wc.is_active),
        None,
    )
    if not saw_wc:
        # Fallback: any active SAW
        saw_wc = select_work_center(work_centers, WorkCenterType.SAW)

    saw_setup = saw_wc.setup_base_min if saw_wc and saw_wc.setup_base_min else 10.0
    operation_time = 0.0

    if material_input is None:
        warnings.append("Materiál nezadán — doplňte pro výpočet času řezání")
    elif not material_group_code:
        warnings.append("Materiálová skupina nenalezena — nelze vypočítat čas řezání")
    else:
        # Calculate cut height (mm) — distance blade must travel through workpiece
        cut_height_mm = calculate_cut_height_mm(
            stock_shape=material_input.stock_shape,
            stock_diameter=material_input.stock_diameter,
            stock_width=material_input.stock_width,
            stock_height=material_input.stock_height,
            stock_wall_thickness=material_input.stock_wall_thickness,
        )

        if cut_height_mm <= 0:
            warnings.append("Rozměry polotovaru nejsou zadány — čas řezání = 0")
        else:
            # Get feed rate (mm/min) from DB
            feed_rate = await _get_sawing_feed_rate(
                material_group_code, cutting_mode, db
            )
            if feed_rate is None:
                warnings.append(
                    "Řezné podmínky pro pilu nejsou v DB — spusťte seed nebo zadejte v Master Admin"
                )
            else:
                operation_time = round(cut_height_mm / feed_rate, 1)

    return OperationCreate(
        part_id=part_id,
        seq=10,
        name="OP10 - Řezání materiálu",
        type="cutting",
        icon="scissors",
        work_center_id=saw_wc.id if saw_wc else None,
        cutting_mode=cutting_mode,
        setup_time_min=saw_setup,
        operation_time_min=operation_time,
    )


def _build_op_machining(
    part_id: int,
    estimation: TimeVisionEstimation,
    work_centers: list[WorkCenter],
    warnings: list[str],
) -> OperationCreate:
    """Build OP 20 - Main machining operation (from AI estimation)."""

    part_type = estimation.part_type or "ROT"
    op_type = "milling" if part_type == "PRI" else "turning"
    op_label = "CNC frézování" if part_type == "PRI" else "CNC soustružení"
    op_icon = "settings" if part_type == "PRI" else "rotate-cw"

    # Select work center based on part type and dimensions
    if part_type == "PRI":
        wc_type = WorkCenterType.CNC_MILL_3AX
        min_dim = estimation.max_length_mm
    else:
        wc_type = WorkCenterType.CNC_LATHE
        min_dim = estimation.max_diameter_mm

    wc = select_work_center(work_centers, wc_type, min_diameter=min_dim)
    if not wc:
        warnings.append(
            f"Nenalezen vhodný {wc_type.value} stroj pro rozměr {min_dim} mm"
        )

    wc_setup = wc.setup_base_min if wc and wc.setup_base_min else 30.0

    return OperationCreate(
        part_id=part_id,
        seq=20,
        name=f"OP20 - {op_label}",
        type=op_type,
        icon=op_icon,
        work_center_id=wc.id if wc else None,
        cutting_mode="mid",
        setup_time_min=wc_setup,
        operation_time_min=estimation.estimated_time_min or 0.0,
        ai_estimation_id=estimation.id,
    )


def _build_op_kontrola(
    part_id: int,
    complexity: str,
    work_centers: list[WorkCenter],
    warnings: list[str],
) -> OperationCreate:
    """Build OP 100 - Kontrola (quality control)."""

    qc_wc = select_work_center(work_centers, WorkCenterType.QUALITY_CONTROL)
    if not qc_wc:
        warnings.append("Nenalezeno pracoviště KONTROLA")

    qc_setup_time = COMPLEXITY_QC_TIME.get(complexity, 15.0)

    return OperationCreate(
        part_id=part_id,
        seq=100,
        name="OP100 - Kontrola",
        type="generic",
        icon="check",
        work_center_id=qc_wc.id if qc_wc else None,
        cutting_mode="mid",
        setup_time_min=qc_setup_time,
        operation_time_min=0.0,
    )


async def build_technology(
    estimation: TimeVisionEstimation,
    material_input: Optional[MaterialInput],
    part_id: int,
    db: AsyncSession,
    cutting_mode: str = "mid",
) -> TechnologyPlan:
    """
    Build complete technology plan from AI estimation + material data.

    Always generates 3 operations:
    - OP 10: Řezání materiálu (always, even without material — time=0 with warning)
    - OP 20: Main machining (AI estimated_time_min)
    - OP 100: Kontrola (setup_time based on complexity)

    Args:
        estimation: AI estimation result (part_type, complexity, estimated_time_min)
        material_input: Stock data (shape, dimensions) — may be None
        part_id: Part ID for operation FK
        db: Database session
        cutting_mode: low/mid/high for sawing feed rate lookup

    Returns:
        TechnologyPlan with 3 operations and any warnings
    """
    warnings: list[str] = []
    operations: list[OperationCreate] = []

    # Load active work centers
    wc_result = await db.execute(
        select(WorkCenter).where(WorkCenter.is_active == True)
    )
    work_centers = list(wc_result.scalars().all())

    # Resolve material group code (for sawing feed rate lookup)
    material_group_code = None
    if material_input:
        material_group_code = await _resolve_material_group_code(
            material_input, db
        )

    # === OP 10: Řezání materiálu (ALWAYS) ===
    op10 = await _build_op_cutting(
        part_id=part_id,
        material_input=material_input,
        material_group_code=material_group_code,
        work_centers=work_centers,
        cutting_mode=cutting_mode,
        db=db,
        warnings=warnings,
    )
    operations.append(op10)

    # === OP 20: Main machining (from AI) ===
    op20 = _build_op_machining(
        part_id=part_id,
        estimation=estimation,
        work_centers=work_centers,
        warnings=warnings,
    )
    operations.append(op20)

    # === OP 100: Kontrola ===
    op100 = _build_op_kontrola(
        part_id=part_id,
        complexity=estimation.complexity or "medium",
        work_centers=work_centers,
        warnings=warnings,
    )
    operations.append(op100)

    return TechnologyPlan(operations=operations, warnings=warnings)
