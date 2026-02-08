"""Seed MaterialGroup cutting parameters for machining time estimation.

ADR-040: Machining Time Estimation System
Migration: t3u4v5w6x7y8

Populates 9 material groups with industrial cutting data:
- OCEL-AUTO (Free-cutting steel, ISO P)
- OCEL-KONS (Structural steel, ISO P)
- OCEL-LEG (Alloy steel, ISO P)
- OCEL-NAST (Tool steel, ISO K)
- NEREZ (Stainless, ISO M)
- HLINIK (Aluminum, ISO N)
- MED (Copper, ISO N)
- MOSAZ (Brass, ISO N)
- LITINA (Cast iron, ISO K)

Data sources: Sandvik Coromant 2024, Iscar 2024, Kennametal 2024
Reference: ISO 3685 (tool life), DIN 6580 (metal cutting)
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session
from app.models.material import MaterialGroup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Material group cutting parameters (9 standard materials)
MATERIAL_GROUPS_CUTTING_DATA = [
    {
        "code": "OCEL-AUTO",
        "name": "Ocel automatová",
        "density": 7.85,
        "iso_group": "P",
        "hardness_hb": 180.0,
        "mrr_turning_roughing": 350.0,
        "mrr_turning_finishing": 200.0,
        "mrr_milling_roughing": 300.0,
        "mrr_milling_finishing": 180.0,
        "cutting_speed_turning": 220.0,
        "cutting_speed_milling": 200.0,
        "feed_turning": 0.35,
        "feed_milling": 0.25,
        "deep_pocket_penalty": 1.5,
        "thin_wall_penalty": 2.2,
        "cutting_data_source": "Sandvik Coromant 2024",
    },
    {
        "code": "OCEL-KONS",
        "name": "Ocel konstrukční",
        "density": 7.85,
        "iso_group": "P",
        "hardness_hb": 200.0,
        "mrr_turning_roughing": 300.0,
        "mrr_turning_finishing": 180.0,
        "mrr_milling_roughing": 250.0,
        "mrr_milling_finishing": 150.0,
        "cutting_speed_turning": 180.0,
        "cutting_speed_milling": 160.0,
        "feed_turning": 0.30,
        "feed_milling": 0.22,
        "deep_pocket_penalty": 1.6,
        "thin_wall_penalty": 2.3,
        "cutting_data_source": "Sandvik Coromant 2024",
    },
    {
        "code": "OCEL-LEG",
        "name": "Ocel legovaná",
        "density": 7.85,
        "iso_group": "P",
        "hardness_hb": 230.0,
        "mrr_turning_roughing": 220.0,
        "mrr_turning_finishing": 120.0,
        "mrr_milling_roughing": 180.0,
        "mrr_milling_finishing": 100.0,
        "cutting_speed_turning": 160.0,
        "cutting_speed_milling": 140.0,
        "feed_turning": 0.28,
        "feed_milling": 0.20,
        "deep_pocket_penalty": 1.8,
        "thin_wall_penalty": 2.5,
        "cutting_data_source": "Iscar 2024",
    },
    {
        "code": "OCEL-NAST",
        "name": "Ocel nástrojová",
        "density": 7.85,
        "iso_group": "K",
        "hardness_hb": 250.0,
        "mrr_turning_roughing": 150.0,
        "mrr_turning_finishing": 80.0,
        "mrr_milling_roughing": 120.0,
        "mrr_milling_finishing": 70.0,
        "cutting_speed_turning": 120.0,
        "cutting_speed_milling": 100.0,
        "feed_turning": 0.22,
        "feed_milling": 0.16,
        "deep_pocket_penalty": 2.2,
        "thin_wall_penalty": 3.0,
        "cutting_data_source": "Kennametal 2024",
    },
    {
        "code": "NEREZ",
        "name": "Nerezová ocel",
        "density": 7.90,
        "iso_group": "M",
        "hardness_hb": 180.0,
        "mrr_turning_roughing": 180.0,
        "mrr_turning_finishing": 100.0,
        "mrr_milling_roughing": 150.0,
        "mrr_milling_finishing": 90.0,
        "cutting_speed_turning": 140.0,
        "cutting_speed_milling": 120.0,
        "feed_turning": 0.25,
        "feed_milling": 0.18,
        "deep_pocket_penalty": 2.0,
        "thin_wall_penalty": 2.8,
        "cutting_data_source": "Sandvik Coromant 2024",
    },
    {
        "code": "HLINIK",
        "name": "Hliník",
        "density": 2.70,
        "iso_group": "N",
        "hardness_hb": 60.0,
        "mrr_turning_roughing": 1000.0,
        "mrr_turning_finishing": 500.0,
        "mrr_milling_roughing": 800.0,
        "mrr_milling_finishing": 400.0,
        "cutting_speed_turning": 350.0,
        "cutting_speed_milling": 300.0,
        "feed_turning": 0.45,
        "feed_milling": 0.35,
        "deep_pocket_penalty": 1.3,
        "thin_wall_penalty": 1.8,
        "cutting_data_source": "Iscar 2024",
    },
    {
        "code": "MED",
        "name": "Měď",
        "density": 8.90,
        "iso_group": "N",
        "hardness_hb": 70.0,
        "mrr_turning_roughing": 600.0,
        "mrr_turning_finishing": 300.0,
        "mrr_milling_roughing": 500.0,
        "mrr_milling_finishing": 250.0,
        "cutting_speed_turning": 200.0,
        "cutting_speed_milling": 180.0,
        "feed_turning": 0.38,
        "feed_milling": 0.28,
        "deep_pocket_penalty": 1.4,
        "thin_wall_penalty": 2.0,
        "cutting_data_source": "Kennametal 2024",
    },
    {
        "code": "MOSAZ",
        "name": "Mosaz",
        "density": 8.50,
        "iso_group": "N",
        "hardness_hb": 90.0,
        "mrr_turning_roughing": 800.0,
        "mrr_turning_finishing": 400.0,
        "mrr_milling_roughing": 650.0,
        "mrr_milling_finishing": 350.0,
        "cutting_speed_turning": 250.0,
        "cutting_speed_milling": 220.0,
        "feed_turning": 0.40,
        "feed_milling": 0.30,
        "deep_pocket_penalty": 1.3,
        "thin_wall_penalty": 1.7,
        "cutting_data_source": "Sandvik Coromant 2024",
    },
    {
        "code": "LITINA",
        "name": "Litina",
        "density": 7.20,
        "iso_group": "K",
        "hardness_hb": 220.0,
        "mrr_turning_roughing": 280.0,
        "mrr_turning_finishing": 160.0,
        "mrr_milling_roughing": 220.0,
        "mrr_milling_finishing": 130.0,
        "cutting_speed_turning": 160.0,
        "cutting_speed_milling": 140.0,
        "feed_turning": 0.32,
        "feed_milling": 0.24,
        "deep_pocket_penalty": 1.7,
        "thin_wall_penalty": 2.4,
        "cutting_data_source": "Iscar 2024",
    },
]


async def seed_material_group_cutting_params(db: AsyncSession) -> None:
    """
    Seed MaterialGroup with cutting parameters.

    Updates existing records or creates new ones.
    Uses try/except/rollback for transaction safety (L-008).
    """
    from sqlalchemy import select

    updated_count = 0
    created_count = 0

    for material_data in MATERIAL_GROUPS_CUTTING_DATA:
        code = material_data["code"]

        # Check if material group exists
        result = await db.execute(select(MaterialGroup).filter(MaterialGroup.code == code))
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing record
            for key, value in material_data.items():
                if key != "code":  # Don't update code
                    setattr(existing, key, value)
            updated_count += 1
            logger.info(f"Updated MaterialGroup: {code}")
        else:
            # Create new record
            new_group = MaterialGroup(**material_data)
            db.add(new_group)
            created_count += 1
            logger.info(f"Created MaterialGroup: {code}")

    # Transaction handling (L-008)
    try:
        await db.commit()
        logger.info(f"✅ Seed completed: {created_count} created, {updated_count} updated")
    except Exception:
        await db.rollback()
        raise


async def main():
    """Run seed script."""
    logger.info("Starting MaterialGroup cutting parameters seed...")

    async with async_session() as db:
        try:
            await seed_material_group_cutting_params(db)
        except Exception as e:
            logger.error(f"❌ Seed failed: {e}", exc_info=True)
            raise

    logger.info("Seed completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
