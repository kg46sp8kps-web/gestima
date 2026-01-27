#!/usr/bin/env python3
"""
DETAILNÍ PREVIEW importu - CO PŘESNĚ SE VYTVOŘÍ V DATABÁZI

Zobrazí vzorové záznamy pro:
1. MaterialGroup (16 kategorií)
2. MaterialPriceCategory (39 kombinací materiál+tvar)
3. MaterialItem (2405 položek)

+ jaká pole budou naplněna a jaká zůstanou NULL
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from typing import Dict, Optional, Tuple
from collections import defaultdict


# Import z import scriptu
from import_material_catalog import (
    MATERIAL_GROUPS,
    identify_material_group,
    get_price_category_code,
    correct_shape,
    PARSED_CSV,
    EXCEL_PATH
)


def show_detailed_preview():
    """Zobrazí detailní preview databázových záznamů"""

    print("=" * 100)
    print("DETAILNÍ PREVIEW - CO SE VYTVOŘÍ V DATABÁZI")
    print("=" * 100)

    # Load parsed data
    if not PARSED_CSV.exists():
        print(f"\n❌ Parsovaná data nenalezena: {PARSED_CSV}")
        return

    df_parsed = pd.read_csv(PARSED_CSV)
    print(f"\n✅ Načteno {len(df_parsed)} parsovatelných položek")

    # ========== 1. MATERIAL GROUPS ==========
    print("\n" + "=" * 100)
    print("1. MATERIAL GROUPS (tabulka: material_groups)")
    print("=" * 100)

    material_groups_to_create = {}

    for _, row in df_parsed.iterrows():
        material_code = row['material']
        group_info = identify_material_group(material_code)

        if group_info:
            code = group_info['code']
            if code not in material_groups_to_create:
                material_groups_to_create[code] = {
                    'code': code,
                    'name': group_info['name'],
                    'density': group_info['density'],
                    'item_count': 0
                }
            material_groups_to_create[code]['item_count'] += 1

    print(f"\n📦 Vytvoří se {len(material_groups_to_create)} MaterialGroup záznamů:\n")
    print(f"{'ID':>3s} | {'Code':<10s} | {'Name':<42s} | {'Density':>8s} | {'Items':>6s}")
    print("-" * 100)

    for i, (code, info) in enumerate(sorted(material_groups_to_create.items()), 1):
        print(f"{i:3d} | {info['code']:<10s} | {info['name']:<42s} | {info['density']:>7.2f}  | {info['item_count']:>6d}")

    print(f"\n💡 Pole v databázi:")
    print(f"  - id: auto-increment")
    print(f"  - code: z MATERIAL_GROUPS mappingu")
    print(f"  - name: název kategorie")
    print(f"  - density: hustota v kg/dm³ (pro výpočet váhy)")
    print(f"  - created_at, updated_at: automaticky")
    print(f"  - version: optimistic locking (default 0)")

    # ========== 2. PRICE CATEGORIES ==========
    print("\n" + "=" * 100)
    print("2. MATERIAL PRICE CATEGORIES (tabulka: material_price_categories)")
    print("=" * 100)

    price_categories_to_create = {}

    for _, row in df_parsed.iterrows():
        material_code = row['material']
        shape = row['shape']
        shape_code = row['shape_code']

        corrected_shape = correct_shape(shape, shape_code)
        group_info = identify_material_group(material_code)

        if group_info:
            cat_code, cat_name = get_price_category_code(group_info['code'], corrected_shape)

            if cat_code not in price_categories_to_create:
                price_categories_to_create[cat_code] = {
                    'code': cat_code,
                    'name': cat_name,
                    'material_group_code': group_info['code'],
                    'item_count': 0
                }
            price_categories_to_create[cat_code]['item_count'] += 1

    print(f"\n💰 Vytvoří se {len(price_categories_to_create)} PriceCategory záznamů:\n")
    print(f"{'ID':>3s} | {'Code':<27s} | {'Name':<52s} | {'Group':<10s} | {'Items':>6s}")
    print("-" * 100)

    for i, (code, info) in enumerate(sorted(price_categories_to_create.items()), 1):
        print(f"{i:3d} | {info['code']:<27s} | {info['name']:<52s} | {info['material_group_code']:<10s} | {info['item_count']:>6d}")

    print(f"\n💡 Pole v databázi:")
    print(f"  - id: auto-increment")
    print(f"  - code: kombinace materiál-tvar (např. OCEL-KRUHOVA)")
    print(f"  - name: lidsky čitelný název")
    print(f"  - material_group_id: FK → material_groups.id")
    print(f"  - created_at, updated_at, version: audit fields")

    # ========== 3. MATERIAL ITEMS - DETAILED SAMPLES ==========
    print("\n" + "=" * 100)
    print("3. MATERIAL ITEMS (tabulka: material_items)")
    print("=" * 100)

    print(f"\n📦 Vytvoří se {len(df_parsed)} MaterialItem záznamů")
    print(f"\n⚠️  ZDROJ DAT:")
    print(f"  ✅ Z Excelu: code (Pol.), parsované rozměry")
    print(f"  ❌ CHYBÍ: weight_per_meter, standard_length, norms, supplier_code, supplier")
    print(f"  → Tyto pole zůstanou NULL (doplníme později ručně nebo z jiného zdroje)")

    print(f"\n📋 UKÁZKA 10 VZOROVÝCH ZÁZNAMŮ:\n")

    # Show samples from different material types
    samples = []

    # 1. Ocel kruhová
    ocel_kr = df_parsed[(df_parsed['material'].str.startswith('1.0')) & (df_parsed['shape'] == 'ROUND_BAR')].head(1)
    samples.append(('Ocel kruhová', ocel_kr))

    # 2. Nerez kruhová
    nerez_kr = df_parsed[(df_parsed['material'].str.startswith('1.4')) & (df_parsed['shape'] == 'ROUND_BAR')].head(1)
    samples.append(('Nerez kruhová', nerez_kr))

    # 3. Hliník deska
    hlinik_de = df_parsed[(df_parsed['material'].str.startswith('3.')) & (df_parsed['shape'] == 'PLATE')].head(1)
    samples.append(('Hliník deska', hlinik_de))

    # 4. Ocel plochá
    ocel_hr = df_parsed[(df_parsed['material'].str.startswith('1.0')) & (df_parsed['shape'] == 'FLAT_BAR')].head(1)
    samples.append(('Ocel plochá', ocel_hr))

    # 5. Nerez trubka
    nerez_tr = df_parsed[(df_parsed['material'].str.startswith('1.4')) & (df_parsed['shape'] == 'TUBE')].head(1)
    samples.append(('Nerez trubka', nerez_tr))

    # 6. Mosaz kruhová
    mosaz = df_parsed[(df_parsed['material'].str.startswith('2.1')) & (df_parsed['shape'] == 'ROUND_BAR')].head(1)
    samples.append(('Mosaz kruhová', mosaz))

    # 7. Měď kruhová
    med = df_parsed[(df_parsed['material'].str.startswith('2.0')) & (df_parsed['shape'] == 'ROUND_BAR')].head(1)
    samples.append(('Měď kruhová', med))

    # 8. Šestihran (OK → HEXAGONAL_BAR)
    sesthran = df_parsed[df_parsed['shape_code'] == 'OK'].head(1)
    samples.append(('Šestihran (opraveno)', sesthran))

    # 9. Plast PA6
    plast = df_parsed[df_parsed['material'] == 'Pa6'].head(1)
    samples.append(('Plast PA6', plast))

    # 10. Ocel čtvercová
    ocel_sq = df_parsed[(df_parsed['material'].str.startswith('1.0')) & (df_parsed['shape'] == 'SQUARE_BAR')].head(1)
    samples.append(('Ocel čtvercová', ocel_sq))

    for idx, (description, sample_df) in enumerate(samples, 1):
        if sample_df.empty:
            continue

        row = sample_df.iloc[0]

        print(f"\n--- VZOREK #{idx}: {description} ---")
        print(f"  raw_code (Excel):     {row['raw_code']}")

        # Identify group and category
        material_code = row['material']
        shape = row['shape']
        shape_code = row['shape_code']
        corrected_shape = correct_shape(shape, shape_code)
        group_info = identify_material_group(material_code)

        if group_info:
            cat_code, cat_name = get_price_category_code(group_info['code'], corrected_shape)

            # Generate item name
            dimension_str = ""
            if corrected_shape == 'ROUND_BAR':
                dimension_str = f"Ø{row['diameter']:.1f}mm"
            elif corrected_shape == 'FLAT_BAR':
                dimension_str = f"{row['width']:.0f}×{row['thickness']:.0f}mm"
            elif corrected_shape == 'SQUARE_BAR':
                dimension_str = f"{row['width']:.0f}×{row['width']:.0f}mm"
            elif corrected_shape == 'HEXAGONAL_BAR':
                dimension_str = f"SW{row['diameter']:.1f}mm"
            elif corrected_shape == 'TUBE':
                dimension_str = f"Ø{row['diameter']:.0f}×{row['wall_thickness']:.0f}mm"
            elif corrected_shape == 'PLATE':
                dimension_str = f"{row['thickness']:.0f}mm"

            shape_names = {
                'ROUND_BAR': 'tyč kruhová',
                'FLAT_BAR': 'tyč plochá',
                'SQUARE_BAR': 'tyč čtvercová',
                'HEXAGONAL_BAR': 'tyč šestihranná',
                'TUBE': 'trubka',
                'PLATE': 'deska'
            }
            shape_name = shape_names.get(corrected_shape, corrected_shape)

            item_name = f"{material_code} {dimension_str} - {shape_name} {group_info['name'].lower()}"

            print(f"\n  DATABÁZOVÝ ZÁZNAM MaterialItem:")
            print(f"    id:                   [auto-increment]")
            print(f"    code:                 {row['raw_code']}")
            print(f"    name:                 {item_name}")
            print(f"    shape:                {corrected_shape}")
            print(f"    diameter:             {row['diameter'] if pd.notna(row['diameter']) else 'NULL'}")
            print(f"    width:                {row['width'] if pd.notna(row['width']) else 'NULL'}")
            print(f"    thickness:            {row['thickness'] if pd.notna(row['thickness']) else 'NULL'}")
            print(f"    wall_thickness:       {row['wall_thickness'] if pd.notna(row['wall_thickness']) else 'NULL'}")
            print(f"    weight_per_meter:     NULL  ⚠️ (není v Excelu)")
            print(f"    standard_length:      NULL  ⚠️ (není v Excelu)")
            print(f"    norms:                NULL  ⚠️ (není v Excelu)")
            print(f"    supplier_code:        NULL  ⚠️ (není v Excelu)")
            print(f"    supplier:             NULL  ⚠️ (není v Excelu)")
            print(f"    stock_available:      0.0")
            print(f"    material_group_id:    [FK → {group_info['code']}]")
            print(f"    price_category_id:    [FK → {cat_code}]")
            print(f"    created_at:           [timestamp]")
            print(f"    updated_at:           [timestamp]")
            print(f"    version:              0")

    # ========== 4. SUMMARY ==========
    print("\n" + "=" * 100)
    print("📊 SOUHRN")
    print("=" * 100)
    print(f"""
  1. MaterialGroup:          {len(material_groups_to_create):4d} záznamů
  2. PriceCategory:          {len(price_categories_to_create):4d} záznamů
  3. MaterialItem:           {len(df_parsed):4d} záznamů

  ✅ NAPLNĚNÁ POLE (z Excelu):
     - code, rozměry (diameter/width/thickness/wall_thickness), shape

  ❌ PRÁZDNÁ POLE (doplníme později):
     - weight_per_meter (kg/m)
     - standard_length (mm)
     - norms (EN/DIN)
     - supplier_code
     - supplier

  💡 POZNÁMKA:
     Prázdná pole můžeš později doplnit:
     - Ručně přes admin rozhraní
     - Importem z TheSteel.com katalogu (pokud získáš data)
     - SQL UPDATE scriptem
""")

    print("=" * 100)
    print("✅ PREVIEW DOKONČEN - žádné změny v databázi")
    print("=" * 100)


if __name__ == "__main__":
    show_detailed_preview()
