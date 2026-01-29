#!/usr/bin/env python3
"""
GESTIMA - Seed Material Items (konkrétní skladové položky)

Vytvoří demo MaterialItems pro testování Parts.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import async_session
from app.models.material import MaterialGroup, MaterialPriceCategory, MaterialItem


# Demo material items (konkrétní skladové položky)
DEMO_ITEMS = [
    {
        "material_number": "20001001",  # 8-digit: 20XXXXXX (Materials prefix)
        "code": "C45-ROUND-20",
        "name": "C45 Tyč kruhová Ø20",
        "shape": "round_bar",
        "diameter": 20.0,
        "standard_length": 3000.0,
        "weight_per_meter": 2.47,  # 20mm diameter steel ~ 2.47 kg/m
        "norms": "1.0503, C45, 12050",
        "supplier": "Demo Supplier",
        "stock_available": True,
        "group_code": "OCEL-KONS",
        "category_code": "OCEL-KONS-KRUHOVA",
    },
    {
        "material_number": "20001002",  # 8-digit: 20XXXXXX (Materials prefix)
        "code": "C45-ROUND-30",
        "name": "C45 Tyč kruhová Ø30",
        "shape": "round_bar",
        "diameter": 30.0,
        "standard_length": 3000.0,
        "weight_per_meter": 5.55,  # 30mm diameter steel
        "norms": "1.0503, C45, 12050",
        "supplier": "Demo Supplier",
        "stock_available": True,
        "group_code": "OCEL-KONS",
        "category_code": "OCEL-KONS-KRUHOVA",
    },
    {
        "material_number": "20001003",  # 8-digit: 20XXXXXX (Materials prefix)
        "code": "C45-ROUND-40",
        "name": "C45 Tyč kruhová Ø40",
        "shape": "round_bar",
        "diameter": 40.0,
        "standard_length": 3000.0,
        "weight_per_meter": 9.87,  # 40mm diameter steel
        "norms": "1.0503, C45, 12050",
        "supplier": "Demo Supplier",
        "stock_available": True,
        "group_code": "OCEL-KONS",
        "category_code": "OCEL-KONS-KRUHOVA",
    },
    {
        "material_number": "20001004",  # 8-digit: 20XXXXXX (Materials prefix)
        "code": "NEREZ-ROUND-20",
        "name": "Nerez 304 Tyč kruhová Ø20",
        "shape": "round_bar",
        "diameter": 20.0,
        "standard_length": 3000.0,
        "weight_per_meter": 2.48,  # Similar to C45 but slightly different density
        "norms": "1.4301, X5CrNi18-10, 304",
        "supplier": "Demo Supplier",
        "stock_available": True,
        "group_code": "NEREZ",
        "category_code": "NEREZ-CTVEREC",  # Using available category
    },
]


async def seed_material_items(session=None):
    """Seed demo material items

    Args:
        session: Optional AsyncSession (pro testy). If None, vytvoří vlastní.

    Returns:
        int: Počet vytvořených items
    """
    # Use provided session or create own
    own_session = session is None
    if own_session:
        session = async_session()
        session = await session.__aenter__()

    try:
        created = 0
        skipped = 0

        for item_data in DEMO_ITEMS:
            # Check if exists
            result = await session.execute(
                select(MaterialItem).where(MaterialItem.code == item_data["code"])
            )
            if result.scalar_one_or_none():
                skipped += 1
                print(f"⏭️  {item_data['code']} - již existuje")
                continue

            # Get material group
            group = await session.execute(
                select(MaterialGroup).where(MaterialGroup.code == item_data["group_code"])
            )
            group = group.scalar_one_or_none()
            if not group:
                print(f"⚠️  {item_data['code']} - chybí MaterialGroup: {item_data['group_code']}")
                continue

            # Get price category
            category = await session.execute(
                select(MaterialPriceCategory).where(
                    MaterialPriceCategory.code == item_data["category_code"]
                )
            )
            category = category.scalar_one_or_none()
            if not category:
                print(f"⚠️  {item_data['code']} - chybí MaterialPriceCategory: {item_data['category_code']}")
                continue

            # Create material item
            item = MaterialItem(
                material_number=item_data["material_number"],
                code=item_data["code"],
                name=item_data["name"],
                shape=item_data["shape"],
                diameter=item_data.get("diameter"),
                standard_length=item_data.get("standard_length"),
                weight_per_meter=item_data.get("weight_per_meter"),
                norms=item_data.get("norms"),
                supplier=item_data.get("supplier"),
                stock_available=item_data.get("stock_available", True),
                material_group_id=group.id,
                price_category_id=category.id,
                created_by="system_seed",
                updated_by="system_seed",
            )
            session.add(item)
            created += 1
            print(f"✅ {item_data['code']} - vytvořeno")

        # Commit only if we own the session
        if own_session:
            await session.commit()

        print(f"\n📊 Seed material items dokončen:")
        print(f"   ✅ Vytvořeno: {created}")
        print(f"   ⏭️  Přeskočeno: {skipped}")
        print(f"   📦 Celkem: {len(DEMO_ITEMS)}")

        return created
    finally:
        if own_session:
            await session.__aexit__(None, None, None)


if __name__ == "__main__":
    print("🌱 Seed Material Items do GESTIMA databáze\n")
    asyncio.run(seed_material_items())
