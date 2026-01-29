"""GESTIMA - Seed data for development/demo

Tento skript vytváří demo data při každém startu aplikace.
Demo záznamy mají v notes "DEMO" pro snadnou identifikaci a mazání.

KRITICKÉ: Demo data MUSÍ dodržovat ADR-017 v2.0 (8-digit random numbering: 10XXXXXX)
"""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.part import Part
from app.models.material import MaterialItem
from app.services.number_generator import NumberGenerator

logger = logging.getLogger(__name__)


async def seed_demo_parts(db: AsyncSession):
    """Vytvoř demo parts pokud neexistují

    Demo parts mají v notes "DEMO" a dají se snadno smazat a znovu vytvořit.

    IMPORTANT: Uses NumberGenerator to comply with ADR-017 v2.0 (8-digit format: 10XXXXXX)
    """
    try:
        # Zjisti jestli máme nějaký materiál
        result = await db.execute(select(MaterialItem).limit(1))
        material = result.scalar_one_or_none()

        if not material:
            logger.warning("No materials found - skipping demo parts creation")
            return

        # Check if demo parts already exist (by notes="DEMO")
        result = await db.execute(
            select(Part).where(Part.notes.like("%DEMO - Vzorový díl%"))
        )
        existing_demo = result.scalars().all()

        if len(existing_demo) >= 3:
            logger.debug("Demo parts already exist")
            return

        # Generate 8-digit part numbers (ADR-017 v2.0: 10XXXXXX format)
        part_numbers = await NumberGenerator.generate_part_numbers_batch(db, 3)

        # Demo parts data (WITHOUT hardcoded part_numbers!)
        demo_parts_data = [
            {
                "article_number": "ART-DEMO-001",
                "name": "Demo hřídel",
                "length": 150.0,
                "notes": "DEMO - Vzorový díl pro testování. Můžete smazat a znovu se vytvoří při restartu."
            },
            {
                "article_number": "ART-DEMO-002",
                "name": "Demo pouzdro",
                "length": 80.0,
                "notes": "DEMO - Vzorový díl pro testování. Můžete smazat a znovu se vytvoří při restartu."
            },
            {
                "article_number": None,
                "name": "Demo příruba (bez article)",
                "length": 200.0,
                "notes": "DEMO - Vzorový díl bez article number. Můžete smazat a znovu se vytvoří při restartu."
            },
        ]

        created_count = 0
        for i, data in enumerate(demo_parts_data):
            part = Part(
                part_number=part_numbers[i],  # ADR-017 v2.0 compliant (10XXXXXX)
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
            logger.info(f"✅ Created {created_count} demo parts with ADR-017 compliant numbers: {part_numbers}")
        else:
            logger.debug("Demo parts already exist")

    except Exception as e:
        await db.rollback()
        logger.error(f"Error seeding demo parts: {e}", exc_info=True)
