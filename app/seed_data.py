"""GESTIMA - Seed data for development/demo

Tento skript vytváří demo data při každém startu aplikace.
Demo záznamy mají v notes "DEMO" pro snadnou identifikaci a mazání.
"""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.part import Part
from app.models.material import MaterialItem

logger = logging.getLogger(__name__)


async def seed_demo_parts(db: AsyncSession):
    """Vytvoř demo parts pokud neexistují

    Demo parts mají v notes "DEMO" a dají se snadno smazat a znovu vytvořit.
    """
    try:
        # Zjisti jestli máme nějaký materiál
        result = await db.execute(select(MaterialItem).limit(1))
        material = result.scalar_one_or_none()

        if not material:
            logger.warning("No materials found - skipping demo parts creation")
            return

        # Demo parts (kontrola podle part_number)
        demo_parts_data = [
            {
                "part_number": "DEMO-001",
                "article_number": "ART-DEMO-001",
                "name": "Demo hřídel",
                "length": 150.0,
                "notes": "DEMO - Vzorový díl pro testování. Můžete smazat a znovu se vytvoří při restartu."
            },
            {
                "part_number": "DEMO-002",
                "article_number": "ART-DEMO-002",
                "name": "Demo pouzdro",
                "length": 80.0,
                "notes": "DEMO - Vzorový díl pro testování. Můžete smazat a znovu se vytvoří při restartu."
            },
            {
                "part_number": "DEMO-003",
                "article_number": None,
                "name": "Demo příruba (bez article)",
                "length": 200.0,
                "notes": "DEMO - Vzorový díl bez article number. Můžete smazat a znovu se vytvoří při restartu."
            },
        ]

        created_count = 0
        for data in demo_parts_data:
            # Kontrola existence
            result = await db.execute(
                select(Part).where(Part.part_number == data["part_number"])
            )
            existing = result.scalar_one_or_none()

            if not existing:
                part = Part(
                    part_number=data["part_number"],
                    article_number=data["article_number"],
                    name=data["name"],
                    material_item_id=material.id,
                    length=data["length"],
                    notes=data["notes"],
                    created_by="system_seed"
                )
                db.add(part)
                created_count += 1

        if created_count > 0:
            await db.commit()
            logger.info(f"✅ Created {created_count} demo parts")
        else:
            logger.debug("Demo parts already exist")

    except Exception as e:
        await db.rollback()
        logger.error(f"Error seeding demo parts: {e}", exc_info=True)
