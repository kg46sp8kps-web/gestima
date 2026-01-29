#!/usr/bin/env python3
"""GESTIMA - Seed DEMO PARTS (simple, without batches)"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import async_session
from app.models import Part, MaterialItem, MaterialInput
from app.models.enums import StockShape
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

        # Demo parts (lean Part - bez materiálu)
        demo_parts = [
            {
                "part_number": part_numbers[0],
                "article_number": "ART-001",
                "name": "Demo Hřídel 1",
                "length": 85.0,
                "notes": "DEMO part 1",
                "created_by": "seed",
                "updated_by": "seed",
            },
            {
                "part_number": part_numbers[1],
                "article_number": "ART-002",
                "name": "Demo Pouzdro",
                "length": 45.0,
                "notes": "DEMO part 2",
                "created_by": "seed",
                "updated_by": "seed",
            },
            {
                "part_number": part_numbers[2],
                "article_number": "ART-003",
                "name": "Demo Šroub",
                "length": 25.0,
                "notes": "DEMO part 3",
                "created_by": "seed",
                "updated_by": "seed",
            },
        ]

        # Material inputs (separátně)
        material_inputs_data = [
            {"material_idx": 0, "stock_diameter": 40.0, "stock_length": 100.0},
            {"material_idx": 1, "stock_diameter": 30.0, "stock_length": 50.0},
            {"material_idx": 2, "stock_diameter": 20.0, "stock_length": 30.0},
        ]

        created = 0
        for idx, part_data in enumerate(demo_parts):
            # Check if exists
            result = await db.execute(
                select(Part).where(Part.part_number == part_data["part_number"])
            )
            if result.scalar_one_or_none():
                print(f"⏭️  {part_data['part_number']} - již existuje")
                continue

            # Create Part
            part = Part(**part_data)
            db.add(part)
            await db.flush()  # Get part.id

            # Create MaterialInput
            material_input_data = material_inputs_data[idx]
            material_idx = material_input_data["material_idx"]
            material_item = materials[material_idx] if material_idx < len(materials) else materials[0]

            material_input = MaterialInput(
                part_id=part.id,
                seq=0,
                price_category_id=material_item.price_category_id,  # Z MaterialItem
                material_item_id=material_item.id,
                stock_shape=StockShape.ROUND_BAR,  # Všechny demo parts jsou tyče
                stock_diameter=material_input_data["stock_diameter"],
                stock_length=material_input_data["stock_length"],
                quantity=1,
                created_by="seed",
                updated_by="seed",
            )
            db.add(material_input)

            created += 1
            print(f"✅ {part_data['part_number']}: {part_data['name']} + MaterialInput")

        # Commit only if we own the session
        if own_session:
            await db.commit()

        print(f"\n📊 Vytvořeno {created} demo parts (+ MaterialInputs)!")
        print("🚀 Teď by měly být vidět v /parts")

        return created
    finally:
        if own_session:
            await session.__aexit__(None, None, None)


if __name__ == "__main__":
    print("🌱 Seed Demo Parts\n")
    asyncio.run(seed_demo_parts())
