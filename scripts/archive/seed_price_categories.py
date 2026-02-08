#!/usr/bin/env python3
"""
Seed script: Material Price Categories & Tiers (ADR-014)

Naplní databázi 13 cenovými kategoriemi a price tiers podle PDF ceníku.
Kategorie sdružují polotovary se stejnou cenovou strukturou (např. "OCEL - kruhová tyč").

Spuštění:
    python -m scripts.seed_price_categories
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session
from app.models.material import MaterialPriceCategory, MaterialPriceTier, MaterialGroup
from app.db_helpers import set_audit


# ========== MAPPING: Price Category → Material Group ==========
# Každá price category musí být namapována na správnou material group pro výpočet hustoty
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


# ========== PRICE CATEGORIES & TIERS (podle PDF) ==========

PRICE_CATEGORIES = [
    {
        "code": "OCEL-KRUHOVA",
        "name": "OCEL konstrukční - kruhová tyč/šestihran",
        "tiers": [
            {"min_weight": 0, "max_weight": 15, "price_per_kg": 49.4},
            {"min_weight": 15, "max_weight": 100, "price_per_kg": 34.5},
            {"min_weight": 100, "max_weight": None, "price_per_kg": 26.3},
        ]
    },
    {
        "code": "OCEL-PLOCHA",
        "name": "OCEL konstrukční - plochá tyč",
        "tiers": [
            {"min_weight": 0, "max_weight": 15, "price_per_kg": 57.1},
            {"min_weight": 15, "max_weight": 100, "price_per_kg": 40.9},
            {"min_weight": 100, "max_weight": None, "price_per_kg": 30.7},
        ]
    },
    {
        "code": "OCEL-DESKY",
        "name": "OCEL konstrukční - desky/bloky",
        "tiers": [
            {"min_weight": 0, "max_weight": 15, "price_per_kg": 30.0},
            {"min_weight": 15, "max_weight": None, "price_per_kg": 29.7},
        ]
    },
    {
        "code": "OCEL-TRUBKA",
        "name": "OCEL konstrukční - trubka",
        "tiers": [
            {"min_weight": 0, "max_weight": 15, "price_per_kg": 210.3},
            {"min_weight": 15, "max_weight": None, "price_per_kg": 139.4},
        ]
    },
    {
        "code": "NEREZ-KRUHOVA",
        "name": "NEREZ - kruhová tyč",
        "tiers": [
            {"min_weight": 0, "max_weight": 15, "price_per_kg": 119.3},
            {"min_weight": 15, "max_weight": 100, "price_per_kg": 104.6},
            {"min_weight": 100, "max_weight": None, "price_per_kg": 89.7},
        ]
    },
    {
        "code": "NEREZ-PLOCHA",
        "name": "NEREZ - plochá tyč",
        "tiers": [
            {"min_weight": 0, "max_weight": 15, "price_per_kg": 205.0},
            {"min_weight": 15, "max_weight": None, "price_per_kg": 168.0},
        ]
    },
    {
        "code": "HLINIK-DESKY",
        "name": "HLINÍK - desky a bloky",
        "tiers": [
            {"min_weight": 0, "max_weight": 15, "price_per_kg": 117.9},
            {"min_weight": 15, "max_weight": None, "price_per_kg": 108.0},
        ]
    },
    {
        "code": "HLINIK-KRUHOVA",
        "name": "HLINÍK - kruhová tyč",
        "tiers": [
            {"min_weight": 0, "max_weight": 15, "price_per_kg": 179.4},
            {"min_weight": 15, "max_weight": 100, "price_per_kg": 150.5},
            {"min_weight": 100, "max_weight": None, "price_per_kg": 110.3},
        ]
    },
    {
        "code": "HLINIK-PLOCHA",
        "name": "HLINÍK - plochá tyč",
        "tiers": [
            {"min_weight": 0, "max_weight": 15, "price_per_kg": 151.6},
            {"min_weight": 15, "max_weight": 100, "price_per_kg": 146.8},
            {"min_weight": 100, "max_weight": None, "price_per_kg": 135.0},
        ]
    },
    {
        "code": "PLASTY-DESKY",
        "name": "PLASTY (POM/PA6) - desky",
        "tiers": [
            {"min_weight": 0, "max_weight": None, "price_per_kg": 336.9},
        ]
    },
    {
        "code": "PLASTY-TYCE",
        "name": "PLASTY (POM/PA6) - tyče",
        "tiers": [
            {"min_weight": 0, "max_weight": 15, "price_per_kg": 177.2},
            {"min_weight": 15, "max_weight": None, "price_per_kg": 177.4},
        ]
    },
    {
        "code": "OCEL-NASTROJOVA",
        "name": "OCEL nástrojová - kruhová tyč",
        "tiers": [
            {"min_weight": 0, "max_weight": 15, "price_per_kg": 104.0},
            {"min_weight": 15, "max_weight": 100, "price_per_kg": 95.0},
            {"min_weight": 100, "max_weight": None, "price_per_kg": 90.0},
        ]
    },
    {
        "code": "MOSAZ-BRONZ",
        "name": "MOSAZ/BRONZ - kruhová tyč",
        "tiers": [
            {"min_weight": 0, "max_weight": 15, "price_per_kg": 320.0},
            {"min_weight": 15, "max_weight": 100, "price_per_kg": 290.0},
            {"min_weight": 100, "max_weight": None, "price_per_kg": 270.0},
        ]
    },
]


async def seed_price_categories(db: AsyncSession):
    """Seed price categories and tiers."""
    print("🎯 Seeding Material Price Categories & Tiers...")
    print(f"   Categories: {len(PRICE_CATEGORIES)}")

    total_tiers = sum(len(cat["tiers"]) for cat in PRICE_CATEGORIES)
    print(f"   Tiers: {total_tiers}")
    print()

    # Load material groups for mapping
    print("📦 Loading Material Groups for mapping...")
    groups_result = await db.execute(select(MaterialGroup))
    groups_dict = {g.code: g.id for g in groups_result.scalars().all()}
    print(f"   Found {len(groups_dict)} material groups")
    print()

    username = "seed_script"

    for cat_data in PRICE_CATEGORIES:
        # Map to material_group_id
        group_code = PRICE_CATEGORY_TO_GROUP.get(cat_data["code"])
        material_group_id = groups_dict.get(group_code) if group_code else None

        if not material_group_id:
            print(f"⚠️  WARNING: No material_group mapping for {cat_data['code']}")

        # Create category
        category = MaterialPriceCategory(
            code=cat_data["code"],
            name=cat_data["name"],
            material_group_id=material_group_id  # ✅ ROOT CAUSE FIX!
        )
        set_audit(category, username)
        db.add(category)
        await db.flush()  # Get ID

        group_info = f" → {group_code}" if group_code else " (no group)"
        print(f"✅ {category.code:20} - {category.name}{group_info}")

        # Create tiers
        for tier_data in cat_data["tiers"]:
            tier = MaterialPriceTier(
                price_category_id=category.id,
                min_weight=tier_data["min_weight"],
                max_weight=tier_data["max_weight"],
                price_per_kg=tier_data["price_per_kg"]
            )
            set_audit(tier, username)
            db.add(tier)

            max_weight_str = f"{tier.max_weight}kg" if tier.max_weight else "∞"
            print(f"   └─ [{tier.min_weight}kg - {max_weight_str:7}] → {tier.price_per_kg:6.1f} Kč/kg")

        print()

    await db.commit()
    print(f"✅ Seeded {len(PRICE_CATEGORIES)} categories with {total_tiers} tiers")


async def main():
    """Main seed function."""
    async with async_session() as db:
        try:
            await seed_price_categories(db)
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
