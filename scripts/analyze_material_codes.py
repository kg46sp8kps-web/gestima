#!/usr/bin/env python3
"""
Analýza materiálových kódů z Excel katalogu (PREVIEW před importem)

Formát kódů:
  [MATERIÁL]-[TVAR][ROZMĚRY]-[STAV]

Příklady:
  1.4404-KR240.000-O  → 1.4404 (nerez), KR (kruhová), Ø24mm, O (žíhaný)
  1.0036-HR010x005-T  → 1.0036 (ocel), HR (hranaté), 10×5mm, T (tažený)
  1.0039-TR010x002-T  → 1.0039, TR (trubka), Ø10mm/2mm stěna, T

Tvary:
  KR = Kruhová tyč (ROUND_BAR)
  HR = Hranaté tyč (SQUARE_BAR nebo FLAT_BAR)
  OK = ? (pravděpodobně ocel konstrukční - určit ze vzorů)
  TR = Trubka (TUBE)
  DE = ? (pravděpodobně desková/plochá)

Stavy:
  T = Tažený (drawn)
  V = Válcovaný (rolled)
  O = Žíhaný (annealed)
"""

import pandas as pd
import re
from pathlib import Path
from typing import Dict, Optional, Tuple
import json

# Paths
EXCEL_PATH = Path(__file__).parent.parent / "data" / "materialy_export_import.xlsx"
OUTPUT_CSV = Path(__file__).parent.parent / "temp" / "material_codes_preview.csv"
OUTPUT_JSON = Path(__file__).parent.parent / "temp" / "material_codes_summary.json"


def parse_material_code(code: str) -> Optional[Dict]:
    """
    Parse material code into components.

    Returns:
        dict with keys: material, shape, dimensions, state, raw_code
        None if unparseable
    """
    code_str = str(code).strip()

    # Skip system codes, vypaleky
    if code_str.startswith('000-') or 'vypalek' in code_str.lower():
        # Exception: 000-nab-mat-[PLASTIC] are valid plastic codes
        if not any(p in code_str for p in ['Pa6', 'POM', 'ABS']):
            return None

    # Try plastic formats first
    plastic_result = parse_plastic_code(code_str)
    if plastic_result:
        return plastic_result

    # Pattern: [MATERIAL]-[SHAPE][DIMENSIONS]-[STATE]
    # Examples:
    #   1.4404-KR240.000-O
    #   1.0036-HR010x005-T
    #   1.0039-TR010x002-T

    # Try metal plates with specific dimensions first: [MATERIAL]-DE[TTT]-[WWW]-[LLL]-[STATE]
    # Example: 3.3547-DE010-177-302-F
    plate_pattern = r'^([1-3]\.\d{4})-DE(\d{3})-(\d{3})-(\d{3})-([A-Z]+)$'
    plate_match = re.match(plate_pattern, code_str)

    if plate_match:
        material, thickness, width, length, state = plate_match.groups()

        # Skip aluminum plates with unwanted surface treatments
        # Material 3.xxxx = aluminum/non-ferrous
        if material.startswith('3.'):
            # Skip: EP (elektropolovaný) - elektricky leštěný povrch
            # Keep: L (litý), F (frézovaný), V (válcovaný)
            if state == 'EP':
                return None  # Skip elektropolished surface

        return {
            'raw_code': code_str,
            'material': material,
            'material_type': 'metal',
            'shape_code': 'DE',
            'dimensions_raw': f'{thickness}-{width}-{length}',
            'state': state,
            'shape': 'PLATE',
            'diameter': None,
            'width': float(width),
            'thickness': float(thickness),
            'wall_thickness': None,
            'length': float(length)  # Extra field for plates
        }

    # Try standard metal format: [MATERIAL]-[SHAPE][DIMENSIONS]-[STATE]
    pattern = r'^([1-3]\.\d{4})(?:\+\w+)?-([A-Z]{2})([0-9x.]+)-([A-Z]+)$'
    match = re.match(pattern, code_str)

    if not match:
        return None

    material, shape, dimensions, state = match.groups()

    # Parse dimensions based on shape
    parsed_dims = parse_dimensions(shape, dimensions)

    if not parsed_dims:
        return None

    return {
        'raw_code': code_str,
        'material': material,
        'material_type': 'metal',
        'shape_code': shape,
        'dimensions_raw': dimensions,
        'state': state,
        **parsed_dims
    }


def parse_plastic_code(code: str) -> Optional[Dict]:
    """
    Parse plastic material codes.

    Formats:
      000-nab-mat-Pa6
      000-nab-mat-Pa6-natur
      000-nab-mat-POM
      PA66-GF30-DE012-000-P-B
    """
    code_upper = code.upper()

    # Format 1: 000-nab-mat-[PLASTIC]
    if '000-NAB-MAT-' in code_upper:
        plastic_part = code.split('000-nab-mat-')[-1]
        # Extract plastic name (before any additional suffix)
        plastic_name = plastic_part.split('-')[0]

        return {
            'raw_code': code,
            'material': plastic_name,
            'material_type': 'plastic',
            'shape_code': 'GENERIC',
            'dimensions_raw': '',
            'state': 'STOCK',
            'shape': 'ROUND_BAR',  # Default for generic stock
            'diameter': None,
            'width': None,
            'thickness': None,
            'wall_thickness': None
        }

    # Format 2: PA66-GF30-DE012-000-P-B
    # [PLASTIC]-[SHAPE][DIMENSIONS]-[...]-[STATE]-[...]
    plastic_match = re.match(r'^(PA\d+|POM|ABS)(?:-GF\d+)?-([A-Z]{2})(\d+)(?:-\d+)?-([A-Z])-?', code_upper)
    if plastic_match:
        plastic, shape_code, dimensions, state = plastic_match.groups()

        # Parse dimensions
        parsed_dims = parse_dimensions(shape_code, dimensions)
        if not parsed_dims:
            return None

        return {
            'raw_code': code,
            'material': plastic,
            'material_type': 'plastic',
            'shape_code': shape_code,
            'dimensions_raw': dimensions,
            'state': state,
            **parsed_dims
        }

    return None


def parse_dimensions(shape: str, dimensions: str) -> Optional[Dict]:
    """
    Parse dimension string based on shape.

    Returns:
        dict with keys depending on shape:
        - KR: diameter
        - HR: width, thickness
        - TR: diameter, wall_thickness
        - OK: diameter (?)
        - DE: thickness (?)
    """

    if shape == 'KR':  # Kruhová tyč (round bar)
        # Format: 240.000 → Ø24.0mm or Ø240mm?
        # Assume format XXX.000 = XX.X mm (240.000 = 24.0mm)
        match = re.match(r'(\d+)\.(\d+)', dimensions)
        if match:
            major, minor = match.groups()
            diameter = float(f"{major[:-1]}.{major[-1]}")  # 240 → 24.0
            return {
                'shape': 'ROUND_BAR',
                'diameter': diameter,
                'width': None,
                'thickness': None,
                'wall_thickness': None
            }

    elif shape == 'HR':  # Hranaté (flat bar or square bar)
        # Format: 010x005 → 10mm × 5mm
        match = re.match(r'(\d+)x(\d+)', dimensions)
        if match:
            w, t = match.groups()
            width = float(w)
            thickness = float(t)

            # Square bar if width == thickness
            bar_shape = 'SQUARE_BAR' if width == thickness else 'FLAT_BAR'

            return {
                'shape': bar_shape,
                'diameter': None,
                'width': width,
                'thickness': thickness,
                'wall_thickness': None
            }

    elif shape == 'TR':  # Trubka (tube)
        # Format: 010x002 → Ø10mm, wall 2mm
        match = re.match(r'(\d+)x(\d+)', dimensions)
        if match:
            diameter, wall = match.groups()
            return {
                'shape': 'TUBE',
                'diameter': float(diameter),
                'width': None,
                'thickness': None,
                'wall_thickness': float(wall)
            }

    elif shape == 'OK':
        # Unknown shape - analyze from examples
        # Assume similar to KR?
        match = re.match(r'(\d+)\.(\d+)', dimensions)
        if match:
            major, _ = match.groups()
            diameter = float(f"{major[:-1]}.{major[-1]}")
            return {
                'shape': 'ROUND_BAR',  # Tentative
                'diameter': diameter,
                'width': None,
                'thickness': None,
                'wall_thickness': None
            }

    elif shape == 'DE':
        # Desková? Analyze from examples
        match = re.match(r'(\d+)\.?(\d*)', dimensions)
        if match:
            thickness_str = match.group(1)
            if '.' in dimensions:
                thickness = float(dimensions.replace('-', '.'))
            else:
                thickness = float(thickness_str)
            return {
                'shape': 'PLATE',  # Tentative
                'diameter': None,
                'width': None,
                'thickness': thickness,
                'wall_thickness': None
            }

    return None


def analyze_catalog():
    """Main analysis function"""
    print("=" * 80)
    print("ANALÝZA KATALOGU: materialy_export_import.xlsx")
    print("=" * 80)

    # Load Excel
    df = pd.read_excel(EXCEL_PATH)
    print(f"\nCelkem řádků: {len(df)}")

    # Parse all codes
    parsed = []
    skipped = []

    for code in df['Pol.']:
        result = parse_material_code(code)
        if result:
            parsed.append(result)
        else:
            skipped.append(code)

    print(f"\n✅ Parsovatelné kódy: {len(parsed)}")
    print(f"⊘  Přeskočené kódy:   {len(skipped)}")

    # Create DataFrame
    df_parsed = pd.DataFrame(parsed)

    # Statistics
    print("\n" + "=" * 80)
    print("STATISTIKY")
    print("=" * 80)

    print("\nMateriály (TOP 10):")
    for mat, count in df_parsed['material'].value_counts().head(10).items():
        print(f"  {mat}: {count:4d} variant")

    print("\nTvary:")
    for shape, count in df_parsed['shape'].value_counts().items():
        print(f"  {shape:15s}: {count:4d} položek")

    print("\nStavy:")
    for state, count in df_parsed['state'].value_counts().items():
        print(f"  {state}: {count:4d} položek")

    # Save preview CSV
    OUTPUT_CSV.parent.mkdir(exist_ok=True)
    df_parsed.to_csv(OUTPUT_CSV, index=False)
    print(f"\n✅ Preview uložen: {OUTPUT_CSV}")

    # Save summary JSON
    summary = {
        'total_rows': len(df),
        'parsed': len(parsed),
        'skipped': len(skipped),
        'materials': df_parsed['material'].value_counts().to_dict(),
        'shapes': df_parsed['shape'].value_counts().to_dict(),
        'states': df_parsed['state'].value_counts().to_dict(),
        'sample_parsed': parsed[:10],
        'sample_skipped': skipped[:10]
    }

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"✅ Souhrn uložen: {OUTPUT_JSON}")

    print("\n" + "=" * 80)
    print("UKÁZKA PARSOVANÝCH KÓDŮ (prvních 20):")
    print("=" * 80)
    print(df_parsed[['raw_code', 'material', 'shape', 'diameter', 'width', 'thickness', 'state']].head(20).to_string(index=False))

    print("\n" + "=" * 80)
    print("UKÁZKA PŘESKOČENÝCH KÓDŮ (prvních 20):")
    print("=" * 80)
    for i, code in enumerate(skipped[:20], 1):
        print(f"{i:2d}. {code}")


if __name__ == "__main__":
    analyze_catalog()
