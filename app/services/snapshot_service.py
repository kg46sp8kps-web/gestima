"""GESTIMA - Snapshot service for batch freezing (ADR-012)"""

import logging
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from app.models.batch import Batch
from app.models.part import Part

logger = logging.getLogger(__name__)


async def create_batch_snapshot(
    batch: Batch,
    username: str,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Vytvoří minimal snapshot pro zmrazení cen batche (ADR-012, ADR-014).

    Snapshot obsahuje:
    - frozen_at, frozen_by
    - costs (material_cost, machining_cost, setup_cost, coop_cost, unit_cost, total_cost)
    - metadata (material_code, material_price_per_kg, part_number)

    Args:
        batch: Batch instance (s loaded part.material_item.group + price_category)
        username: Uživatel provádějící freeze
        db: AsyncSession

    Returns:
        Dict[str, Any]: Snapshot data (JSON structure)
    """
    # Načíst part s material_item, group a price_category (pokud nejsou eager loaded)
    try:
        if not hasattr(batch, 'part') or not batch.part:
            from sqlalchemy import select
            from app.models.material import MaterialItem
            from app.models.material_input import MaterialInput
            stmt = select(Batch).where(Batch.id == batch.id).options(
                selectinload(Batch.part)
                .selectinload(Part.material_inputs)
                .selectinload(MaterialInput.material_item)
                .selectinload(MaterialItem.group),
                selectinload(Batch.part)
                .selectinload(Part.material_inputs)
                .selectinload(MaterialInput.price_category)
            )
            result = await db.execute(stmt)
            loaded_batch = result.scalar_one_or_none()
            if not loaded_batch:
                raise ValueError(f"Batch not found")
            batch = loaded_batch
    except SQLAlchemyError as e:
        logger.error(f"Database error loading batch for snapshot: {e}", exc_info=True)
        raise ValueError(f"Failed to load batch data for snapshot: {e}")

    part = batch.part
    material_item = part.material_item if hasattr(part, 'material_item') else None
    material_group = material_item.group if material_item and hasattr(material_item, 'group') else None

    # ADR-014: Získat price_per_kg který byl použit pro výpočet batche
    material_price_per_kg = None
    if material_item:
        try:
            from app.services.price_calculator import calculate_stock_cost_from_part
            # Vypočítat stock cost s quantity batche pro získání správného tier price
            stock_cost = await calculate_stock_cost_from_part(part, batch.quantity, db)
            material_price_per_kg = stock_cost.price_per_kg
        except Exception as e:
            logger.warning(f"Failed to calculate price_per_kg for snapshot: {e}", exc_info=True)
            # Fallback: použít průměr z tiers nebo None
            material_price_per_kg = None

    # Sbírat varování o podezřelých hodnotách (neblokovat freeze)
    # Kontrolujeme jen finální výsledky (costs), ne intermediate hodnoty
    warnings = []

    if batch.material_cost <= 0:
        warnings.append(f"Náklady na materiál: {batch.material_cost} Kč")

    if batch.machining_cost <= 0:
        warnings.append(f"Náklady na obrábění: {batch.machining_cost} Kč")

    if batch.total_cost <= 0:
        warnings.append(f"Celkové náklady: {batch.total_cost} Kč")

    # Logovat varování pro audit
    if warnings:
        logger.warning(
            f"Freezing batch {batch.id} with suspicious values",
            extra={
                "batch_id": batch.id,
                "part_id": batch.part_id,
                "warnings": warnings,
                "user": username
            }
        )

    # Sestavit snapshot
    snapshot = {
        "frozen_at": datetime.utcnow().isoformat(),
        "frozen_by": username,
        "costs": {
            "material_cost": batch.material_cost,
            "machining_cost": batch.machining_cost,
            "setup_cost": batch.setup_cost,
            "coop_cost": batch.coop_cost,
            "unit_cost": batch.unit_cost,
            "total_cost": batch.total_cost,
        },
        "metadata": {
            "part_number": part.part_number,
            "quantity": batch.quantity,
            "material_code": material_group.code if material_group else None,
            "material_price_per_kg": material_price_per_kg,  # ADR-014: Dynamic tier price
        },
        "warnings": warnings  # Uložit varování do snapshotu (pro UI)
    }

    return snapshot


def get_batch_costs(batch: Batch) -> Dict[str, float]:
    """
    Vrátí ceny batche - buď ze snapshotu (pokud je frozen) nebo live ceny.

    Args:
        batch: Batch instance

    Returns:
        Dict[str, float]: {material_cost, machining_cost, setup_cost, coop_cost, unit_cost, total_cost}
    """
    if batch.is_frozen and batch.snapshot_data:
        # Použít ceny ze snapshotu
        return batch.snapshot_data.get("costs", {})
    else:
        # Použít live ceny (aktuální stav)
        return {
            "material_cost": batch.material_cost,
            "machining_cost": batch.machining_cost,
            "setup_cost": batch.setup_cost,
            "coop_cost": batch.coop_cost,
            "unit_cost": batch.unit_cost,
            "total_cost": batch.total_cost,
        }
