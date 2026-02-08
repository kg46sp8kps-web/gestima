"""Seed MaterialGroups with proper codes (clean version)

Creates MaterialGroups with professional codes (HLINIK, OCEL-KONS, etc.)
that are easy to read and maintain.

Replaces W.Nr prefix codes (1.0, 3.) with proper names.
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
from app.models.material import MaterialGroup


# MaterialGroups with 8-digit codes (ADR-017 compliance)
# 9 groups total (4 steel types + plasty)
# Code range: 20910000-20910008 (sub-range: 20910000-20919999)
MATERIAL_GROUPS_CLEAN = [
    # Neželezné kovy
    {'code': '20910000', 'name': 'Hliník', 'density': 2.7},
    {'code': '20910001', 'name': 'Měď', 'density': 8.9},
    {'code': '20910002', 'name': 'Mosaz', 'density': 8.5},

    # Oceli
    {'code': '20910003', 'name': 'Ocel automatová', 'density': 7.85},
    {'code': '20910004', 'name': 'Ocel konstrukční', 'density': 7.85},
    {'code': '20910005', 'name': 'Ocel legovaná', 'density': 7.85},
    {'code': '20910006', 'name': 'Ocel nástrojová', 'density': 7.85},
    {'code': '20910007', 'name': 'Nerez', 'density': 7.9},

    # Plasty
    {'code': '20910008', 'name': 'Plasty', 'density': 1.2},
]


async def seed_material_groups_clean(db: AsyncSession):
    """Seed MaterialGroups with professional codes"""

    print("=" * 100)
    print("🌱 Seeding MaterialGroups (Clean codes)")
    print("=" * 100)
    print()
    print(f"   • Total groups: {len(MATERIAL_GROUPS_CLEAN)}")
    print(f"   • Code pattern: Professional codes (HLINIK, OCEL-KONS, etc.)")
    print(f"   • Steel types: 4 only (auto, konstrukční, legovaná, nástrojová)")
    print()

    created_count = 0
    skipped_count = 0

    for group_data in MATERIAL_GROUPS_CLEAN:
        # Check if exists
        existing = await db.execute(
            select(MaterialGroup)
            .where(MaterialGroup.code == group_data['code'])
        )

        if existing.scalar_one_or_none():
            print(f"⏭️  Skipping existing: {group_data['code']:12s} - {group_data['name']}")
            skipped_count += 1
            continue

        # Create new
        new_group = MaterialGroup(
            code=group_data['code'],
            name=group_data['name'],
            density=group_data['density']
        )

        db.add(new_group)
        print(f"✅ [{group_data['code']:12s}] {group_data['name']:25s} ({group_data['density']} kg/dm³)")
        created_count += 1

    await db.commit()

    print()
    print("=" * 100)
    print("✅ Seeding complete!")
    print("=" * 100)
    print(f"   Created: {created_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Total:   {len(MATERIAL_GROUPS_CLEAN)}")
    print()
    print("📊 Next step: Run seed_price_categories_v2.py to create 38 categories")
    print()


async def main():
    async with async_session() as db:
        await seed_material_groups_clean(db)


if __name__ == "__main__":
    asyncio.run(main())
