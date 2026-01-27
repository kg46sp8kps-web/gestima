#!/usr/bin/env python3
"""
GESTIMA - Seed script pro Material Catalog (Groups + Price Categories + Tiers)

Vytvoří:
- 18 MaterialGroups (oceli, nerez, hliník, plasty, litina, měď, mosaz, bronz)
- ~40 MaterialPriceCategories (kombinace materiál + tvar)
- Price tiers pro každou kategorii (0-15kg, 15-100kg, 100+kg)

Ceny jsou převzaty z existující tabulky (kde jsou dostupné) nebo
odhadnuty podle materiálové rodiny.

Usage:
    python scripts/seed_material_catalog.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import async_session
from app.models.material import MaterialGroup, MaterialPriceCategory, MaterialPriceTier
from datetime import datetime


# ============================================================================
# MATERIAL GROUPS (18 kategorií)
# ============================================================================

MATERIAL_GROUPS = [
    # Oceli konstrukční
    {"code": "OCEL-KONS", "name": "Ocel konstrukční", "density": 7.85},

    # Oceli automatové
    {"code": "OCEL-AUTO", "name": "Ocel automatová", "density": 7.85},

    # Oceli nástrojové
    {"code": "OCEL-NAST", "name": "Ocel nástrojová", "density": 7.85},

    # Oceli legované
    {"code": "OCEL-LEG", "name": "Ocel legovaná", "density": 7.85},

    # Nerezy
    {"code": "NEREZ", "name": "Nerez", "density": 7.90},

    # Měď
    {"code": "MED", "name": "Měď", "density": 8.90},

    # Mosaz
    {"code": "MOSAZ", "name": "Mosaz", "density": 8.50},

    # Bronz
    {"code": "BRONZ", "name": "Bronz", "density": 8.80},

    # Hliník
    {"code": "HLINIK", "name": "Hliník", "density": 2.70},

    # Litina šedá
    {"code": "LITINA-GG", "name": "Litina šedá", "density": 7.20},

    # Litina tvárná
    {"code": "LITINA-TV", "name": "Litina tvárná", "density": 7.10},

    # Plasty (průměrná hustota, reálně 0.95-1.42)
    {"code": "PLAST", "name": "Plasty", "density": 1.20},
]


# ============================================================================
# MATERIAL PRICE CATEGORIES (~40 kombinací)
# ============================================================================
# Format: {code, name, material_group_code}

PRICE_CATEGORIES = [
    # ===== OCEL KONSTRUKČNÍ =====
    {"code": "OCEL-KONS-KRUHOVA", "name": "OCEL konstrukční - kruhová tyč", "group": "OCEL-KONS"},
    {"code": "OCEL-KONS-PLOCHA", "name": "OCEL konstrukční - plochá tyč", "group": "OCEL-KONS"},
    {"code": "OCEL-KONS-CTVEREC", "name": "OCEL konstrukční - čtvercová tyč", "group": "OCEL-KONS"},
    {"code": "OCEL-KONS-SESTIHRAN", "name": "OCEL konstrukční - šestihran", "group": "OCEL-KONS"},
    {"code": "OCEL-KONS-DESKA", "name": "OCEL konstrukční - deska/blok", "group": "OCEL-KONS"},
    {"code": "OCEL-KONS-TRUBKA", "name": "OCEL konstrukční - trubka", "group": "OCEL-KONS"},

    # ===== OCEL AUTOMATOVÁ =====
    {"code": "OCEL-AUTO-KRUHOVA", "name": "OCEL automatová - kruhová tyč", "group": "OCEL-AUTO"},
    {"code": "OCEL-AUTO-PLOCHA", "name": "OCEL automatová - plochá tyč", "group": "OCEL-AUTO"},
    {"code": "OCEL-AUTO-SESTIHRAN", "name": "OCEL automatová - šestihran", "group": "OCEL-AUTO"},

    # ===== OCEL NÁSTROJOVÁ =====
    {"code": "OCEL-NAST-KRUHOVA", "name": "OCEL nástrojová - kruhová tyč", "group": "OCEL-NAST"},
    {"code": "OCEL-NAST-PLOCHA", "name": "OCEL nástrojová - plochá tyč", "group": "OCEL-NAST"},
    {"code": "OCEL-NAST-DESKA", "name": "OCEL nástrojová - deska/blok", "group": "OCEL-NAST"},

    # ===== OCEL LEGOVANÁ =====
    {"code": "OCEL-LEG-KRUHOVA", "name": "OCEL legovaná - kruhová tyč", "group": "OCEL-LEG"},
    {"code": "OCEL-LEG-PLOCHA", "name": "OCEL legovaná - plochá tyč", "group": "OCEL-LEG"},

    # ===== NEREZ =====
    {"code": "NEREZ-KRUHOVA", "name": "NEREZ - kruhová tyč", "group": "NEREZ"},
    {"code": "NEREZ-PLOCHA", "name": "NEREZ - plochá tyč", "group": "NEREZ"},
    {"code": "NEREZ-CTVEREC", "name": "NEREZ - čtvercová tyč", "group": "NEREZ"},
    {"code": "NEREZ-SESTIHRAN", "name": "NEREZ - šestihran", "group": "NEREZ"},
    {"code": "NEREZ-DESKA", "name": "NEREZ - deska/blok", "group": "NEREZ"},
    {"code": "NEREZ-TRUBKA", "name": "NEREZ - trubka", "group": "NEREZ"},

    # ===== MĚĎ =====
    {"code": "MED-KRUHOVA", "name": "MĚĎ - kruhová tyč", "group": "MED"},
    {"code": "MED-PLOCHA", "name": "MĚĎ - plochá tyč", "group": "MED"},

    # ===== MOSAZ =====
    {"code": "MOSAZ-KRUHOVA", "name": "MOSAZ - kruhová tyč", "group": "MOSAZ"},
    {"code": "MOSAZ-PLOCHA", "name": "MOSAZ - plochá tyč", "group": "MOSAZ"},
    {"code": "MOSAZ-SESTIHRAN", "name": "MOSAZ - šestihran", "group": "MOSAZ"},

    # ===== BRONZ =====
    {"code": "BRONZ-KRUHOVA", "name": "BRONZ - kruhová tyč", "group": "BRONZ"},
    {"code": "BRONZ-PLOCHA", "name": "BRONZ - plochá tyč", "group": "BRONZ"},

    # ===== HLINÍK =====
    {"code": "HLINIK-KRUHOVA", "name": "HLINÍK - kruhová tyč", "group": "HLINIK"},
    {"code": "HLINIK-PLOCHA", "name": "HLINÍK - plochá tyč", "group": "HLINIK"},
    {"code": "HLINIK-CTVEREC", "name": "HLINÍK - čtvercová tyč", "group": "HLINIK"},
    {"code": "HLINIK-SESTIHRAN", "name": "HLINÍK - šestihran", "group": "HLINIK"},
    {"code": "HLINIK-DESKA", "name": "HLINÍK - deska/blok", "group": "HLINIK"},

    # ===== LITINA =====
    {"code": "LITINA-KRUHOVA", "name": "LITINA - kruhová tyč", "group": "LITINA-GG"},

    # ===== PLASTY =====
    {"code": "PLAST-KRUHOVA", "name": "PLASTY - kruhová tyč", "group": "PLAST"},
    {"code": "PLAST-PLOCHA", "name": "PLASTY - plochá tyč/pás", "group": "PLAST"},
    {"code": "PLAST-DESKA", "name": "PLASTY - deska", "group": "PLAST"},
    {"code": "PLAST-BLOK", "name": "PLASTY - blok 3D", "group": "PLAST"},
]


# ============================================================================
# PRICE TIERS (podle současné tabulky + odhady)
# ============================================================================
# Format: {category_code: [(min_weight, max_weight, price_per_kg), ...]}
# Ceny převzaty z existující tabulky (2026-01-27)

PRICE_TIERS = {
    # ===== OCEL KONSTRUKČNÍ (z existující tabulky) =====
    "OCEL-KONS-KRUHOVA": [
        (0.0, 15.0, 49.4),
        (15.0, 100.0, 34.5),
        (100.0, None, 26.3),
    ],
    "OCEL-KONS-PLOCHA": [
        (0.0, 15.0, 57.1),
        (15.0, 100.0, 40.9),
        (100.0, None, 30.7),
    ],
    "OCEL-KONS-DESKA": [
        (0.0, 15.0, 30.0),
        (15.0, None, 29.7),
    ],
    "OCEL-KONS-TRUBKA": [
        (0.0, 15.0, 210.3),
        (15.0, None, 139.4),
    ],
    "OCEL-KONS-SESTIHRAN": [  # Podobná cena jako kruhová
        (0.0, 15.0, 49.4),
        (15.0, 100.0, 34.5),
        (100.0, None, 26.3),
    ],
    "OCEL-KONS-CTVEREC": [  # Mezi kruhová a plochá
        (0.0, 15.0, 53.0),
        (15.0, 100.0, 37.5),
        (100.0, None, 28.0),
    ],

    # ===== OCEL AUTOMATOVÁ (odhad +10% oproti konstrukční) =====
    "OCEL-AUTO-KRUHOVA": [
        (0.0, 15.0, 54.3),
        (15.0, 100.0, 38.0),
        (100.0, None, 29.0),
    ],
    "OCEL-AUTO-PLOCHA": [
        (0.0, 15.0, 62.8),
        (15.0, 100.0, 45.0),
        (100.0, None, 33.8),
    ],
    "OCEL-AUTO-SESTIHRAN": [
        (0.0, 15.0, 54.3),
        (15.0, 100.0, 38.0),
        (100.0, None, 29.0),
    ],

    # ===== OCEL NÁSTROJOVÁ (z existující tabulky) =====
    "OCEL-NAST-KRUHOVA": [
        (0.0, 15.0, 104.0),
        (15.0, 100.0, 95.0),
        (100.0, None, 90.0),
    ],
    "OCEL-NAST-PLOCHA": [
        (0.0, 15.0, 110.0),
        (15.0, 100.0, 100.0),
        (100.0, None, 95.0),
    ],
    "OCEL-NAST-DESKA": [
        (0.0, 15.0, 95.0),
        (15.0, None, 90.0),
    ],

    # ===== OCEL LEGOVANÁ (odhad mezi konstrukční a nástrojová) =====
    "OCEL-LEG-KRUHOVA": [
        (0.0, 15.0, 75.0),
        (15.0, 100.0, 65.0),
        (100.0, None, 55.0),
    ],
    "OCEL-LEG-PLOCHA": [
        (0.0, 15.0, 80.0),
        (15.0, 100.0, 70.0),
        (100.0, None, 60.0),
    ],

    # ===== NEREZ (z existující tabulky) =====
    "NEREZ-KRUHOVA": [
        (0.0, 15.0, 119.3),
        (15.0, 100.0, 104.6),
        (100.0, None, 89.7),
    ],
    "NEREZ-PLOCHA": [
        (0.0, 15.0, 205.0),
        (15.0, None, 168.0),
    ],
    "NEREZ-DESKA": [
        (0.0, 15.0, 180.0),
        (15.0, None, 150.0),
    ],
    "NEREZ-TRUBKA": [
        (0.0, 15.0, 250.0),
        (15.0, None, 200.0),
    ],
    "NEREZ-SESTIHRAN": [
        (0.0, 15.0, 125.0),
        (15.0, 100.0, 110.0),
        (100.0, None, 95.0),
    ],
    "NEREZ-CTVEREC": [
        (0.0, 15.0, 160.0),
        (15.0, 100.0, 140.0),
        (100.0, None, 120.0),
    ],

    # ===== MĚĎ (odhad podle trhu 2026) =====
    "MED-KRUHOVA": [
        (0.0, 15.0, 450.0),
        (15.0, 100.0, 420.0),
        (100.0, None, 400.0),
    ],
    "MED-PLOCHA": [
        (0.0, 15.0, 470.0),
        (15.0, None, 440.0),
    ],

    # ===== MOSAZ (z existující tabulky) =====
    "MOSAZ-KRUHOVA": [
        (0.0, 15.0, 320.0),
        (15.0, 100.0, 290.0),
        (100.0, None, 270.0),
    ],
    "MOSAZ-PLOCHA": [
        (0.0, 15.0, 340.0),
        (15.0, 100.0, 310.0),
        (100.0, None, 290.0),
    ],
    "MOSAZ-SESTIHRAN": [
        (0.0, 15.0, 330.0),
        (15.0, 100.0, 300.0),
        (100.0, None, 280.0),
    ],

    # ===== BRONZ (odhad podobný mosazi) =====
    "BRONZ-KRUHOVA": [
        (0.0, 15.0, 350.0),
        (15.0, 100.0, 320.0),
        (100.0, None, 300.0),
    ],
    "BRONZ-PLOCHA": [
        (0.0, 15.0, 370.0),
        (15.0, 100.0, 340.0),
        (100.0, None, 320.0),
    ],

    # ===== HLINÍK (z existující tabulky) =====
    "HLINIK-KRUHOVA": [
        (0.0, 15.0, 179.4),
        (15.0, 100.0, 150.5),
        (100.0, None, 110.3),
    ],
    "HLINIK-PLOCHA": [
        (0.0, 15.0, 151.6),
        (15.0, 100.0, 146.8),
        (100.0, None, 135.0),
    ],
    "HLINIK-DESKA": [
        (0.0, 15.0, 117.9),
        (15.0, None, 108.0),
    ],
    "HLINIK-SESTIHRAN": [
        (0.0, 15.0, 185.0),
        (15.0, 100.0, 155.0),
        (100.0, None, 115.0),
    ],
    "HLINIK-CTVEREC": [
        (0.0, 15.0, 165.0),
        (15.0, 100.0, 148.0),
        (100.0, None, 122.0),
    ],

    # ===== LITINA (odhad podle ocelí) =====
    "LITINA-KRUHOVA": [
        (0.0, 15.0, 55.0),
        (15.0, 100.0, 40.0),
        (100.0, None, 32.0),
    ],

    # ===== PLASTY (z existující tabulky) =====
    "PLAST-KRUHOVA": [
        (0.0, 15.0, 177.2),
        (15.0, None, 177.4),
    ],
    "PLAST-PLOCHA": [
        (0.0, 15.0, 190.0),
        (15.0, None, 190.0),
    ],
    "PLAST-DESKA": [
        (0.0, None, 336.9),
    ],
    "PLAST-BLOK": [
        (0.0, None, 350.0),
    ],
}


async def seed_catalog():
    """Seed MaterialGroups, MaterialPriceCategories a MaterialPriceTiers"""

    async with async_session() as db:
        print("=" * 80)
        print("SEED: Material Catalog (Groups + Price Categories + Tiers)")
        print("=" * 80)

        # Check if already seeded
        result = await db.execute(select(MaterialGroup))
        existing_groups = result.scalars().all()

        if len(existing_groups) >= 10:
            print(f"\n⚠️  Already seeded ({len(existing_groups)} groups found)")
            print("Skipping seed to avoid duplicates.")
            print("If you want to re-seed, delete existing data first:")
            print("  DELETE FROM material_price_tiers;")
            print("  DELETE FROM material_price_categories;")
            print("  DELETE FROM material_groups;")
            return

        # === STEP 1: Create MaterialGroups ===
        print("\n[1/3] Creating MaterialGroups...")

        group_map = {}  # code -> id mapping

        for group_data in MATERIAL_GROUPS:
            # Check if already exists
            result = await db.execute(
                select(MaterialGroup).where(MaterialGroup.code == group_data["code"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"  ⏭️  {group_data['code']} already exists")
                group_map[group_data["code"]] = existing.id
                continue

            # Create new group
            group = MaterialGroup(
                code=group_data["code"],
                name=group_data["name"],
                density=group_data["density"],
                version=1,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                created_by="system",
                updated_by="system"
            )
            db.add(group)
            await db.flush()  # Get ID

            group_map[group_data["code"]] = group.id
            print(f"  ✅ {group_data['code']} (ID: {group.id}, {group_data['density']} kg/dm³)")

        await db.commit()
        print(f"\n  📊 Total: {len(group_map)} MaterialGroups")

        # === STEP 2: Create MaterialPriceCategories ===
        print("\n[2/3] Creating MaterialPriceCategories...")

        category_map = {}  # code -> id mapping

        for cat_data in PRICE_CATEGORIES:
            # Check if already exists
            result = await db.execute(
                select(MaterialPriceCategory).where(MaterialPriceCategory.code == cat_data["code"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"  ⏭️  {cat_data['code']} already exists")
                category_map[cat_data["code"]] = existing.id
                continue

            # Get material_group_id
            group_code = cat_data["group"]
            material_group_id = group_map.get(group_code)

            if not material_group_id:
                print(f"  ❌ {cat_data['code']} - MaterialGroup '{group_code}' not found!")
                continue

            # Create new category
            category = MaterialPriceCategory(
                code=cat_data["code"],
                name=cat_data["name"],
                material_group_id=material_group_id,
                version=1,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                created_by="system",
                updated_by="system"
            )
            db.add(category)
            await db.flush()  # Get ID

            category_map[cat_data["code"]] = category.id
            print(f"  ✅ {cat_data['code']} (ID: {category.id})")

        await db.commit()
        print(f"\n  📊 Total: {len(category_map)} MaterialPriceCategories")

        # === STEP 3: Create MaterialPriceTiers ===
        print("\n[3/3] Creating MaterialPriceTiers...")

        tier_count = 0

        for cat_code, tiers in PRICE_TIERS.items():
            category_id = category_map.get(cat_code)

            if not category_id:
                print(f"  ⚠️  Category '{cat_code}' not found, skipping tiers")
                continue

            for min_weight, max_weight, price_per_kg in tiers:
                tier = MaterialPriceTier(
                    price_category_id=category_id,
                    min_weight=min_weight,
                    max_weight=max_weight,
                    price_per_kg=price_per_kg,
                    version=1,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    created_by="system",
                    updated_by="system"
                )
                db.add(tier)
                tier_count += 1

            max_weight_str = f"{max_weight}kg" if max_weight else "∞"
            print(f"  ✅ {cat_code}: {len(tiers)} tiers")

        await db.commit()
        print(f"\n  📊 Total: {tier_count} MaterialPriceTiers")

        # === SUMMARY ===
        print("\n" + "=" * 80)
        print("✅ SEED COMPLETED")
        print("=" * 80)
        print(f"  MaterialGroups:        {len(group_map)}")
        print(f"  MaterialPriceCategories: {len(category_map)}")
        print(f"  MaterialPriceTiers:      {tier_count}")
        print()
        print("💡 Tip: Now you can:")
        print("  1. View in admin UI: http://localhost:8000/admin/material-catalog")
        print("  2. Manually adjust prices if needed")
        print("  3. Run material catalog import: python scripts/import_material_catalog.py --execute")
        print()


if __name__ == "__main__":
    asyncio.run(seed_catalog())
