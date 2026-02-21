#!/usr/bin/env python3
"""GESTIMA - Seed MaterialGroups with cutting parameters

10 material groups with complete cutting data for machining time estimation.
Data sources: Sandvik Coromant 2024, Iscar 2024, Kennametal 2024
Codes: 8-digit (ADR-017), range 20910000-20910009
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.material import MaterialGroup


MATERIAL_GROUPS = [
    # === Neželezné kovy ===
    {
        'code': '20910000', 'name': 'Hliník', 'density': 2.7,
        'iso_group': 'N', 'hardness_hb': 80.0,
        'mrr_turning_roughing': 1200.0, 'mrr_turning_finishing': 300.0,
        'mrr_milling_roughing': 800.0, 'mrr_milling_finishing': 200.0,
        'cutting_speed_turning': 350.0, 'cutting_speed_milling': 300.0,
        'feed_turning': 0.35, 'feed_milling': 0.25,
        'deep_pocket_penalty': 1.5, 'thin_wall_penalty': 2.0,
        'cutting_data_source': 'Iscar 2024 / Sandvik Coromant 2024',
    },
    {
        'code': '20910001', 'name': 'Měď', 'density': 8.9,
        'iso_group': 'N', 'hardness_hb': 90.0,
        'mrr_turning_roughing': 800.0, 'mrr_turning_finishing': 200.0,
        'mrr_milling_roughing': 500.0, 'mrr_milling_finishing': 125.0,
        'cutting_speed_turning': 200.0, 'cutting_speed_milling': 180.0,
        'feed_turning': 0.30, 'feed_milling': 0.20,
        'deep_pocket_penalty': 1.6, 'thin_wall_penalty': 2.2,
        'cutting_data_source': 'Kennametal 2024',
    },
    {
        'code': '20910002', 'name': 'Mosaz', 'density': 8.5,
        'iso_group': 'N', 'hardness_hb': 100.0,
        'mrr_turning_roughing': 1000.0, 'mrr_turning_finishing': 250.0,
        'mrr_milling_roughing': 650.0, 'mrr_milling_finishing': 160.0,
        'cutting_speed_turning': 250.0, 'cutting_speed_milling': 220.0,
        'feed_turning': 0.32, 'feed_milling': 0.22,
        'deep_pocket_penalty': 1.5, 'thin_wall_penalty': 2.0,
        'cutting_data_source': 'Sandvik Coromant 2024',
    },

    # === Oceli ===
    {
        'code': '20910003', 'name': 'Ocel automatová', 'density': 7.85,
        'iso_group': 'P', 'hardness_hb': 180.0,
        'mrr_turning_roughing': 450.0, 'mrr_turning_finishing': 110.0,
        'mrr_milling_roughing': 300.0, 'mrr_milling_finishing': 75.0,
        'cutting_speed_turning': 220.0, 'cutting_speed_milling': 200.0,
        'feed_turning': 0.28, 'feed_milling': 0.18,
        'deep_pocket_penalty': 1.8, 'thin_wall_penalty': 2.5,
        'cutting_data_source': 'Iscar 2024 (11SM, 11SMn30)',
    },
    {
        'code': '20910004', 'name': 'Ocel konstrukční', 'density': 7.85,
        'iso_group': 'P', 'hardness_hb': 200.0,
        'mrr_turning_roughing': 400.0, 'mrr_turning_finishing': 100.0,
        'mrr_milling_roughing': 250.0, 'mrr_milling_finishing': 65.0,
        'cutting_speed_turning': 180.0, 'cutting_speed_milling': 160.0,
        'feed_turning': 0.25, 'feed_milling': 0.16,
        'deep_pocket_penalty': 1.8, 'thin_wall_penalty': 2.5,
        'cutting_data_source': 'Sandvik Coromant 2024 (C45, 16MnCr5)',
    },
    {
        'code': '20910005', 'name': 'Ocel legovaná', 'density': 7.85,
        'iso_group': 'P', 'hardness_hb': 250.0,
        'mrr_turning_roughing': 300.0, 'mrr_turning_finishing': 75.0,
        'mrr_milling_roughing': 180.0, 'mrr_milling_finishing': 45.0,
        'cutting_speed_turning': 150.0, 'cutting_speed_milling': 140.0,
        'feed_turning': 0.22, 'feed_milling': 0.14,
        'deep_pocket_penalty': 2.0, 'thin_wall_penalty': 2.8,
        'cutting_data_source': 'Iscar 2024 (42CrMo4, 34CrNiMo6)',
    },
    {
        'code': '20910006', 'name': 'Ocel nástrojová', 'density': 7.85,
        'iso_group': 'K', 'hardness_hb': 300.0,
        'mrr_turning_roughing': 200.0, 'mrr_turning_finishing': 50.0,
        'mrr_milling_roughing': 120.0, 'mrr_milling_finishing': 30.0,
        'cutting_speed_turning': 110.0, 'cutting_speed_milling': 100.0,
        'feed_turning': 0.18, 'feed_milling': 0.12,
        'deep_pocket_penalty': 2.2, 'thin_wall_penalty': 3.0,
        'cutting_data_source': 'Kennametal 2024 (X153CrMoV12, 90MnCrV8)',
    },
    {
        'code': '20910007', 'name': 'Nerez', 'density': 7.9,
        'iso_group': 'M', 'hardness_hb': 220.0,
        'mrr_turning_roughing': 250.0, 'mrr_turning_finishing': 65.0,
        'mrr_milling_roughing': 150.0, 'mrr_milling_finishing': 40.0,
        'cutting_speed_turning': 130.0, 'cutting_speed_milling': 120.0,
        'feed_turning': 0.20, 'feed_milling': 0.14,
        'deep_pocket_penalty': 2.0, 'thin_wall_penalty': 2.8,
        'cutting_data_source': 'Sandvik Coromant 2024 (1.4301, 1.4401)',
    },

    # === Litina ===
    {
        'code': '20910009', 'name': 'Litina', 'density': 7.2,
        'iso_group': 'K', 'hardness_hb': 200.0,
        'mrr_turning_roughing': 350.0, 'mrr_turning_finishing': 90.0,
        'mrr_milling_roughing': 220.0, 'mrr_milling_finishing': 55.0,
        'cutting_speed_turning': 160.0, 'cutting_speed_milling': 140.0,
        'feed_turning': 0.25, 'feed_milling': 0.18,
        'deep_pocket_penalty': 1.8, 'thin_wall_penalty': 2.5,
        'cutting_data_source': 'Sandvik Coromant 2024 (GJL-250, GJS-400)',
    },

    # === Plasty ===
    {
        'code': '20910008', 'name': 'Plasty', 'density': 1.2,
        'iso_group': 'N', 'hardness_hb': 30.0,
        'mrr_turning_roughing': 2000.0, 'mrr_turning_finishing': 500.0,
        'mrr_milling_roughing': 1500.0, 'mrr_milling_finishing': 400.0,
        'cutting_speed_turning': 500.0, 'cutting_speed_milling': 450.0,
        'feed_turning': 0.40, 'feed_milling': 0.30,
        'deep_pocket_penalty': 1.3, 'thin_wall_penalty': 1.8,
        'cutting_data_source': 'Kennametal 2024 (POM, PA6, PEEK)',
    },
]


async def seed_material_groups(db: AsyncSession):
    """Seed MaterialGroups with cutting parameters. Idempotent: update existing, create new."""

    print("🌱 Seeding MaterialGroups (10 groups with cutting data)...")

    created_count = 0
    updated_count = 0

    for group_data in MATERIAL_GROUPS:
        result = await db.execute(
            select(MaterialGroup).where(MaterialGroup.code == group_data['code'])
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update all fields on existing record
            for key, value in group_data.items():
                if key != 'code':
                    setattr(existing, key, value)
            updated_count += 1
        else:
            new_group = MaterialGroup(**group_data)
            db.add(new_group)
            created_count += 1

    await db.commit()

    print(f"✅ MaterialGroups seeded: {created_count} created, {updated_count} updated")


async def main():
    async with async_session() as db:
        await seed_material_groups(db)


if __name__ == "__main__":
    asyncio.run(main())
