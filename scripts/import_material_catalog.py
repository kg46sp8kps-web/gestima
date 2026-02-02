#!/usr/bin/env python3
"""
Import materiálového katalogu z Excel do databáze (s DRY-RUN režimem)

Workflow:
1. Načíst parsovaná data z temp/material_codes_preview.csv
2. Načíst původní Excel pro zobrazení přeskočených položek
3. Identifikovat MaterialGroups (s opravenými kategoriemi)
4. Mapovat PriceCategories (materiál + tvar)
5. Zobrazit kompletní preview
6. Čekat na schválení před importem

Opravy podle user feedback:
- OK shape = HEXAGONAL_BAR (šestihranná tyč)
- 3.xxxx = Hliník (ne bronz)
- 2.xxxx = Měď, bronz, mosaz
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import asyncio
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


# ========== PATHS ==========
EXCEL_PATH = Path(__file__).parent.parent / "data" / "materialy_export_import.xlsx"
PARSED_CSV = Path(__file__).parent.parent / "temp" / "material_codes_preview.csv"


# ========== MATERIAL GROUP MAPPING (User-corrected 2026-02-02) ==========
MATERIAL_GROUPS = {
    # Oceli (1.0xxx - 1.3xxx)
    "1.0": {"code": "OCEL-KONS", "name": "Ocel konstrukční", "density": 7.85},
    "1.1": {"code": "OCEL-AUTO", "name": "Ocel automatová", "density": 7.85},
    "1.2": {"code": "OCEL-NAST", "name": "Ocel nástrojová", "density": 7.85},
    "1.3": {"code": "OCEL-LEG", "name": "Ocel legovaná", "density": 7.85},

    # Nerez (1.4xxx)
    "1.4": {"code": "NEREZ", "name": "Nerez", "density": 7.90},

    # Měď, bronz, mosaz (2.xxxx)
    "2.0": {"code": "MED", "name": "Měď", "density": 8.90},
    "2.1": {"code": "MOSAZ", "name": "Mosaz", "density": 8.50},
    "2.2": {"code": "BRONZ", "name": "Bronz", "density": 8.80},

    # Hliník (3.xxxx) - SLOUČENO pod jednu kategorii
    "3.0": {"code": "HLINIK", "name": "Hliník", "density": 2.70},
    "3.1": {"code": "HLINIK", "name": "Hliník", "density": 2.70},
    "3.2": {"code": "HLINIK", "name": "Hliník", "density": 2.70},
    "3.3": {"code": "HLINIK", "name": "Hliník", "density": 2.70},
    "3.4": {"code": "HLINIK", "name": "Hliník", "density": 2.70},

    # Litina (cast iron)
    "GG250": {"code": "LITINA-GG", "name": "Litina šedá", "density": 7.20},
    "GGG40": {"code": "LITINA-TV", "name": "Litina tvárná", "density": 7.10},
    "GG": {"code": "LITINA-GG", "name": "Litina šedá", "density": 7.20},  # Fallback for GG200, GG300, etc.
    "GGG": {"code": "LITINA-TV", "name": "Litina tvárná", "density": 7.10},  # Fallback for GGG50, etc.

    # Plasty - SLOUČENO pod jednu kategorii (průměrná hustota)
    "PA6": {"code": "PLAST", "name": "Plasty", "density": 1.20},
    "PA6G": {"code": "PLAST", "name": "Plasty", "density": 1.20},
    "PA66": {"code": "PLAST", "name": "Plasty", "density": 1.20},
    "POM": {"code": "PLAST", "name": "Plasty", "density": 1.20},
    "POM-C": {"code": "PLAST", "name": "Plasty", "density": 1.20},
    "PE300": {"code": "PLAST", "name": "Plasty", "density": 1.20},
    "PE500": {"code": "PLAST", "name": "Plasty", "density": 1.20},
    "PE1000": {"code": "PLAST", "name": "Plasty", "density": 1.20},
    "PC": {"code": "PLAST", "name": "Plasty", "density": 1.20},
    "PEEK": {"code": "PLAST", "name": "Plasty", "density": 1.20},
    "PEEK1000": {"code": "PLAST", "name": "Plasty", "density": 1.20},
    "PEEK-GF30": {"code": "PLAST", "name": "Plasty", "density": 1.20},
    "MAPA": {"code": "PLAST", "name": "Plasty", "density": 1.20},
    "ABS": {"code": "PLAST", "name": "Plasty", "density": 1.20},
}


def identify_material_group(material_code: str) -> Optional[Dict]:
    """
    Identifikuj MaterialGroup podle kódu materiálu.

    Args:
        material_code: např. "1.4404", "3.3547", "PA6", "GG250", "GGG40"

    Returns:
        dict s code, name, density nebo None
    """
    material_upper = material_code.upper()

    # Cast iron (litina) - exact match first
    if material_upper in ["GG250", "GGG40"]:
        return MATERIAL_GROUPS[material_upper]

    # Cast iron (litina) - prefix match for other grades (GG200, GG300, GGG50, etc.)
    if material_upper.startswith("GGG"):
        return MATERIAL_GROUPS["GGG"]
    if material_upper.startswith("GG"):
        return MATERIAL_GROUPS["GG"]

    # Plasty - exact match
    plastic_list = ["PA6", "PA6G", "PA66", "POM", "POM-C", "PE300", "PE500", "PE1000",
                    "PC", "PEEK", "PEEK1000", "PEEK-GF30", "MAPA", "ABS"]
    if material_upper in plastic_list:
        return MATERIAL_GROUPS[material_upper]

    # Kovové materiály (formát X.YYYY)
    if '.' in material_code:
        prefix = material_code[:3]  # "1.0", "1.4", "3.3"

        if prefix in MATERIAL_GROUPS:
            return MATERIAL_GROUPS[prefix]

        # Fallback: prvních 2 znaky (např. "2.0xxx" → "2.0")
        prefix_short = material_code[:2]
        if prefix_short in MATERIAL_GROUPS:
            return MATERIAL_GROUPS[prefix_short]

    return None


# ========== PRICE CATEGORY MAPPING ==========
def get_price_category_code(material_group_code: str, shape: str) -> Tuple[str, str]:
    """
    Vrátí (code, name) pro PriceCategory podle material group + shape.

    Args:
        material_group_code: např. "14xxx" (nerez), "33xxx" (hliník)
        shape: StockShape enum value (např. "ROUND_BAR", "PLATE")

    Returns:
        (code, name) tuple
    """
    # Material family mapping (corrected 2026-02-02)
    family_map = {
        "OCEL-KONS": "OCEL-KONS",
        "OCEL-AUTO": "OCEL-AUTO",
        "OCEL-NAST": "OCEL-NAST",
        "OCEL-LEG": "OCEL-LEG",
        "NEREZ": "NEREZ",
        "MED": "MED",
        "MOSAZ": "MOSAZ",
        "BRONZ": "BRONZ",
        "HLINIK": "HLINIK",
        "LITINA-GG": "LITINA-GG",
        "LITINA-TV": "LITINA-TV",
        "PLAST": "PLAST",
    }

    # Shape suffix (aligned with seed_material_catalog.py)
    shape_map = {
        "ROUND_BAR": ("KRUHOVA", "kruhová tyč"),
        "FLAT_BAR": ("PLOCHA", "plochá tyč"),
        "SQUARE_BAR": ("CTVEREC", "čtvercová tyč"),
        "HEXAGONAL_BAR": ("SESTIHRAN", "šestihran"),
        "TUBE": ("TRUBKA", "trubka"),
        "PLATE": ("DESKA", "deska"),
    }

    family = family_map.get(material_group_code, "UNKNOWN")
    shape_code, shape_name = shape_map.get(shape, ("UNKNOWN", "unknown"))

    # Special case: PLAST profily (CTVERC, PLOCHA) → DESKA
    if family == "PLAST" and shape in ["SQUARE_BAR", "FLAT_BAR"]:
        shape_code, shape_name = ("DESKA", "deska")

    code = f"{family}-{shape_code}"

    # Name construction (aligned with seed_material_catalog.py)
    family_names = {
        "OCEL-KONS": "OCEL konstrukční",
        "OCEL-AUTO": "OCEL automatová",
        "OCEL-NAST": "OCEL nástrojová",
        "OCEL-LEG": "OCEL legovaná",
        "NEREZ": "NEREZ",
        "MED": "MĚĎ",
        "MOSAZ": "MOSAZ",
        "BRONZ": "BRONZ",
        "HLINIK": "HLINÍK",
        "LITINA-GG": "LITINA",
        "LITINA-TV": "LITINA",
        "PLAST": "PLASTY",
    }

    family_name_full = family_names.get(family, family)
    name = f"{family_name_full} - {shape_name}"

    return code, name


# ========== SHAPE CORRECTION (User feedback: OK = HEXAGONAL_BAR) ==========
def correct_shape(parsed_shape: str, shape_code: str) -> str:
    """
    Opraví shape podle user feedback.

    User correction: OK = šestihranná tyč (HEXAGONAL_BAR)
    """
    if shape_code == "OK":
        return "HEXAGONAL_BAR"
    return parsed_shape


# ========== PRICE TIER TEMPLATE MAPPING ==========
# Nové kategorie → Template pro kopírování price tiers
# Používá seed_price_categories.py naming (OCEL-KRUHOVA, OCEL-PLOCHA, atd.)
TIER_TEMPLATES = {
    # OCEL KONSTRUKČNÍ
    "OCEL-KONS-CTVEREC": "OCEL-KRUHOVA",
    "OCEL-KONS-SESTIHRAN": "OCEL-KRUHOVA",

    # OCEL AUTOMATOVÁ (NOVÉ)
    "OCEL-AUTO-KRUHOVA": "OCEL-KRUHOVA",
    "OCEL-AUTO-PLOCHA": "OCEL-PLOCHA",
    "OCEL-AUTO-SESTIHRAN": "OCEL-KRUHOVA",

    # OCEL NÁSTROJOVÁ (částečně existuje)
    "OCEL-NAST-PLOCHA": "OCEL-PLOCHA",
    "OCEL-NAST-CTVEREC": "OCEL-NASTROJOVA",  # seed má OCEL-NAST-KRUHOVA
    "OCEL-NAST-SESTIHRAN": "OCEL-NASTROJOVA",

    # OCEL LEGOVANÁ (NOVÉ)
    "OCEL-LEG-KRUHOVA": "OCEL-KRUHOVA",
    "OCEL-LEG-PLOCHA": "OCEL-PLOCHA",
    "OCEL-LEG-CTVEREC": "OCEL-KRUHOVA",

    # NEREZ (částečně existuje)
    "NEREZ-CTVEREC": "NEREZ-KRUHOVA",
    "NEREZ-SESTIHRAN": "NEREZ-KRUHOVA",
    "NEREZ-TRUBKA": "NEREZ-KRUHOVA",

    # MĚĎ (NOVÉ)
    "MED-KRUHOVA": "MOSAZ-BRONZ",  # seed nemá MED, použijeme MOSAZ
    "MED-PLOCHA": "NEREZ-PLOCHA",

    # MOSAZ (částečně existuje)
    "MOSAZ-CTVEREC": "MOSAZ-KRUHOVA",  # seed má MOSAZ-KRUHOVA

    # BRONZ (NOVÉ)
    "BRONZ-KRUHOVA": "MOSAZ-BRONZ",  # seed má MOSAZ-BRONZ
    "BRONZ-PLOCHA": "NEREZ-PLOCHA",
    "BRONZ-CTVEREC": "MOSAZ-BRONZ",

    # HLINÍK (částečně existuje)
    "HLINIK-CTVEREC": "HLINIK-KRUHOVA",
    "HLINIK-SESTIHRAN": "HLINIK-KRUHOVA",

    # PLASTY (NOVÉ kromě základních)
    # seed má: PLAST-KRUHOVA, PLAST-PLOCHA, PLAST-DESKA, PLAST-BLOK

    # LITINA (NOVÉ)
    "LITINA-KRUHOVA": "OCEL-KRUHOVA",  # seed má jen generic LITINA-KRUHOVA
}


def get_tier_template(new_category_code: str) -> Optional[str]:
    """
    Vrátí code existující kategorie, ze které zkopírovat tier strukturu.

    Args:
        new_category_code: Code nové kategorie (např. "OCEL-AUTO-KRUHOVA")

    Returns:
        Code existující kategorie (např. "OCEL-KRUHOVA") nebo None
    """
    return TIER_TEMPLATES.get(new_category_code)


# ========== DRY RUN PREVIEW ==========
def preview_import(dry_run: bool = True):
    """
    Zobrazí preview importu s kategoriemi MaterialGroup a PriceCategory.

    Args:
        dry_run: Pokud True, pouze zobrazí preview bez zápisu do DB
    """
    print("=" * 100)
    print("IMPORT MATERIÁLOVÉHO KATALOGU - PREVIEW")
    print("=" * 100)

    # 1. Load parsed data
    if not PARSED_CSV.exists():
        print(f"\n❌ Parsovaná data nenalezena: {PARSED_CSV}")
        print("   Spusť nejdřív: python scripts/analyze_material_codes.py")
        return

    df_parsed = pd.read_csv(PARSED_CSV)
    print(f"\n✅ Parsovatelné položky: {len(df_parsed)}")

    # 2. Load original Excel for skipped items
    if not EXCEL_PATH.exists():
        print(f"\n❌ Excel katalog nenalezen: {EXCEL_PATH}")
        return

    df_excel = pd.read_excel(EXCEL_PATH)
    all_codes = set(df_excel['Pol.'].astype(str))
    parsed_codes = set(df_parsed['raw_code'].astype(str))
    skipped_codes = all_codes - parsed_codes

    print(f"⊘  Přeskočené položky: {len(skipped_codes)}")
    print(f"📊 Celkem v katalogu:  {len(all_codes)}")

    # 3. Analyze MaterialGroups
    print("\n" + "=" * 100)
    print("MATERIAL GROUPS (opravené kategorie)")
    print("=" * 100)

    material_groups_needed = {}  # {code: {name, density, count}}

    for _, row in df_parsed.iterrows():
        material_code = row['material']
        group_info = identify_material_group(material_code)

        if group_info:
            code = group_info['code']
            if code not in material_groups_needed:
                material_groups_needed[code] = {
                    'name': group_info['name'],
                    'density': group_info['density'],
                    'count': 0,
                    'samples': []
                }
            material_groups_needed[code]['count'] += 1
            if len(material_groups_needed[code]['samples']) < 3:
                material_groups_needed[code]['samples'].append(material_code)

    print(f"\n📦 Počet Material Groups: {len(material_groups_needed)}\n")

    for code, info in sorted(material_groups_needed.items()):
        samples = ", ".join(info['samples'][:3])
        print(f"  {code:10s} | {info['name']:40s} | {info['density']:.2f} kg/dm³ | {info['count']:4d}× | např: {samples}")

    # 4. Analyze PriceCategories
    print("\n" + "=" * 100)
    print("PRICE CATEGORIES (materiál + tvar)")
    print("=" * 100)

    price_categories_needed = {}  # {code: {name, material_group_code, count}}

    for _, row in df_parsed.iterrows():
        material_code = row['material']
        shape = row['shape']
        shape_code = row['shape_code']

        # Correct shape (OK → HEXAGONAL_BAR)
        corrected_shape = correct_shape(shape, shape_code)

        group_info = identify_material_group(material_code)
        if group_info:
            cat_code, cat_name = get_price_category_code(group_info['code'], corrected_shape)

            if cat_code not in price_categories_needed:
                price_categories_needed[cat_code] = {
                    'name': cat_name,
                    'material_group_code': group_info['code'],
                    'count': 0
                }
            price_categories_needed[cat_code]['count'] += 1

    print(f"\n💰 Počet Price Categories: {len(price_categories_needed)}\n")

    for code, info in sorted(price_categories_needed.items()):
        print(f"  {code:25s} | {info['name']:50s} | {info['count']:4d}×")

    # 5. Show skipped items (sample)
    print("\n" + "=" * 100)
    print("PŘESKOČENÉ POLOŽKY (důvody)")
    print("=" * 100)

    print(f"\n⊘  Celkem přeskočeno: {len(skipped_codes)}\n")

    # Categorize skipped reasons
    skipped_categories = defaultdict(list)

    for code in list(skipped_codes)[:50]:  # Sample first 50
        code_str = str(code).strip()

        if code_str.startswith('000-') and not any(p in code_str for p in ['Pa6', 'POM', 'ABS']):
            skipped_categories['System kódy (000-)'].append(code_str)
        elif 'vypalek' in code_str.lower():
            skipped_categories['Výpalky'].append(code_str)
        elif '-EP' in code_str:
            skipped_categories['EP povrch (hliník elektropolovaný)'].append(code_str)
        else:
            skipped_categories['Ostatní (nerozpoznaný formát)'].append(code_str)

    for reason, codes in sorted(skipped_categories.items()):
        print(f"  {reason}: {len(codes)}×")
        for code in codes[:5]:
            print(f"    - {code}")
        if len(codes) > 5:
            print(f"    ... a dalších {len(codes) - 5}")
        print()

    # 6. Show import preview (sample items)
    print("\n" + "=" * 100)
    print("PREVIEW IMPORTU (ukázka prvních 20 položek)")
    print("=" * 100)

    print(f"\n{'Kód':<25s} | {'Tvar':<15s} | {'Materiál':<10s} | {'Group':<10s} | {'Price Category':<25s}")
    print("-" * 100)

    for idx, row in df_parsed.head(20).iterrows():
        material_code = row['material']
        shape = row['shape']
        shape_code = row['shape_code']
        code = row['raw_code']

        corrected_shape = correct_shape(shape, shape_code)
        group_info = identify_material_group(material_code)

        if group_info:
            cat_code, _ = get_price_category_code(group_info['code'], corrected_shape)
            print(f"{code:<25s} | {corrected_shape:<15s} | {material_code:<10s} | {group_info['code']:<10s} | {cat_code:<25s}")

    print("\n" + "=" * 100)

    if dry_run:
        print("🔍 DRY RUN REŽIM - žádné změny v databázi")
        print("\nPro import spusť s --execute:")
        print("  python scripts/import_material_catalog.py --execute")
    else:
        print("⚠️  EXECUTE REŽIM - provede import do databáze!")
        print("\nPokračovat? (y/n): ", end='')
        confirm = input().strip().lower()

        if confirm != 'y':
            print("❌ Import zrušen")
            return

        # Execute import (async)
        print("\n🚀 Spouštím import...")
        asyncio.run(execute_import(df_parsed, material_groups_needed, price_categories_needed))


async def execute_import(
    df_parsed: pd.DataFrame,
    material_groups_needed: Dict,
    price_categories_needed: Dict
):
    """
    Provede skutečný import do databáze.

    Args:
        df_parsed: Parsovaná data z CSV
        material_groups_needed: {code: {name, density, count, samples}}
        price_categories_needed: {code: {name, material_group_code, count}}
    """
    from app.database import async_session
    from app.models.material import MaterialGroup, MaterialPriceCategory, MaterialItem
    from app.models.enums import StockShape
    from sqlalchemy import select
    from sqlalchemy.exc import IntegrityError
    import random

    print("\n" + "=" * 100)
    print("🚀 SPOUŠTÍM IMPORT DO DATABÁZE")
    print("=" * 100)

    async with async_session() as session:
        try:
            # ========== KROK 1: MaterialGroups ==========
            print(f"\n📦 Vytvářím MaterialGroups ({len(material_groups_needed)})...")

            group_id_map = {}  # {code: db_id}

            for code, info in material_groups_needed.items():
                # Check if exists
                result = await session.execute(
                    select(MaterialGroup).where(MaterialGroup.code == code)
                )
                existing = result.scalar_one_or_none()

                if existing:
                    print(f"   ✓ {code:10s} - již existuje (ID: {existing.id})")
                    group_id_map[code] = existing.id
                else:
                    # Create new
                    new_group = MaterialGroup(
                        code=code,
                        name=info['name'],
                        density=info['density']
                    )
                    session.add(new_group)
                    await session.flush()  # Get ID
                    group_id_map[code] = new_group.id
                    print(f"   + {code:10s} - vytvořeno (ID: {new_group.id}) - {info['name']}")

            await session.commit()
            print(f"   ✅ MaterialGroups hotovo ({len(group_id_map)} skupin)")

            # ========== KROK 2: PriceCategories + Tiers ==========
            print(f"\n💰 Vytvářím PriceCategories ({len(price_categories_needed)})...")

            category_id_map = {}  # {code: db_id}
            tiers_created_count = 0

            for code, info in price_categories_needed.items():
                # Check if exists
                result = await session.execute(
                    select(MaterialPriceCategory).where(MaterialPriceCategory.code == code)
                )
                existing = result.scalar_one_or_none()

                if existing:
                    print(f"   ✓ {code:25s} - již existuje (ID: {existing.id})")
                    category_id_map[code] = existing.id
                else:
                    # Get MaterialGroup ID
                    material_group_code = info['material_group_code']
                    material_group_id = group_id_map.get(material_group_code)

                    # Create new category
                    new_category = MaterialPriceCategory(
                        code=code,
                        name=info['name'],
                        material_group_id=material_group_id
                    )
                    session.add(new_category)
                    await session.flush()
                    category_id_map[code] = new_category.id
                    print(f"   + {code:25s} - vytvořeno (ID: {new_category.id})")

                    # Auto-create price tiers from template
                    template_code = get_tier_template(code)
                    if template_code:
                        # Find template category
                        template_result = await session.execute(
                            select(MaterialPriceCategory).where(MaterialPriceCategory.code == template_code)
                        )
                        template_category = template_result.scalar_one_or_none()

                        if template_category:
                            # Load tiers from template
                            from app.models.material import MaterialPriceTier
                            tiers_result = await session.execute(
                                select(MaterialPriceTier)
                                .where(MaterialPriceTier.price_category_id == template_category.id)
                                .order_by(MaterialPriceTier.min_weight)
                            )
                            template_tiers = tiers_result.scalars().all()

                            if template_tiers:
                                print(f"      └─ Kopíruji {len(template_tiers)} tiers z {template_code} (80% cena):")
                                for tier in template_tiers:
                                    # Copy tier structure with 80% price
                                    new_tier = MaterialPriceTier(
                                        price_category_id=new_category.id,
                                        min_weight=tier.min_weight,
                                        max_weight=tier.max_weight,
                                        price_per_kg=round(tier.price_per_kg * 0.8, 1)
                                    )
                                    session.add(new_tier)
                                    tiers_created_count += 1

                                    max_w = f"{tier.max_weight}kg" if tier.max_weight else "∞"
                                    print(f"         [{tier.min_weight}-{max_w:6}] → {new_tier.price_per_kg:6.1f} Kč/kg")
                        else:
                            print(f"      ⚠️  Template {template_code} nenalezen - tiers nezkopírovány")
                    else:
                        print(f"      ⚠️  Žádný template - tiers je třeba nastavit manuálně")

            await session.commit()
            print(f"   ✅ PriceCategories hotovo ({len(category_id_map)} kategorií, {tiers_created_count} tiers)")
            if tiers_created_count > 0:
                print(f"   ℹ️  Price Tiers vytvořeny s 80% cenou z template kategorií - upravitelné později!")

            # ========== KROK 3: MaterialItems ==========
            print(f"\n📋 Vytvářím MaterialItems ({len(df_parsed)})...")

            created_count = 0
            skipped_count = 0

            for idx, row in df_parsed.iterrows():
                material_code = row['material']
                shape = row['shape']
                shape_code = row['shape_code']
                code = row['raw_code']

                # Correct shape (OK → HEXAGONAL_BAR)
                corrected_shape = correct_shape(shape, shape_code)

                # Get MaterialGroup
                group_info = identify_material_group(material_code)
                if not group_info:
                    print(f"   ⊘ {code} - nelze identifikovat MaterialGroup")
                    skipped_count += 1
                    continue

                material_group_id = group_id_map.get(group_info['code'])
                if not material_group_id:
                    print(f"   ⊘ {code} - MaterialGroup nenalezen v DB")
                    skipped_count += 1
                    continue

                # Get PriceCategory
                cat_code, cat_name = get_price_category_code(group_info['code'], corrected_shape)
                price_category_id = category_id_map.get(cat_code)
                if not price_category_id:
                    print(f"   ⊘ {code} - PriceCategory nenalezena v DB ({cat_code})")
                    skipped_count += 1
                    continue

                # Check if already exists
                result = await session.execute(
                    select(MaterialItem).where(MaterialItem.code == code)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    skipped_count += 1
                    continue

                # Generate material_number (8-digit: 20XXXXXX)
                material_number = f"20{random.randint(100000, 999999)}"

                # Ensure unique
                while True:
                    result = await session.execute(
                        select(MaterialItem).where(MaterialItem.material_number == material_number)
                    )
                    if result.scalar_one_or_none() is None:
                        break
                    material_number = f"20{random.randint(100000, 999999)}"

                # Parse dimensions
                diameter = row['diameter'] if pd.notna(row['diameter']) else None
                width = row['width'] if pd.notna(row['width']) else None
                thickness = row['thickness'] if pd.notna(row['thickness']) else None
                wall_thickness = row['wall_thickness'] if pd.notna(row['wall_thickness']) else None

                # Lookup norms from MaterialNorm table
                from app.models.material_norm import MaterialNorm
                norms_text = None
                norm_result = await session.execute(
                    select(MaterialNorm).where(
                        (MaterialNorm.w_nr == material_code) |
                        (MaterialNorm.en_iso == material_code) |
                        (MaterialNorm.csn == material_code) |
                        (MaterialNorm.aisi == material_code)
                    ).limit(1)
                )
                norm_entry = norm_result.scalar_one_or_none()
                if norm_entry:
                    # Build norms string from available fields
                    norms_parts = []
                    if norm_entry.w_nr:
                        norms_parts.append(f"W.Nr: {norm_entry.w_nr}")
                    if norm_entry.en_iso:
                        norms_parts.append(f"EN: {norm_entry.en_iso}")
                    if norm_entry.csn:
                        norms_parts.append(f"ČSN: {norm_entry.csn}")
                    if norm_entry.aisi:
                        norms_parts.append(f"AISI: {norm_entry.aisi}")
                    norms_text = ", ".join(norms_parts) if norms_parts else None

                # Create MaterialItem
                try:
                    new_item = MaterialItem(
                        material_number=material_number,
                        code=code,
                        name=f"{material_code} {code.split('-', 1)[1] if '-' in code else code}",
                        shape=StockShape[corrected_shape],
                        diameter=diameter,
                        width=width,
                        thickness=thickness,
                        wall_thickness=wall_thickness,
                        norms=norms_text,  # ← Naplnit z MaterialNorm
                        material_group_id=material_group_id,
                        price_category_id=price_category_id,
                        stock_available=0.0
                    )
                    session.add(new_item)
                    created_count += 1

                    if created_count % 100 == 0:
                        await session.flush()
                        print(f"   ... {created_count} položek vytvořeno")

                except Exception as e:
                    print(f"   ⊘ {code} - chyba: {str(e)}")
                    skipped_count += 1

            await session.commit()

            print(f"\n   ✅ MaterialItems hotovo:")
            print(f"      + Vytvořeno:  {created_count}")
            print(f"      ⊘ Přeskočeno: {skipped_count}")

            print("\n" + "=" * 100)
            print("✅ IMPORT ÚSPĚŠNĚ DOKONČEN")
            print("=" * 100)
            print(f"\n📊 Souhrn:")
            print(f"   MaterialGroups:     {len(group_id_map)}")
            print(f"   PriceCategories:    {len(category_id_map)}")
            print(f"   MaterialItems:      {created_count}")
            print(f"\n⚠️  DALŠÍ KROKY:")
            print(f"   1. Nastavit Price Tiers pro nové kategorie (admin UI)")
            print(f"   2. Doplnit supplier info (supplier, supplier_code)")
            print(f"   3. Doplnit katalogové info (weight_per_meter, standard_length, norms)")

        except Exception as e:
            await session.rollback()
            print(f"\n❌ CHYBA PŘI IMPORTU: {str(e)}")
            import traceback
            traceback.print_exc()
            raise


# ========== MAIN ==========
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Import materiálového katalogu")
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Provést skutečný import (default: dry-run preview)'
    )

    args = parser.parse_args()

    preview_import(dry_run=not args.execute)


if __name__ == "__main__":
    main()
