"""Seed MaterialGroups from Infor W.Nr analysis

Creates MaterialGroups with W.Nr prefix codes (1.0xxx, 1.4xxx, 3.xxxx)
that map directly to Infor material codes for clean import.

Based on test_preview_price_categories_v2.py analysis.
Date: 2026-02-03
"""

import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.material import MaterialGroup


# MaterialGroups derived from Infor W.Nr analysis
# Using prefix codes (1.0, 1.4, 3.x) for easy mapping
MATERIAL_GROUPS_INFOR = [
    # Oceli (W.Nr 1.0xxx - 1.8xxx)
    {'code': '1.0', 'name': 'Ocel konstrukční', 'density': 7.85},
    {'code': '1.1', 'name': 'Ocel automatová', 'density': 7.85},
    {'code': '1.2', 'name': 'Ocel nástrojová', 'density': 7.85},
    {'code': '1.3', 'name': 'Ocel odolná', 'density': 7.85},
    {'code': '1.4', 'name': 'Nerez', 'density': 7.9},
    {'code': '1.5', 'name': 'Ocel speciální', 'density': 7.85},
    {'code': '1.6', 'name': 'Ocel legovaná', 'density': 7.85},
    {'code': '1.7', 'name': 'Ocel pro kalení', 'density': 7.85},
    {'code': '1.8', 'name': 'Ocel uhlíková', 'density': 7.85},

    # Neželezné kovy (W.Nr 2.x)
    {'code': '2.0', 'name': 'Měď', 'density': 8.9},
    {'code': '2.1', 'name': 'Mosaz', 'density': 8.5},

    # Hliník (W.Nr 3.xxxx) - GENERIC pro všechny série 3.0-3.4
    {'code': '3.', 'name': 'Hliník', 'density': 2.7},
]


async def seed_material_groups_infor(db: AsyncSession):
    """Seed MaterialGroups with W.Nr prefix codes"""

    print("=" * 100)
    print("🌱 Seeding MaterialGroups (Infor W.Nr structure)")
    print("=" * 100)
    print()
    print(f"   • Total groups: {len(MATERIAL_GROUPS_INFOR)}")
    print(f"   • Code pattern: W.Nr prefixes (1.0, 1.4, 3., etc.)")
    print(f"   • Purpose: Direct mapping for Infor material import")
    print()

    created_count = 0
    skipped_count = 0

    for group_data in MATERIAL_GROUPS_INFOR:
        # Check if exists
        existing = await db.execute(
            select(MaterialGroup)
            .where(MaterialGroup.code == group_data['code'])
        )

        if existing.scalar_one_or_none():
            print(f"⏭️  Skipping existing: {group_data['code']} - {group_data['name']}")
            skipped_count += 1
            continue

        # Create new
        new_group = MaterialGroup(
            code=group_data['code'],
            name=group_data['name'],
            density=group_data['density']
        )

        db.add(new_group)
        print(f"✅ [{group_data['code']:4s}] {group_data['name']:25s} ({group_data['density']} kg/dm³)")
        created_count += 1

    await db.commit()

    print()
    print("=" * 100)
    print("✅ Seeding complete!")
    print("=" * 100)
    print(f"   Created: {created_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Total:   {len(MATERIAL_GROUPS_INFOR)}")
    print()
    print("📊 Next step: Run seed_price_categories_v2.py to create 53 categories")
    print()


async def main():
    async with async_session() as db:
        await seed_material_groups_infor(db)


if __name__ == "__main__":
    asyncio.run(main())
