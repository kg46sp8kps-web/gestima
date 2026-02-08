"""Import MaterialPriceTiers from CSV template

Usage:
    python scripts/import_price_tiers_from_csv.py data/material_price_tiers_template.csv

CSV Format:
    code,category_name,tier1_min,tier1_max,tier1_price,tier2_min,tier2_max,tier2_price,tier3_min,tier3_max,tier3_price

Date: 2026-02-03
"""

import asyncio
import csv
import sys
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.material import MaterialPriceCategory, MaterialPriceTier


async def import_price_tiers_from_csv(csv_path: Path, db: AsyncSession):
    """Import MaterialPriceTiers from CSV file"""

    print("=" * 100)
    print(f"📥 Importing MaterialPriceTiers from CSV")
    print("=" * 100)
    print(f"   File: {csv_path}")
    print()

    # Load categories for validation
    result = await db.execute(select(MaterialPriceCategory))
    categories = {cat.code: cat for cat in result.scalars().all()}

    print(f"✅ Found {len(categories)} MaterialPriceCategories")
    print()

    created_count = 0
    skipped_count = 0
    error_count = 0

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            code = row['code']
            category = categories.get(code)

            if not category:
                print(f"❌ Category not found: {code}")
                error_count += 1
                continue

            # Check if tiers already exist
            existing = await db.execute(
                select(MaterialPriceTier)
                .where(MaterialPriceTier.price_category_id == category.id)
            )

            if existing.scalars().first():
                print(f"⏭️  [{code}] Already has tiers: {row['category_name']}")
                skipped_count += 1
                continue

            # Create tiers
            tiers_created = 0

            # Tier 1
            if row.get('tier1_price'):
                tier1 = MaterialPriceTier(
                    price_category_id=category.id,
                    min_weight=float(row['tier1_min']),
                    max_weight=float(row['tier1_max']) if row['tier1_max'] else None,
                    price_per_kg=float(row['tier1_price'])
                )
                db.add(tier1)
                tiers_created += 1

            # Tier 2
            if row.get('tier2_price'):
                tier2 = MaterialPriceTier(
                    price_category_id=category.id,
                    min_weight=float(row['tier2_min']),
                    max_weight=float(row['tier2_max']) if row['tier2_max'] else None,
                    price_per_kg=float(row['tier2_price'])
                )
                db.add(tier2)
                tiers_created += 1

            # Tier 3
            if row.get('tier3_price'):
                tier3 = MaterialPriceTier(
                    price_category_id=category.id,
                    min_weight=float(row['tier3_min']),
                    max_weight=float(row['tier3_max']) if row['tier3_max'] else None,
                    price_per_kg=float(row['tier3_price'])
                )
                db.add(tier3)
                tiers_created += 1

            print(f"✅ [{code}] {row['category_name']:40s} → {tiers_created} tiers")
            created_count += tiers_created

    await db.commit()

    print()
    print("=" * 100)
    print("✅ Import complete!")
    print("=" * 100)
    print(f"   Tiers created:    {created_count}")
    print(f"   Categories skipped: {skipped_count}")
    print(f"   Errors:           {error_count}")
    print()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_price_tiers_from_csv.py <csv_file>")
        print()
        print("Example:")
        print("  python scripts/import_price_tiers_from_csv.py data/material_price_tiers_template.csv")
        sys.exit(1)

    csv_path = Path(sys.argv[1])

    if not csv_path.exists():
        print(f"❌ File not found: {csv_path}")
        sys.exit(1)

    async with async_session() as db:
        await import_price_tiers_from_csv(csv_path, db)


if __name__ == "__main__":
    asyncio.run(main())
