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

    # Skip system codes, vypaleky, "nab" materiály
    if code_str.startswith('000-') or 'vypalek' in code_str.lower():
        # Exception: 000-nab-mat-[PLASTIC] are valid plastic codes
        if not any(p in code_str for p in ['Pa6', 'POM', 'ABS']):
            return None

    # Skip materiály s "nab" v kódu (user request 2026-01-27)
    if 'nab' in code_str.lower():
        # Exception: 000-nab-mat-[PLASTIC] are valid
        if not any(p in code_str for p in ['Pa6', 'POM', 'ABS']):
            return None

    # Try plastic formats first
    plastic_result = parse_plastic_code(code_str)
    if plastic_result:
        return plastic_result

    # Try cast iron (litina) - formats: GG250-KR050.000-L, GGG40-KR150.000-L
    cast_iron_result = parse_cast_iron(code_str)
    if cast_iron_result:
        return cast_iron_result

    # Strip surface treatment suffixes (user request 2026-01-27: "-Kl" = klínové, parse as normal bars)
    # Examples: HR018x011-T-Kl → HR018x011-T, TR006x002-T-Zn → TR006x002-T
    code_normalized = code_str
    for suffix in ['-Kl', '-Zn', '-Vs']:
        if code_normalized.endswith(suffix):
            code_normalized = code_normalized[:-len(suffix)]
            break

    # Try bars with length (tyče s délkou): HR015x001.5-B-/500
    # Format: [MATERIAL]-HR[WIDTH]x[THICKNESS]-[STATE]-/[LENGTH]
    bar_with_length_pattern = r'^([1-3]\.\d{4})-HR(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)-([A-Z]+)-/(\d+)$'
    bar_with_length_match = re.match(bar_with_length_pattern, code_normalized)

    if bar_with_length_match:
        material, width, thickness, state, length = bar_with_length_match.groups()
        width = float(width)
        thickness = float(thickness)

        bar_shape = 'SQUARE_BAR' if width == thickness else 'FLAT_BAR'

        return {
            'raw_code': code_str,
            'material': material,
            'material_type': 'metal',
            'shape_code': f'HR-/{length}',
            'dimensions_raw': f'{width}x{thickness}-{length}',
            'state': state,
            'shape': bar_shape,
            'diameter': None,
            'width': width,
            'thickness': thickness,
            'wall_thickness': None,
            'length': float(length)
        }

    # Try cut bars (přířezy): KR140.000-015-O
    # Format: [MATERIAL]-KR[DIAMETER].000-[LENGTH]-[STATE]
    cut_bar_pattern = r'^([1-3]\.\d{4})-KR(\d+)\.000-(\d+)-([A-Z]+)$'
    cut_bar_match = re.match(cut_bar_pattern, code_normalized)

    if cut_bar_match:
        material, diameter, length, state = cut_bar_match.groups()

        return {
            'raw_code': code_str,
            'material': material,
            'material_type': 'metal',
            'shape_code': f'KR-CUT',
            'dimensions_raw': f'{diameter}-{length}',
            'state': state,
            'shape': 'ROUND_BAR',
            'diameter': float(diameter),
            'width': None,
            'thickness': None,
            'wall_thickness': None,
            'length': float(length)
        }

    # Pattern: [MATERIAL]-[SHAPE][DIMENSIONS]-[STATE]
    # Examples:
    #   1.4404-KR240.000-O
    #   1.0036-HR010x005-T
    #   1.0039-TR010x002-T

    # Try 3D blocks (steel) first: [MATERIAL]-HR[TTT]-[WWW]-[LLL]-BLOK[-STATE]
    # Examples: 1.0036-HR080-220-275-BLOK, 1.2311-HR000x000-BLOK-T33
    block_pattern = r'^([1-3]\.\d{4})-HR(\d{3})-(\d{3})-(\d{3})-BLOK(?:-([A-Z0-9]+))?$'
    block_match = re.match(block_pattern, code_normalized)

    if block_match:
        material, thickness, width, length, state = block_match.groups()
        state = state or 'BLOK'  # Default state if not provided

        # Skip zero dimensions
        if float(thickness) == 0 or float(width) == 0 or float(length) == 0:
            return None

        return {
            'raw_code': code_str,  # Original code
            'material': material,
            'material_type': 'metal',
            'shape_code': 'HR-BLOK',
            'dimensions_raw': f'{thickness}-{width}-{length}',
            'state': state,
            'shape': 'BLOCK',  # New shape type
            'diameter': None,
            'width': float(width),
            'thickness': float(thickness),
            'wall_thickness': None,
            'length': float(length)
        }

    # Try 3D plates/blocks (aluminum + steel): [MATERIAL]-DE[TTT]-[WWW]-[LLL]-[STATE]
    # Examples: 3.3547-DE012-082-102-F (hliník frézovaný), 3.3547-DE010-177-302-F
    plate_3d_pattern = r'^([1-3]\.\d{4})-DE(\d{3})-(\d{3})-(\d{3})-([A-Z]+)$'
    plate_3d_match = re.match(plate_3d_pattern, code_normalized)

    if plate_3d_match:
        material, thickness, width, length, state = plate_3d_match.groups()

        # Skip aluminum with EP surface (user request: F, L, V = OK; EP = skip)
        if material.startswith('3.') and state == 'EP':
            return None

        return {
            'raw_code': code_str,
            'material': material,
            'material_type': 'metal',
            'shape_code': 'DE-3D',
            'dimensions_raw': f'{thickness}-{width}-{length}',
            'state': state,
            'shape': 'BLOCK',  # 3D block/plate
            'diameter': None,
            'width': float(width),
            'thickness': float(thickness),
            'wall_thickness': None,
            'length': float(length)
        }

    # Try 2D strips/bands (aluminum): [MATERIAL]-DE[TTT]-[WWW]-[STATE]
    # Examples: 3.3547-DE012-066-L (hliník litý, tloušťka 12mm, šířka 66mm)
    strip_pattern = r'^([1-3]\.\d{4})-DE(\d{3})-(\d{3})-([A-Z]+)$'
    strip_match = re.match(strip_pattern, code_normalized)

    if strip_match:
        material, thickness, width, state = strip_match.groups()

        # Skip aluminum with EP surface
        if material.startswith('3.') and state == 'EP':
            return None

        return {
            'raw_code': code_str,
            'material': material,
            'material_type': 'metal',
            'shape_code': 'DE-2D',
            'dimensions_raw': f'{thickness}-{width}',
            'state': state,
            'shape': 'FLAT_BAR',  # 2D strip = flat bar without specified length
            'diameter': None,
            'width': float(width),
            'thickness': float(thickness),
            'wall_thickness': None,
            'length': None
        }

    # Try standard metal format: [MATERIAL]-[SHAPE][DIMENSIONS]-[STATE]
    pattern = r'^([1-3]\.\d{4})(?:\+\w+)?-([A-Z]{2})([0-9x.]+)-([A-Z]+)$'
    match = re.match(pattern, code_normalized)

    if not match:
        return None

    material, shape, dimensions, state = match.groups()

    # Parse dimensions based on shape
    parsed_dims = parse_dimensions(shape, dimensions)

    if not parsed_dims:
        return None

    # Skip zero dimensions (user request 2026-01-27)
    # HR000x000, DE000-000, etc.
    if parsed_dims.get('diameter') == 0:
        return None
    if parsed_dims.get('width') == 0 and parsed_dims.get('thickness') == 0:
        return None
    if parsed_dims.get('thickness') == 0 and shape == 'DE':
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
      POM-C-DE016-014-L-B (plastic strip: thickness × width)
      PA6-KR080.000-P-B (plastic rod: diameter)
      PA6-DE010-000-P-B (plastic plate: thickness only)
      PE500-DE012-190-303-B (plastic block: thickness × width × length)
    """
    code_upper = code.upper()

    # Plastic materials (expanded list)
    plastic_types = r'(POM-C|POM|PA6G?|PA66|PE\d+|ABS|PC|PEEK\d*|MAPA)'

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
            'wall_thickness': None,
            'length': None
        }

    # Format 2: Plastic rods - [PLASTIC]-KR[DIAMETER].000-[STATE]-[COLOR]
    # Examples: PA6-KR080.000-P-B, PE1000-KR025.000-L-N
    # Color codes: B (black), N (natural/natur), G/GR (gray)
    plastic_rod_pattern = r'^' + plastic_types + r'(?:-GF\d+|-LFX)?-KR(\d+)\.000[.\-]([A-Z]+)-([BNGR]+)$'
    plastic_rod_match = re.match(plastic_rod_pattern, code_upper)

    if plastic_rod_match:
        plastic, diameter, state, color = plastic_rod_match.groups()

        return {
            'raw_code': code,
            'material': plastic,
            'material_type': 'plastic',
            'shape_code': 'KR',
            'dimensions_raw': f'{diameter}.000',
            'state': f'{state}-{color}',
            'shape': 'ROUND_BAR',
            'diameter': float(diameter),
            'width': None,
            'thickness': None,
            'wall_thickness': None,
            'length': None
        }

    # Format 3: Plastic 3D blocks - [PLASTIC]-DE[TTT]-[WWW]-[LLL]-[COLOR]
    # Examples: PE500-DE012-190-303-B (12×190×303mm)
    plastic_block_3d_pattern = r'^' + plastic_types + r'-DE(\d{3})-(\d{3})-(\d{3})-([BNGR]+)$'
    plastic_block_3d_match = re.match(plastic_block_3d_pattern, code_upper)

    if plastic_block_3d_match:
        plastic, thickness, width, length, color = plastic_block_3d_match.groups()

        # Skip zero dimensions
        if float(thickness) == 0 or float(width) == 0 or float(length) == 0:
            return None

        return {
            'raw_code': code,
            'material': plastic,
            'material_type': 'plastic',
            'shape_code': 'DE-3D',
            'dimensions_raw': f'{thickness}-{width}-{length}',
            'state': f'L-{color}',  # Assume cast for blocks
            'shape': 'BLOCK',
            'diameter': None,
            'width': float(width),
            'thickness': float(thickness),
            'wall_thickness': None,
            'length': float(length)
        }

    # Format 4: Plastic 2D blocks/plates - [PLASTIC]-DE[TTT]x[WWW]-[STATE]-[COLOR]
    # Examples: PEEK1000-DE030x220-L-N (30×220mm)
    plastic_block_2d_pattern = r'^' + plastic_types + r'-DE(\d{3})x(\d{3})-([A-Z]+)-([BNGR]+)$'
    plastic_block_2d_match = re.match(plastic_block_2d_pattern, code_upper)

    if plastic_block_2d_match:
        plastic, thickness, width, state, color = plastic_block_2d_match.groups()

        return {
            'raw_code': code,
            'material': plastic,
            'material_type': 'plastic',
            'shape_code': 'DE-2D',
            'dimensions_raw': f'{thickness}x{width}',
            'state': f'{state}-{color}',
            'shape': 'FLAT_BAR',
            'diameter': None,
            'width': float(width),
            'thickness': float(thickness),
            'wall_thickness': None,
            'length': None
        }

    # Format 5: Plastic strips - [PLASTIC]-DE[TTT]-[WWW]-[STATE]-[COLOR]
    # Examples: POM-C-DE016-014-L-B
    # Color codes: B (black/černý), N (natural/natur), G (gray/šedý)
    plastic_strip_pattern = r'^' + plastic_types + r'-DE(\d{3})-(\d{3})-([A-Z]+)-([BNGR]+)$'
    plastic_strip_match = re.match(plastic_strip_pattern, code_upper)

    if plastic_strip_match:
        plastic, thickness, width, state, color = plastic_strip_match.groups()

        # Skip zero dimensions
        if float(thickness) == 0 or float(width) == 0:
            return None

        return {
            'raw_code': code,
            'material': plastic,
            'material_type': 'plastic',
            'shape_code': 'DE-2D',
            'dimensions_raw': f'{thickness}-{width}',
            'state': f'{state}-{color}',  # L-B = litý, černý
            'shape': 'FLAT_BAR',  # Strip = flat bar (thickness × width)
            'diameter': None,
            'width': float(width),
            'thickness': float(thickness),
            'wall_thickness': None,
            'length': None
        }

    # Format 6: Plastic plates (thickness only) - [PLASTIC]-DE[TTT]-000-[STATE]-[COLOR]
    # Examples: PA6-DE010-000-P-B (10mm thick plate, no width specified)
    plastic_plate_pattern = r'^' + plastic_types + r'-DE(\d{3})-000-([A-Z]+)-([BNGR]+)$'
    plastic_plate_match = re.match(plastic_plate_pattern, code_upper)

    if plastic_plate_match:
        plastic, thickness, state, color = plastic_plate_match.groups()

        # Skip zero thickness
        if float(thickness) == 0:
            return None

        return {
            'raw_code': code,
            'material': plastic,
            'material_type': 'plastic',
            'shape_code': 'DE',
            'dimensions_raw': f'{thickness}',
            'state': f'{state}-{color}',
            'shape': 'PLATE',  # Plate with only thickness specified
            'diameter': None,
            'width': None,
            'thickness': float(thickness),
            'wall_thickness': None,
            'length': None
        }

    # Format 7: Plastic plates without color - [PLASTIC]-DE[TTT]-000-[STATE]
    # Examples: PC-DE005-000-L, PEEK1000-DE015-000-L-N
    plastic_plate_simple_pattern = r'^' + plastic_types + r'-DE(\d{3})-000-([A-Z]+)$'
    plastic_plate_simple_match = re.match(plastic_plate_simple_pattern, code_upper)

    if plastic_plate_simple_match:
        plastic, thickness, state = plastic_plate_simple_match.groups()

        # Skip zero thickness
        if float(thickness) == 0:
            return None

        return {
            'raw_code': code,
            'material': plastic,
            'material_type': 'plastic',
            'shape_code': 'DE',
            'dimensions_raw': f'{thickness}',
            'state': state,
            'shape': 'PLATE',
            'diameter': None,
            'width': None,
            'thickness': float(thickness),
            'wall_thickness': None,
            'length': None
        }

    # Format 8: PA66-GF30-DE012-000-P-B (older format)
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


def parse_cast_iron(code: str) -> Optional[Dict]:
    """
    Parse cast iron (litina) codes.

    Formats:
        GG250-KR050.000-L (gray cast iron, Ø50mm, cast state)
        GGG40-KR150.000-L (ductile cast iron, Ø150mm, cast state)

    Returns:
        dict with parsed properties or None
    """
    # Pattern: [GRADE]-KR[DIAMETER].000-[STATE]
    pattern = r'^(GG250|GGG40|GG\d+|GGG\d+)-KR(\d+)\.000-([A-Z]+)$'
    match = re.match(pattern, code)

    if not match:
        return None

    grade, diameter, state = match.groups()

    return {
        'raw_code': code,
        'material': grade,
        'material_type': 'cast_iron',
        'shape_code': 'KR',
        'dimensions_raw': f'{diameter}.000',
        'state': state,
        'shape': 'ROUND_BAR',
        'diameter': float(diameter),
        'width': None,
        'thickness': None,
        'wall_thickness': None,
        'length': None
    }


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
        # Format: XXX.000 → tečka je jen formát, celé číslo = mm
        # KR004.000 = 4mm, KR240.000 = 240mm (user correction 2026-01-27)
        match = re.match(r'(\d+)\.(\d+)', dimensions)
        if match:
            major, minor = match.groups()
            diameter = float(major)  # 004 → 4mm, 240 → 240mm
            return {
                'shape': 'ROUND_BAR',
                'diameter': diameter,
                'width': None,
                'thickness': None,
                'wall_thickness': None,
                'length': None
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
                'wall_thickness': None,
                'length': None
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
                'wall_thickness': float(wall),
                'length': None
            }

    elif shape == 'OK':
        # Šestihran (HEXAGONAL_BAR) - user correction
        # Format: OK017.000 = SW 17mm (user correction 2026-01-27)
        match = re.match(r'(\d+)\.(\d+)', dimensions)
        if match:
            major, _ = match.groups()
            diameter = float(major)  # 017 → 17mm
            return {
                'shape': 'HEXAGONAL_BAR',
                'diameter': diameter,
                'width': None,
                'thickness': None,
                'wall_thickness': None,
                'length': None
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
                'wall_thickness': None,
                'length': None
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
