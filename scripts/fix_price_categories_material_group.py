#!/usr/bin/env python3
"""
Data Migration: Fix missing material_group_id in MaterialPriceCategory

ROOT CAUSE FIX:
- Původní seed script nevyplňoval material_group_id
- To způsobovalo TypeError při výpočtu batch costs (density = None)
- Tento script opraví existující data v DB

Spuštění:
    python -m scripts.fix_price_categories_material_group
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session
from app.models.material import MaterialPriceCategory, MaterialGroup


# Mapping price categories → material groups (same as in seed script)
PRICE_CATEGORY_TO_GROUP = {
    "OCEL-KRUHOVA": "OCEL-KONS",
    "OCEL-PLOCHA": "OCEL-KONS",
    "OCEL-DESKY": "OCEL-KONS",
    "OCEL-TRUBKA": "OCEL-KONS",
    "NEREZ-KRUHOVA": "NEREZ",
    "NEREZ-PLOCHA": "NEREZ",
    "HLINIK-DESKY": "HLINIK",
    "HLINIK-KRUHOVA": "HLINIK",
    "HLINIK-PLOCHA": "HLINIK",
    "PLASTY-DESKY": "PLAST",
    "PLASTY-TYCE": "PLAST",
    "OCEL-NASTROJOVA": "OCEL-NAST",
    "MOSAZ-BRONZ": "MOSAZ",
}


async def fix_material_group_links(db: AsyncSession):
    """Fix missing material_group_id in existing price categories."""
    print("🔧 Fixing MaterialPriceCategory → MaterialGroup links...")
    print()

    # Load material groups
    print("📦 Loading Material Groups...")
    groups_result = await db.execute(select(MaterialGroup))
    groups_dict = {g.code: g.id for g in groups_result.scalars().all()}
    print(f"   Found {len(groups_dict)} material groups")
    print()

    # Check current state
    print("🔍 Checking current state...")
    categories_result = await db.execute(select(MaterialPriceCategory))
    categories = categories_result.scalars().all()

    null_count = sum(1 for c in categories if c.material_group_id is None)
    print(f"   Total categories: {len(categories)}")
    print(f"   Categories with NULL material_group_id: {null_count}")
    print()

    if null_count == 0:
        print("✅ All categories already have material_group_id set!")
        return

    # Update categories
    print("🔄 Updating categories...")
    fixed_count = 0
    for cat_code, group_code in PRICE_CATEGORY_TO_GROUP.items():
        group_id = groups_dict.get(group_code)
        if not group_id:
            print(f"⚠️  WARNING: Material group '{group_code}' not found for '{cat_code}'")
            continue

        result = await db.execute(
            update(MaterialPriceCategory)
            .where(MaterialPriceCategory.code == cat_code)
            .where(MaterialPriceCategory.material_group_id.is_(None))  # Only update NULL values
            .values(material_group_id=group_id)
        )

        if result.rowcount > 0:
            print(f"✅ {cat_code:20} → {group_code} (group_id={group_id})")
            fixed_count += result.rowcount

    await db.commit()
    print()
    print(f"✅ Fixed {fixed_count} price categories")
    print()

    # Verify
    print("✅ Verification...")
    categories_result = await db.execute(select(MaterialPriceCategory))
    categories = categories_result.scalars().all()
    remaining_null = sum(1 for c in categories if c.material_group_id is None)

    if remaining_null > 0:
        print(f"⚠️  WARNING: {remaining_null} categories still have NULL material_group_id:")
        for cat in categories:
            if cat.material_group_id is None:
                print(f"   - {cat.code}: {cat.name}")
    else:
        print("   All categories now have material_group_id set!")


async def main():
    """Main migration function."""
    async with async_session() as db:
        try:
            await fix_material_group_links(db)
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
