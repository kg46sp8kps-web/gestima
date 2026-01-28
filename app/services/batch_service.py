"""GESTIMA - Batch Cost Recalculation Service"""

import logging
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch import Batch
from app.models.part import Part
from app.models.operation import Operation
# Machine model removed - replaced by WorkCenter (ADR-021)
from app.models.material import MaterialItem, MaterialGroup, MaterialPriceCategory
from app.services.price_calculator import (
    calculate_stock_cost_from_part,
    calculate_batch_prices,  # Legacy
    calculate_part_price,     # New (ADR-016)
)

logger = logging.getLogger(__name__)


async def recalculate_batch_costs(batch: Batch, db: AsyncSession) -> Batch:
    """
    Přepočítá všechny náklady batche podle aktuálního stavu Part + Operations + Machines.

    Postup:
    1. Načte Part (s material_item + group + price_category)
    2. Vypočítá material cost (calculate_stock_cost_from_part)
    3. Načte Operations pro part
    4. Načte Machines pro operations
    5. Vypočítá machining/setup/coop costs (calculate_batch_prices)
    6. Updatne batch fields

    Args:
        batch: Batch instance (může být nový nebo existující)
        db: AsyncSession

    Returns:
        Batch: Updatnutý batch (caller musí commitnout!)

    Raises:
        ValueError: Part nenalezen, chybí material_item, atd.
    """
    try:
        # 1. Načíst Part s material dependencies + operations (Migration 2026-01-26: + Part.price_category)
        stmt = select(Part).where(Part.id == batch.part_id).options(
            # Nové: Part.price_category + material_group + tiers
            selectinload(Part.price_category)
            .selectinload(MaterialPriceCategory.material_group),
            selectinload(Part.price_category)
            .selectinload(MaterialPriceCategory.tiers),
            # Fallback: Part.material_item (starší parts)
            selectinload(Part.material_item)
            .selectinload(MaterialItem.group),
            selectinload(Part.material_item)
            .selectinload(MaterialItem.price_category)
            .selectinload(MaterialPriceCategory.tiers),
            # Operations (pro calculate_part_price - ADR-016)
            selectinload(Part.operations),
        )
        result = await db.execute(stmt)
        part = result.scalar_one_or_none()

        if not part:
            raise ValueError(f"Part {batch.part_id} not found")

        # Migration 2026-01-26: Part může mít price_category místo material_item
        if not part.price_category and not part.material_item:
            logger.warning(
                f"Part {part.id} has neither price_category nor material_item, setting material_cost=0"
            )
            batch.material_cost = 0.0
            batch.material_weight_kg = None
            batch.material_price_per_kg = None
            material_cost = 0.0
        else:
            # 2. Vypočítat material cost (s dynamic price tiers - ADR-014)
            material_calc = await calculate_stock_cost_from_part(
                part, batch.quantity, db
            )
            material_cost = material_calc.cost  # Za 1 kus
            batch.material_cost = material_cost

            # ADR-017: Hybrid material snapshot (fast lookup + audit trail)
            total_weight = material_calc.weight_kg * batch.quantity
            batch.material_weight_kg = round(total_weight, 3)
            batch.material_price_per_kg = material_calc.price_per_kg

            # Rozšířit snapshot_data o material detail (pro audit trail)
            if not batch.snapshot_data:
                batch.snapshot_data = {}
            batch.snapshot_data["material"] = {
                "weight_per_piece_kg": material_calc.weight_kg,
                "total_weight_kg": total_weight,
                "density": material_calc.density,
                "price_per_kg": material_calc.price_per_kg,
                "tier_calculation_timestamp": datetime.now().isoformat(),
            }

        # 3. Načíst Operations pro unit_time_min výpočet (kalkulace už má operace)
        operations_stmt = (
            select(Operation)
            .where(Operation.part_id == part.id, Operation.deleted_at.is_(None))
            .order_by(Operation.seq)
        )
        operations_result = await db.execute(operations_stmt)
        operations = operations_result.scalars().all()

        # 4. Vypočítat batch prices (NOVÁ KALKULACE - ADR-016)
        breakdown = await calculate_part_price(
            part=part,
            quantity=batch.quantity,
            db=db
        )

        # 5. Mapovat PriceBreakdown → Batch fields (za kus!)
        # Material: již obsahuje stock_coefficient
        batch.material_cost = breakdown.material_cost / batch.quantity if batch.quantity > 0 else 0.0

        # Stroje: operace + setup (BEZ režie/marže)
        batch.machining_cost = breakdown.machine_operation_cost / batch.quantity if batch.quantity > 0 else 0.0
        batch.setup_cost = breakdown.machine_setup_cost / batch.quantity if batch.quantity > 0 else 0.0

        # Režie a marže: pouze přirážky (computed properties)
        batch.overhead_cost = breakdown.overhead_markup / batch.quantity if batch.quantity > 0 else 0.0
        batch.margin_cost = breakdown.margin_markup / batch.quantity if batch.quantity > 0 else 0.0

        # Kooperace: již obsahuje coop_coefficient
        batch.coop_cost = breakdown.coop_cost / batch.quantity if batch.quantity > 0 else 0.0

        # Celkem
        batch.unit_cost = breakdown.cost_per_piece
        batch.total_cost = breakdown.total_cost

        # unit_time_min = součet operation_time_min (bez setup, bez coop)
        batch.unit_time_min = sum(
            op.operation_time_min or 0.0
            for op in operations
            if not op.is_coop
        )

        # Logging (batch.id může být None pokud není flushed)
        log_extra = {
            "part_id": batch.part_id,
            "material": batch.material_cost,
            "machining": batch.machining_cost,
            "setup": batch.setup_cost,
            "coop": batch.coop_cost,
        }
        if batch.id:
            log_extra["batch_id"] = batch.id

        logger.info(
            f"Recalculated batch costs: quantity={batch.quantity}, "
            f"unit_cost={batch.unit_cost} Kč, total_cost={batch.total_cost} Kč",
            extra=log_extra
        )

        return batch
    except Exception as e:
        # Prepare error log extra (batch.id může být None)
        error_extra = {
            "part_id": batch.part_id,
            "quantity": batch.quantity,
            "error": str(e),
            "error_type": type(e).__name__
        }
        if batch.id:
            error_extra["batch_id"] = batch.id

        logger.error(
            f"CRITICAL: Batch recalculation failed for batch_id={batch.id or 'NEW'}, part_id={batch.part_id}",
            exc_info=True,
            extra=error_extra
        )
        # Re-raise aby caller mohl handlovat
        raise
