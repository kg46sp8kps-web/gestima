"""Seed MaterialPriceCategory from Infor data analysis"""

import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_engine, async_session
from app.models.material import MaterialGroup, MaterialPriceCategory
from app.models.enums import StockShape


# Generated from test_material_group_shape_combinations.py
PRICE_CATEGORIES = [
    # Hliník 3000
    {'code': 'HLINIK-3000-ROUND-BAR', 'name': 'Hliník 3000 - tyč kruhová', 'group_code': '3.0xxx', 'shape': StockShape.ROUND_BAR},
    {'code': 'HLINIK-3000-SQUARE-BAR', 'name': 'Hliník 3000 - tyč čtvercová/plochá', 'group_code': '3.0xxx', 'shape': StockShape.FLAT_BAR},

    # Hliník 3100
    {'code': 'HLINIK-3100-HEXAGONAL-BAR', 'name': 'Hliník 3100 - tyč šestihranná', 'group_code': '3.1xxx', 'shape': StockShape.HEXAGONAL_BAR},
    {'code': 'HLINIK-3100-PLATE', 'name': 'Hliník 3100 - plech', 'group_code': '3.1xxx', 'shape': StockShape.PLATE},
    {'code': 'HLINIK-3100-ROUND-BAR', 'name': 'Hliník 3100 - tyč kruhová', 'group_code': '3.1xxx', 'shape': StockShape.ROUND_BAR},
    {'code': 'HLINIK-3100-SQUARE-BAR', 'name': 'Hliník 3100 - tyč čtvercová/plochá', 'group_code': '3.1xxx', 'shape': StockShape.FLAT_BAR},
    {'code': 'HLINIK-3100-TUBE', 'name': 'Hliník 3100 - trubka', 'group_code': '3.1xxx', 'shape': StockShape.TUBE},

    # Hliník 3200
    {'code': 'HLINIK-3200-PLATE', 'name': 'Hliník 3200 - plech', 'group_code': '3.2xxx', 'shape': StockShape.PLATE},
    {'code': 'HLINIK-3200-ROUND-BAR', 'name': 'Hliník 3200 - tyč kruhová', 'group_code': '3.2xxx', 'shape': StockShape.ROUND_BAR},
    {'code': 'HLINIK-3200-SQUARE-BAR', 'name': 'Hliník 3200 - tyč čtvercová/plochá', 'group_code': '3.2xxx', 'shape': StockShape.FLAT_BAR},
    {'code': 'HLINIK-3200-TUBE', 'name': 'Hliník 3200 - trubka', 'group_code': '3.2xxx', 'shape': StockShape.TUBE},

    # Hliník 3300
    {'code': 'HLINIK-3300-PLATE', 'name': 'Hliník 3300 - plech', 'group_code': '3.3xxx', 'shape': StockShape.PLATE},
    {'code': 'HLINIK-3300-ROUND-BAR', 'name': 'Hliník 3300 - tyč kruhová', 'group_code': '3.3xxx', 'shape': StockShape.ROUND_BAR},
    {'code': 'HLINIK-3300-SQUARE-BAR', 'name': 'Hliník 3300 - tyč čtvercová/plochá', 'group_code': '3.3xxx', 'shape': StockShape.FLAT_BAR},
    {'code': 'HLINIK-3300-TUBE', 'name': 'Hliník 3300 - trubka', 'group_code': '3.3xxx', 'shape': StockShape.TUBE},

    # Hliník 3400
    {'code': 'HLINIK-3400-PLATE', 'name': 'Hliník 3400 - plech', 'group_code': '3.4xxx', 'shape': StockShape.PLATE},
    {'code': 'HLINIK-3400-ROUND-BAR', 'name': 'Hliník 3400 - tyč kruhová', 'group_code': '3.4xxx', 'shape': StockShape.ROUND_BAR},
    {'code': 'HLINIK-3400-SQUARE-BAR', 'name': 'Hliník 3400 - tyč čtvercová/plochá', 'group_code': '3.4xxx', 'shape': StockShape.FLAT_BAR},

    # Mosaz
    {'code': 'MOSAZ-ROUND-BAR', 'name': 'Mosaz - tyč kruhová', 'group_code': '21xxx', 'shape': StockShape.ROUND_BAR},
    {'code': 'MOSAZ-SQUARE-BAR', 'name': 'Mosaz - tyč čtvercová/plochá', 'group_code': '21xxx', 'shape': StockShape.FLAT_BAR},
    {'code': 'MOSAZ-TUBE', 'name': 'Mosaz - trubka', 'group_code': '21xxx', 'shape': StockShape.TUBE},

    # Měď
    {'code': 'MED-HEXAGONAL-BAR', 'name': 'Měď - tyč šestihranná', 'group_code': '20xxx', 'shape': StockShape.HEXAGONAL_BAR},
    {'code': 'MED-PLATE', 'name': 'Měď - plech', 'group_code': '20xxx', 'shape': StockShape.PLATE},
    {'code': 'MED-ROUND-BAR', 'name': 'Měď - tyč kruhová', 'group_code': '20xxx', 'shape': StockShape.ROUND_BAR},
    {'code': 'MED-SQUARE-BAR', 'name': 'Měď - tyč čtvercová/plochá', 'group_code': '20xxx', 'shape': StockShape.FLAT_BAR},
    {'code': 'MED-TUBE', 'name': 'Měď - trubka', 'group_code': '20xxx', 'shape': StockShape.TUBE},

    # Nerez
    {'code': 'NEREZ-HEXAGONAL-BAR', 'name': 'Nerez - tyč šestihranná', 'group_code': '14xxx', 'shape': StockShape.HEXAGONAL_BAR},
    {'code': 'NEREZ-PLATE', 'name': 'Nerez - plech', 'group_code': '14xxx', 'shape': StockShape.PLATE},
    {'code': 'NEREZ-ROUND-BAR', 'name': 'Nerez - tyč kruhová', 'group_code': '14xxx', 'shape': StockShape.ROUND_BAR},
    {'code': 'NEREZ-SQUARE-BAR', 'name': 'Nerez - tyč čtvercová/plochá', 'group_code': '14xxx', 'shape': StockShape.FLAT_BAR},
    {'code': 'NEREZ-TUBE', 'name': 'Nerez - trubka', 'group_code': '14xxx', 'shape': StockShape.TUBE},

    # Ocel automatová
    {'code': 'OCEL-AUTO-ROUND-BAR', 'name': 'Ocel automatová - tyč kruhová', 'group_code': '11xxx', 'shape': StockShape.ROUND_BAR},
    {'code': 'OCEL-AUTO-SQUARE-BAR', 'name': 'Ocel automatová - tyč čtvercová/plochá', 'group_code': '11xxx', 'shape': StockShape.FLAT_BAR},

    # Ocel konstrukční
    {'code': 'OCEL-KONS-HEXAGONAL-BAR', 'name': 'Ocel konstrukční - tyč šestihranná', 'group_code': '10xxx', 'shape': StockShape.HEXAGONAL_BAR},
    {'code': 'OCEL-KONS-PLATE', 'name': 'Ocel konstrukční - plech', 'group_code': '10xxx', 'shape': StockShape.PLATE},
    {'code': 'OCEL-KONS-ROUND-BAR', 'name': 'Ocel konstrukční - tyč kruhová', 'group_code': '10xxx', 'shape': StockShape.ROUND_BAR},
    {'code': 'OCEL-KONS-SQUARE-BAR', 'name': 'Ocel konstrukční - tyč čtvercová/plochá', 'group_code': '10xxx', 'shape': StockShape.FLAT_BAR},
    {'code': 'OCEL-KONS-TUBE', 'name': 'Ocel konstrukční - trubka', 'group_code': '10xxx', 'shape': StockShape.TUBE},

    # Ocel nástrojová
    {'code': 'OCEL-NASTROJ-PLATE', 'name': 'Ocel nástrojová - plech', 'group_code': '12xxx', 'shape': StockShape.PLATE},
    {'code': 'OCEL-NASTROJ-ROUND-BAR', 'name': 'Ocel nástrojová - tyč kruhová', 'group_code': '12xxx', 'shape': StockShape.ROUND_BAR},
    {'code': 'OCEL-NASTROJ-SQUARE-BAR', 'name': 'Ocel nástrojová - tyč čtvercová/plochá', 'group_code': '12xxx', 'shape': StockShape.FLAT_BAR},
]


async def seed_price_categories(db: AsyncSession):
    """Seed MaterialPriceCategory from Infor analysis"""

    print("🌱 Seeding MaterialPriceCategory from Infor data...")
    print()

    # Load all MaterialGroups
    result = await db.execute(select(MaterialGroup))
    groups = {g.code: g for g in result.scalars().all()}

    print(f"✅ Found {len(groups)} MaterialGroups")
    print()

    created_count = 0
    skipped_count = 0

    for cat_data in PRICE_CATEGORIES:
        # Find MaterialGroup by code pattern
        group_code = cat_data['group_code']
        material_group = None

        for code, group in groups.items():
            if code.startswith(group_code.replace('xxx', '')) or code == group_code:
                material_group = group
                break

        if not material_group:
            print(f"⚠️  MaterialGroup not found for: {cat_data['name']} (code: {group_code})")
            skipped_count += 1
            continue

        # Check if exists
        existing = await db.execute(
            select(MaterialPriceCategory)
            .where(MaterialPriceCategory.code == cat_data['code'])
        )

        if existing.scalar_one_or_none():
            print(f"⏭️  Skipping existing: {cat_data['code']}")
            skipped_count += 1
            continue

        # Create new
        new_category = MaterialPriceCategory(
            code=cat_data['code'],
            name=cat_data['name'],
            material_group_id=material_group.id
        )

        db.add(new_category)
        print(f"✅ Created: {cat_data['code']} → {cat_data['name']}")
        created_count += 1

    await db.commit()

    print()
    print("=" * 80)
    print(f"✅ Seeding complete!")
    print(f"   Created: {created_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Total:   {len(PRICE_CATEGORIES)}")


async def main():
    async with async_session() as db:
        await seed_price_categories(db)


if __name__ == "__main__":
    asyncio.run(main())
