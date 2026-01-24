"""GESTIMA - Snapshot service for batch freezing (ADR-012)"""

from datetime import datetime
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.batch import Batch
from app.models.part import Part


async def create_batch_snapshot(
    batch: Batch,
    username: str,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Vytvoří minimal snapshot pro zmrazení cen batche.

    Snapshot obsahuje:
    - frozen_at, frozen_by
    - costs (material_cost, machining_cost, setup_cost, coop_cost, unit_cost, total_cost)
    - metadata (material_code, material_price_per_kg, part_number)

    Args:
        batch: Batch instance (s loaded part.material_item.group)
        username: Uživatel provádějící freeze
        db: AsyncSession

    Returns:
        Dict[str, Any]: Snapshot data (JSON structure)
    """
    # Načíst part s material_item a group (pokud nejsou eager loaded)
    if not hasattr(batch, 'part') or not batch.part:
        from sqlalchemy import select
        stmt = select(Batch).where(Batch.id == batch.id).options(
            selectinload(Batch.part).selectinload(Part.material_item).selectinload('group')
        )
        result = await db.execute(stmt)
        batch = result.scalar_one()

    part = batch.part
    material_item = part.material_item if hasattr(part, 'material_item') else None
    material_group = material_item.group if material_item and hasattr(material_item, 'group') else None

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
            "material_price_per_kg": material_item.price_per_kg if material_item else None,
        }
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
