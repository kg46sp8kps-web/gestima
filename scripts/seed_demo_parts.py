#!/usr/bin/env python3
"""GESTIMA - Seed DEMO PARTS (simple, without batches)"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import async_session
from app.models import Part, MaterialItem
from app.services.number_generator import NumberGenerator
from sqlalchemy import select


async def seed_demo_parts(session=None):
    """Vytvoř demo parts pro zobrazení v UI

    Args:
        session: Optional AsyncSession (pro testy). If None, vytvoří vlastní.

    Returns:
        int: Počet vytvořených parts
    """
    # Use provided session or create own
    own_session = session is None
    if own_session:
        session = async_session()
        session = await session.__aenter__()

    try:
        db = session
        # Get material items
        result = await db.execute(select(MaterialItem).limit(3))
        materials = result.scalars().all()

        if len(materials) == 0:
            print("❌ Chybí MaterialItems! Spusť: python scripts/seed_material_items.py")
            return

        # Generate part numbers
        part_numbers = await NumberGenerator.generate_part_numbers_batch(db, count=3)

        # Demo parts
        demo_parts = [
            {
                "part_number": part_numbers[0],
                "article_number": "ART-001",
                "name": "Demo Hřídel 1",
                "material_item_id": materials[0].id,
                "stock_diameter": 40.0,
                "stock_length": 100.0,
                "length": 85.0,
                "notes": "DEMO part 1",
                "created_by": "seed",
                "updated_by": "seed",
            },
            {
                "part_number": part_numbers[1],
                "article_number": "ART-002",
                "name": "Demo Pouzdro",
                "material_item_id": materials[1].id if len(materials) > 1 else materials[0].id,
                "stock_diameter": 30.0,
                "stock_length": 50.0,
                "length": 45.0,
                "notes": "DEMO part 2",
                "created_by": "seed",
                "updated_by": "seed",
            },
            {
                "part_number": part_numbers[2],
                "article_number": "ART-003",
                "name": "Demo Šroub",
                "material_item_id": materials[2].id if len(materials) > 2 else materials[0].id,
                "stock_diameter": 20.0,
                "stock_length": 30.0,
                "length": 25.0,
                "notes": "DEMO part 3",
                "created_by": "seed",
                "updated_by": "seed",
            },
        ]

        created = 0
        for part_data in demo_parts:
            # Check if exists
            result = await db.execute(
                select(Part).where(Part.part_number == part_data["part_number"])
            )
            if result.scalar_one_or_none():
                print(f"⏭️  {part_data['part_number']} - již existuje")
                continue

            part = Part(**part_data)
            db.add(part)
            created += 1
            print(f"✅ {part_data['part_number']}: {part_data['name']}")

        # Commit only if we own the session
        if own_session:
            await db.commit()

        print(f"\n📊 Vytvořeno {created} demo parts!")
        print("🚀 Teď by měly být vidět v /parts")

        return created
    finally:
        if own_session:
            await session.__aexit__(None, None, None)


if __name__ == "__main__":
    print("🌱 Seed Demo Parts\n")
    asyncio.run(seed_demo_parts())
