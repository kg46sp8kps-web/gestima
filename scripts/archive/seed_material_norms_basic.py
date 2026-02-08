"""Seed MaterialNorms from Infor export CSV

Loads material norms from scripts/material_norms_export.csv
which was extracted from Infor SLItems (3189 materials → 82 unique norms).

Usage:
    python scripts/seed_material_norms_basic.py

Date: 2026-02-03
Source: Infor CloudSuite Industrial (FamilyCode = 'Materiál')
"""

import asyncio
import csv
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.material_norm import MaterialNorm


# MaterialGroup ID mapping
GROUP_NAMES = {
    1: "Hliník",
    2: "Měď",
    3: "Mosaz",
    4: "Ocel automatová",
    5: "Ocel konstrukční",
    6: "Ocel legovaná",
    7: "Ocel nástrojová",
    8: "Nerez",
    9: "Plasty",
}


def load_norms_from_csv():
    """Load norms from CSV file."""
    csv_path = os.path.join(os.path.dirname(__file__), "material_norms_export.csv")

    norms = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["material_group_id"]:  # Skip unmapped
                norms.append({
                    "w_nr": row["w_nr"] or None,
                    "csn": row["csn"] or None,
                    "en_iso": row["en_iso"] or None,
                    "aisi": row["aisi"] or None,
                    "material_group_id": int(row["material_group_id"]),
                    "note": row["mapping_reason"],
                })

    return norms


async def seed_material_norms_basic(db: AsyncSession):
    """Seed MaterialNorms from Infor export CSV."""

    norms = load_norms_from_csv()

    print("=" * 100)
    print("🌱 Seeding MaterialNorms from Infor export")
    print("=" * 100)
    print()
    print(f"   • CSV norms: {len(norms)}")
    print(f"   • Source: Infor SLItems (FamilyCode = 'Materiál')")
    print()

    created_count = 0
    skipped_count = 0
    updated_count = 0

    for norm_data in norms:
        w_nr = norm_data["w_nr"]
        group_id = norm_data["material_group_id"]
        group_name = GROUP_NAMES.get(group_id, "Unknown")

        # Check if exists by W.Nr
        result = await db.execute(
            select(MaterialNorm).where(MaterialNorm.w_nr == w_nr)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update if data changed
            if (existing.csn != norm_data["csn"] or
                existing.en_iso != norm_data["en_iso"] or
                existing.aisi != norm_data["aisi"] or
                existing.material_group_id != group_id):

                existing.csn = norm_data["csn"]
                existing.en_iso = norm_data["en_iso"]
                existing.aisi = norm_data["aisi"]
                existing.material_group_id = group_id
                existing.note = f"Infor: {norm_data['note']}"

                print(f"🔄 [{w_nr:12s}] Updated → {group_name}")
                updated_count += 1
            else:
                skipped_count += 1
            continue

        # Create new
        new_norm = MaterialNorm(
            w_nr=norm_data["w_nr"],
            csn=norm_data["csn"],
            en_iso=norm_data["en_iso"],
            aisi=norm_data["aisi"],
            material_group_id=group_id,
            note=f"Infor: {norm_data['note']}"
        )
        db.add(new_norm)

        print(f"✅ [{w_nr:12s}] {norm_data['en_iso'] or '-':20s} → {group_name}")
        created_count += 1

    await db.commit()

    print()
    print("=" * 100)
    print("✅ Seeding complete!")
    print("=" * 100)
    print(f"   Created: {created_count}")
    print(f"   Updated: {updated_count}")
    print(f"   Skipped: {skipped_count} (unchanged)")
    print(f"   Total:   {len(norms)}")
    print()

    # Summary by group
    from collections import Counter
    by_group = Counter(n["material_group_id"] for n in norms)
    print("📊 Norms by MaterialGroup:")
    for gid in sorted(by_group.keys()):
        print(f"   {GROUP_NAMES.get(gid, 'Unknown'):20s}: {by_group[gid]}")
    print()


async def main():
    async with async_session() as db:
        await seed_material_norms_basic(db)


if __name__ == "__main__":
    asyncio.run(main())
