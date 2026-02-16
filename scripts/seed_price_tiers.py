"""Seed MaterialPriceTiers — cenové stupně pro všech 43 kategorií

Inline data z material_price_tiers_template.csv (2026-02-03).
3 stupně na kategorii: 0-15 kg, 15-100 kg, 100+ kg.
Ceny v Kč/kg — orientační, editovatelné přes admin panel.

Pravidla (L-071):
- Data INLINE (žádné CSV závislosti)
- Idempotentní (DELETE ALL + INSERT)
- Spouští se z gestima.py seed-demo

Date: 2026-02-13
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.material import MaterialPriceCategory, MaterialPriceTier


# Inline data: (category_code, [(min_kg, max_kg_or_None, price_per_kg), ...])
# Source: data/material_price_tiers_template.csv (2026-02-03)
PRICE_TIERS_DATA = [
    # Hliník
    ("20900000", [(0, 15, 50.0), (15, 100, 40.0), (100, None, 30.0)]),   # Hliník - deska
    ("20900001", [(0, 15, 50.0), (15, 100, 40.0), (100, None, 30.0)]),   # Hliník - tyč kruhová
    ("20900002", [(0, 15, 50.0), (15, 100, 40.0), (100, None, 30.0)]),   # Hliník - tyč plochá
    ("20900003", [(0, 15, 50.0), (15, 100, 40.0), (100, None, 30.0)]),   # Hliník - tyč čtvercová
    ("20900004", [(0, 15, 60.0), (15, 100, 50.0), (100, None, 40.0)]),   # Hliník - trubka
    ("20900005", [(0, 15, 55.0), (15, 100, 45.0), (100, None, 35.0)]),   # Hliník - tyč šestihranná

    # Mosaz
    ("20900006", [(0, 15, 120.0), (15, 100, 100.0), (100, None, 80.0)]),  # Mosaz - tyč kruhová
    ("20900007", [(0, 15, 120.0), (15, 100, 100.0), (100, None, 80.0)]),  # Mosaz - tyč plochá
    ("20900008", [(0, 15, 120.0), (15, 100, 100.0), (100, None, 80.0)]),  # Mosaz - tyč čtvercová
    ("20900009", [(0, 15, 130.0), (15, 100, 110.0), (100, None, 90.0)]),  # Mosaz - trubka

    # Měď
    ("20900010", [(0, 15, 150.0), (15, 100, 130.0), (100, None, 110.0)]),  # Měď - deska
    ("20900011", [(0, 15, 150.0), (15, 100, 130.0), (100, None, 110.0)]),  # Měď - tyč kruhová
    ("20900012", [(0, 15, 150.0), (15, 100, 130.0), (100, None, 110.0)]),  # Měď - tyč plochá
    ("20900013", [(0, 15, 150.0), (15, 100, 130.0), (100, None, 110.0)]),  # Měď - tyč čtvercová
    ("20900014", [(0, 15, 160.0), (15, 100, 140.0), (100, None, 120.0)]),  # Měď - trubka
    ("20900015", [(0, 15, 155.0), (15, 100, 135.0), (100, None, 115.0)]),  # Měď - tyč šestihranná

    # Nerez
    ("20900016", [(0, 15, 80.0), (15, 100, 65.0), (100, None, 50.0)]),   # Nerez - deska
    ("20900017", [(0, 15, 80.0), (15, 100, 65.0), (100, None, 50.0)]),   # Nerez - tyč kruhová
    ("20900018", [(0, 15, 80.0), (15, 100, 65.0), (100, None, 50.0)]),   # Nerez - tyč plochá
    ("20900019", [(0, 15, 80.0), (15, 100, 65.0), (100, None, 50.0)]),   # Nerez - tyč čtvercová
    ("20900020", [(0, 15, 90.0), (15, 100, 75.0), (100, None, 60.0)]),   # Nerez - trubka
    ("20900021", [(0, 15, 85.0), (15, 100, 70.0), (100, None, 55.0)]),   # Nerez - tyč šestihranná

    # Ocel automatová
    ("20900022", [(0, 15, 35.0), (15, 100, 30.0), (100, None, 25.0)]),   # Ocel automatová - tyč kruhová
    ("20900023", [(0, 15, 35.0), (15, 100, 30.0), (100, None, 25.0)]),   # Ocel automatová - tyč plochá
    ("20900024", [(0, 15, 35.0), (15, 100, 30.0), (100, None, 25.0)]),   # Ocel automatová - tyč čtvercová

    # Ocel konstrukční
    ("20900025", [(0, 15, 30.0), (15, 100, 25.0), (100, None, 20.0)]),   # Ocel konstrukční - deska
    ("20900026", [(0, 15, 30.0), (15, 100, 25.0), (100, None, 20.0)]),   # Ocel konstrukční - tyč kruhová
    ("20900027", [(0, 15, 30.0), (15, 100, 25.0), (100, None, 20.0)]),   # Ocel konstrukční - tyč plochá
    ("20900028", [(0, 15, 30.0), (15, 100, 25.0), (100, None, 20.0)]),   # Ocel konstrukční - tyč čtvercová
    ("20900029", [(0, 15, 35.0), (15, 100, 30.0), (100, None, 25.0)]),   # Ocel konstrukční - trubka
    ("20900030", [(0, 15, 32.0), (15, 100, 27.0), (100, None, 22.0)]),   # Ocel konstrukční - tyč šestihranná

    # Ocel legovaná
    ("20900031", [(0, 15, 45.0), (15, 100, 38.0), (100, None, 32.0)]),   # Ocel legovaná - tyč kruhová
    ("20900032", [(0, 15, 45.0), (15, 100, 38.0), (100, None, 32.0)]),   # Ocel legovaná - tyč plochá
    ("20900033", [(0, 15, 45.0), (15, 100, 38.0), (100, None, 32.0)]),   # Ocel legovaná - tyč čtvercová

    # Ocel nástrojová
    ("20900034", [(0, 15, 55.0), (15, 100, 45.0), (100, None, 38.0)]),   # Ocel nástrojová - deska
    ("20900035", [(0, 15, 55.0), (15, 100, 45.0), (100, None, 38.0)]),   # Ocel nástrojová - tyč kruhová
    ("20900036", [(0, 15, 55.0), (15, 100, 45.0), (100, None, 38.0)]),   # Ocel nástrojová - tyč plochá
    ("20900037", [(0, 15, 55.0), (15, 100, 45.0), (100, None, 38.0)]),   # Ocel nástrojová - tyč čtvercová

    # Plasty
    ("20900038", [(0, 15, 40.0), (15, 100, 35.0), (100, None, 30.0)]),   # Plasty - deska
    ("20900039", [(0, 15, 40.0), (15, 100, 35.0), (100, None, 30.0)]),   # Plasty - tyč kruhová
    ("20900040", [(0, 15, 40.0), (15, 100, 35.0), (100, None, 30.0)]),   # Plasty - tyč plochá
    ("20900041", [(0, 15, 40.0), (15, 100, 35.0), (100, None, 30.0)]),   # Plasty - tyč čtvercová
    ("20900042", [(0, 15, 42.0), (15, 100, 37.0), (100, None, 32.0)]),   # Plasty - tyč šestihranná
]


async def seed_price_tiers(db: AsyncSession):
    """Seed MaterialPriceTiers — idempotent (upsert by category+min_weight)"""

    print("🌱 Seeding MaterialPriceTiers (43 categories × 3 tiers)...")

    # Load categories by code
    result = await db.execute(select(MaterialPriceCategory))
    categories_by_code = {cat.code: cat for cat in result.scalars().all()}

    if not categories_by_code:
        print("❌ No MaterialPriceCategories found! Run seed_price_categories first.")
        return

    # Load existing tiers indexed by (category_id, min_weight) for upsert
    result = await db.execute(select(MaterialPriceTier))
    existing_tiers = {}
    for tier in result.scalars().all():
        key = (tier.price_category_id, tier.min_weight)
        existing_tiers[key] = tier

    created_count = 0
    updated_count = 0
    unchanged_count = 0
    error_count = 0

    for category_code, tier_list in PRICE_TIERS_DATA:
        category = categories_by_code.get(category_code)
        if not category:
            print(f"  ⚠️  Category {category_code} not found, skipping")
            error_count += 1
            continue

        for min_weight, max_weight, price_per_kg in tier_list:
            key = (category.id, min_weight)
            existing = existing_tiers.get(key)

            if existing:
                # Update if changed
                changed = False
                if existing.max_weight != max_weight:
                    existing.max_weight = max_weight
                    changed = True
                if existing.price_per_kg != price_per_kg:
                    existing.price_per_kg = price_per_kg
                    changed = True
                if changed:
                    updated_count += 1
                else:
                    unchanged_count += 1
            else:
                tier = MaterialPriceTier(
                    price_category_id=category.id,
                    min_weight=min_weight,
                    max_weight=max_weight,
                    price_per_kg=price_per_kg,
                )
                db.add(tier)
                created_count += 1

    await db.commit()

    print(f"  ✅ PriceTiers: {created_count} created, {updated_count} updated, {unchanged_count} unchanged")
    if error_count:
        print(f"  ⚠️  {error_count} categories not found")


async def main():
    async with async_session() as db:
        await seed_price_tiers(db)


if __name__ == "__main__":
    asyncio.run(main())
