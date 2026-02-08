"""Seed MaterialPriceCategory with 8-digit codes from Infor analysis V2 (Clean)

Based on test_preview_price_categories_v2.py analysis:
- 43 unique MaterialGroup + Shape combinations (reduced from 53)
- Generic material group names (Hliník = all 3000-3400 series)
- 8-digit codes: 20900000-20900042 (sub-range: 20900000-20909999)
- Split SQUARE_BAR / FLAT_BAR (from HR shape)
- DE = deska (NOT plech!)
- 4 steel types only (auto, konstrukční, legovaná, nástrojová)
- Added Plasty

Date: 2026-02-03
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.material import MaterialGroup, MaterialPriceCategory
from app.models.enums import StockShape


# Generated from test_preview_price_categories_v2.py (2026-02-03) - CLEAN VERSION
# 43 categories with 8-digit codes (20900000-20900042)
# Only 4 steel types + Plasty
PRICE_CATEGORIES_V2 = [
    # Hliník (generic - all 3.0-3.4 series combined)
    {'code': '20900000', 'name': 'Hliník - deska', 'group_name': 'Hliník', 'shape': StockShape.PLATE},
    {'code': '20900001', 'name': 'Hliník - tyč kruhová', 'group_name': 'Hliník', 'shape': StockShape.ROUND_BAR},
    {'code': '20900002', 'name': 'Hliník - tyč plochá', 'group_name': 'Hliník', 'shape': StockShape.FLAT_BAR},
    {'code': '20900003', 'name': 'Hliník - tyč čtvercová', 'group_name': 'Hliník', 'shape': StockShape.SQUARE_BAR},
    {'code': '20900004', 'name': 'Hliník - trubka', 'group_name': 'Hliník', 'shape': StockShape.TUBE},
    {'code': '20900005', 'name': 'Hliník - tyč šestihranná', 'group_name': 'Hliník', 'shape': StockShape.HEXAGONAL_BAR},

    # Mosaz
    {'code': '20900006', 'name': 'Mosaz - tyč kruhová', 'group_name': 'Mosaz', 'shape': StockShape.ROUND_BAR},
    {'code': '20900007', 'name': 'Mosaz - tyč plochá', 'group_name': 'Mosaz', 'shape': StockShape.FLAT_BAR},
    {'code': '20900008', 'name': 'Mosaz - tyč čtvercová', 'group_name': 'Mosaz', 'shape': StockShape.SQUARE_BAR},
    {'code': '20900009', 'name': 'Mosaz - trubka', 'group_name': 'Mosaz', 'shape': StockShape.TUBE},

    # Měď
    {'code': '20900010', 'name': 'Měď - deska', 'group_name': 'Měď', 'shape': StockShape.PLATE},
    {'code': '20900011', 'name': 'Měď - tyč kruhová', 'group_name': 'Měď', 'shape': StockShape.ROUND_BAR},
    {'code': '20900012', 'name': 'Měď - tyč plochá', 'group_name': 'Měď', 'shape': StockShape.FLAT_BAR},
    {'code': '20900013', 'name': 'Měď - tyč čtvercová', 'group_name': 'Měď', 'shape': StockShape.SQUARE_BAR},
    {'code': '20900014', 'name': 'Měď - trubka', 'group_name': 'Měď', 'shape': StockShape.TUBE},
    {'code': '20900015', 'name': 'Měď - tyč šestihranná', 'group_name': 'Měď', 'shape': StockShape.HEXAGONAL_BAR},

    # Nerez
    {'code': '20900016', 'name': 'Nerez - deska', 'group_name': 'Nerez', 'shape': StockShape.PLATE},
    {'code': '20900017', 'name': 'Nerez - tyč kruhová', 'group_name': 'Nerez', 'shape': StockShape.ROUND_BAR},
    {'code': '20900018', 'name': 'Nerez - tyč plochá', 'group_name': 'Nerez', 'shape': StockShape.FLAT_BAR},
    {'code': '20900019', 'name': 'Nerez - tyč čtvercová', 'group_name': 'Nerez', 'shape': StockShape.SQUARE_BAR},
    {'code': '20900020', 'name': 'Nerez - trubka', 'group_name': 'Nerez', 'shape': StockShape.TUBE},
    {'code': '20900021', 'name': 'Nerez - tyč šestihranná', 'group_name': 'Nerez', 'shape': StockShape.HEXAGONAL_BAR},

    # Ocel automatová
    {'code': '20900022', 'name': 'Ocel automatová - tyč kruhová', 'group_name': 'Ocel automatová', 'shape': StockShape.ROUND_BAR},
    {'code': '20900023', 'name': 'Ocel automatová - tyč plochá', 'group_name': 'Ocel automatová', 'shape': StockShape.FLAT_BAR},
    {'code': '20900024', 'name': 'Ocel automatová - tyč čtvercová', 'group_name': 'Ocel automatová', 'shape': StockShape.SQUARE_BAR},

    # Ocel konstrukční
    {'code': '20900025', 'name': 'Ocel konstrukční - deska', 'group_name': 'Ocel konstrukční', 'shape': StockShape.PLATE},
    {'code': '20900026', 'name': 'Ocel konstrukční - tyč kruhová', 'group_name': 'Ocel konstrukční', 'shape': StockShape.ROUND_BAR},
    {'code': '20900027', 'name': 'Ocel konstrukční - tyč plochá', 'group_name': 'Ocel konstrukční', 'shape': StockShape.FLAT_BAR},
    {'code': '20900028', 'name': 'Ocel konstrukční - tyč čtvercová', 'group_name': 'Ocel konstrukční', 'shape': StockShape.SQUARE_BAR},
    {'code': '20900029', 'name': 'Ocel konstrukční - trubka', 'group_name': 'Ocel konstrukční', 'shape': StockShape.TUBE},
    {'code': '20900030', 'name': 'Ocel konstrukční - tyč šestihranná', 'group_name': 'Ocel konstrukční', 'shape': StockShape.HEXAGONAL_BAR},

    # Ocel legovaná
    {'code': '20900031', 'name': 'Ocel legovaná - tyč kruhová', 'group_name': 'Ocel legovaná', 'shape': StockShape.ROUND_BAR},
    {'code': '20900032', 'name': 'Ocel legovaná - tyč plochá', 'group_name': 'Ocel legovaná', 'shape': StockShape.FLAT_BAR},
    {'code': '20900033', 'name': 'Ocel legovaná - tyč čtvercová', 'group_name': 'Ocel legovaná', 'shape': StockShape.SQUARE_BAR},

    # Ocel nástrojová
    {'code': '20900034', 'name': 'Ocel nástrojová - deska', 'group_name': 'Ocel nástrojová', 'shape': StockShape.PLATE},
    {'code': '20900035', 'name': 'Ocel nástrojová - tyč kruhová', 'group_name': 'Ocel nástrojová', 'shape': StockShape.ROUND_BAR},
    {'code': '20900036', 'name': 'Ocel nástrojová - tyč plochá', 'group_name': 'Ocel nástrojová', 'shape': StockShape.FLAT_BAR},
    {'code': '20900037', 'name': 'Ocel nástrojová - tyč čtvercová', 'group_name': 'Ocel nástrojová', 'shape': StockShape.SQUARE_BAR},

    # Plasty
    {'code': '20900038', 'name': 'Plasty - deska', 'group_name': 'Plasty', 'shape': StockShape.PLATE},
    {'code': '20900039', 'name': 'Plasty - tyč kruhová', 'group_name': 'Plasty', 'shape': StockShape.ROUND_BAR},
    {'code': '20900040', 'name': 'Plasty - tyč plochá', 'group_name': 'Plasty', 'shape': StockShape.FLAT_BAR},
    {'code': '20900041', 'name': 'Plasty - tyč čtvercová', 'group_name': 'Plasty', 'shape': StockShape.SQUARE_BAR},
    {'code': '20900042', 'name': 'Plasty - tyč šestihranná', 'group_name': 'Plasty', 'shape': StockShape.HEXAGONAL_BAR},
]


async def seed_price_categories_v2(db: AsyncSession):
    """Seed MaterialPriceCategory with 8-digit codes (V2)"""

    print("=" * 100)
    print("🌱 Seeding MaterialPriceCategory V2 (8-digit codes - CLEAN)")
    print("=" * 100)
    print()
    print(f"   • Total categories: {len(PRICE_CATEGORIES_V2)}")
    print(f"   • Code range: 20900000-20900042 (sub-range: 20900000-20909999)")
    print(f"   • Generic names (Hliník = all 3.0-3.4 series)")
    print(f"   • Split SQUARE_BAR / FLAT_BAR")
    print(f"   • DE = deska (NOT plech!)")
    print(f"   • 4 steel types only + Plasty")
    print()

    # Load all MaterialGroups
    result = await db.execute(select(MaterialGroup))
    groups = list(result.scalars().all())

    print(f"✅ Found {len(groups)} MaterialGroups")
    print()

    created_count = 0
    skipped_count = 0
    error_count = 0

    for cat_data in PRICE_CATEGORIES_V2:
        # Find MaterialGroup by name (since codes are now 8-digit numbers)
        group_name = cat_data['group_name']

        # Find matching group by name
        material_group = None
        for group in groups:
            if group.name == group_name:
                material_group = group
                break

        if not material_group:
            print(f"⚠️  MaterialGroup not found for name: {group_name} (category: {cat_data['name']})")
            error_count += 1
            continue

        # Check if exists
        existing = await db.execute(
            select(MaterialPriceCategory)
            .where(MaterialPriceCategory.code == cat_data['code'])
        )

        if existing.scalar_one_or_none():
            print(f"⏭️  [{cat_data['code']}] Already exists: {cat_data['name']}")
            skipped_count += 1
            continue

        # Create new
        new_category = MaterialPriceCategory(
            code=cat_data['code'],
            name=cat_data['name'],
            material_group_id=material_group.id
        )

        db.add(new_category)
        print(f"✅ [{cat_data['code']}] Created: {cat_data['name']} → {material_group.name}")
        created_count += 1

    await db.commit()

    print()
    print("=" * 100)
    print("✅ Seeding complete!")
    print("=" * 100)
    print(f"   Created: {created_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Errors:  {error_count}")
    print(f"   Total:   {len(PRICE_CATEGORIES_V2)}")
    print()
    print("📊 Next steps:")
    print("   1. Verify categories: SELECT * FROM material_price_categories ORDER BY code;")
    print("   2. Fill in price tiers: data/material_price_tiers_template.csv")
    print("   3. Import price tiers: python scripts/import_price_tiers_from_csv.py data/material_price_tiers_template.csv")
    print("   4. Run Infor material import to populate MaterialItems")
    print()


async def main():
    async with async_session() as db:
        await seed_price_categories_v2(db)


if __name__ == "__main__":
    asyncio.run(main())
