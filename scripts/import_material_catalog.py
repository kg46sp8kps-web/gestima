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


# ========== MATERIAL GROUP MAPPING (User-corrected) ==========
MATERIAL_GROUPS = {
    # Oceli (1.0xxx - 1.3xxx)
    "1.0": {"code": "10xxx", "name": "Ocel uhlíková konstrukční", "density": 7.85},
    "1.1": {"code": "11xxx", "name": "Ocel automatová", "density": 7.85},
    "1.2": {"code": "12xxx", "name": "Ocel nástrojová", "density": 7.85},
    "1.3": {"code": "13xxx", "name": "Ocel nízkolegovaná", "density": 7.85},

    # Nerez (1.4xxx)
    "1.4": {"code": "14xxx", "name": "Nerez (austenitická/feritická)", "density": 7.90},

    # Měď, bronz, mosaz (2.xxxx) - USER CORRECTION
    "2.0": {"code": "20xxx", "name": "Měď a slitiny mědi", "density": 8.90},
    "2.1": {"code": "21xxx", "name": "Mosaz", "density": 8.40},
    "2.2": {"code": "22xxx", "name": "Bronz", "density": 8.80},

    # Hliník (3.xxxx) - USER CORRECTION
    "3.0": {"code": "30xxx", "name": "Hliník čistý", "density": 2.70},
    "3.1": {"code": "31xxx", "name": "Hliník Al-Cu", "density": 2.80},
    "3.2": {"code": "32xxx", "name": "Hliník Al-Mn", "density": 2.70},
    "3.3": {"code": "33xxx", "name": "Hliník Al-Mg-Si (6xxx)", "density": 2.70},
    "3.4": {"code": "34xxx", "name": "Hliník Al-Zn", "density": 2.80},

    # Plasty
    "PA6": {"code": "PA6", "name": "Polyamid 6 (PA6)", "density": 1.14},
    "PA66": {"code": "PA66", "name": "Polyamid 66 (PA66)", "density": 1.14},
    "POM": {"code": "POM", "name": "Polyoxymethylen (POM)", "density": 1.41},
    "ABS": {"code": "ABS", "name": "Acrylonitrile butadiene styrene (ABS)", "density": 1.05},
}


def identify_material_group(material_code: str) -> Optional[Dict]:
    """
    Identifikuj MaterialGroup podle kódu materiálu.

    Args:
        material_code: např. "1.4404", "3.3547", "PA6"

    Returns:
        dict s code, name, density nebo None
    """
    # Plasty
    if material_code.upper() in ["PA6", "PA66", "POM", "ABS"]:
        return MATERIAL_GROUPS[material_code.upper()]

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
    # Material family name
    family_map = {
        "10xxx": "OCEL",
        "11xxx": "OCEL-AUTO",
        "12xxx": "OCEL-NAST",
        "13xxx": "OCEL-NIZKO",
        "14xxx": "NEREZ",
        "20xxx": "MED",
        "21xxx": "MOSAZ",
        "22xxx": "BRONZ",
        "30xxx": "HLINIK",
        "31xxx": "HLINIK",
        "32xxx": "HLINIK",
        "33xxx": "HLINIK",
        "34xxx": "HLINIK",
        "PA6": "PLAST-PA6",
        "PA66": "PLAST-PA66",
        "POM": "PLAST-POM",
        "ABS": "PLAST-ABS",
    }

    # Shape suffix
    shape_map = {
        "ROUND_BAR": ("KRUHOVA", "kruhová tyč"),
        "FLAT_BAR": ("PLOCHA", "plochá tyč"),
        "SQUARE_BAR": ("CTVERC", "čtvercová tyč"),
        "HEXAGONAL_BAR": ("SESTHRAN", "šestihranná tyč"),
        "TUBE": ("TRUBKA", "trubka"),
        "PLATE": ("DESKA", "deska"),
    }

    family = family_map.get(material_group_code, "UNKNOWN")
    shape_code, shape_name = shape_map.get(shape, ("UNKNOWN", "unknown"))

    code = f"{family}-{shape_code}"

    # Name construction
    family_names = {
        "OCEL": "Ocel konstrukční",
        "OCEL-AUTO": "Ocel automatová",
        "OCEL-NAST": "Ocel nástrojová",
        "OCEL-NIZKO": "Ocel nízkolegovaná",
        "NEREZ": "Nerez",
        "MED": "Měď",
        "MOSAZ": "Mosaz",
        "BRONZ": "Bronz",
        "HLINIK": "Hliník",
        "PLAST-PA6": "Plast PA6",
        "PLAST-PA66": "Plast PA66",
        "PLAST-POM": "Plast POM",
        "PLAST-ABS": "Plast ABS",
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

        # TODO: Implement actual import
        print("\n🚀 Spouštím import...")
        execute_import(df_parsed, material_groups_needed, price_categories_needed)


def execute_import(
    df_parsed: pd.DataFrame,
    material_groups_needed: Dict,
    price_categories_needed: Dict
):
    """
    Provede skutečný import do databáze.

    TODO: Implement actual DB import logic
    """
    print("\n⚠️  TODO: Implementovat skutečný import do DB")
    print("   - Vytvořit MaterialGroups")
    print("   - Vytvořit PriceCategories")
    print("   - Vytvořit MaterialItems")
    print("   - Propojit FK relationships")


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
