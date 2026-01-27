#!/usr/bin/env python3
"""
Zobrazí VŠECHNY přeskočené položky z katalogu s kategorizací důvodů
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from collections import defaultdict

# Import parser
from analyze_material_codes import parse_material_code

EXCEL_PATH = Path(__file__).parent.parent / "data" / "materialy_export_import.xlsx"


def categorize_skipped_reason(code: str) -> str:
    """Identifikuj důvod přeskočení"""
    code_lower = code.lower()

    # Výpalky
    if 'vypalek' in code_lower:
        return "Výpalky"

    # System kódy (000-)
    if code.startswith('000-'):
        # Check if plastic exception
        if any(p in code for p in ['Pa6', 'POM', 'ABS']):
            return "VALID_PLASTIC"  # Shouldn't be skipped
        return "System kódy (000-)"

    # Materiály s "nab" (kromě plastů)
    if 'nab' in code_lower:
        if not any(p in code for p in ['Pa6', 'POM', 'ABS']):
            return "Materiály s 'nab' (nabídkové/nákupní)"

    # EP povrch (elektropolovaný hliník)
    if '-EP' in code.upper():
        return "EP povrch (hliník elektropolovaný)"

    # Nulové rozměry
    if '000x000' in code or '-000-000' in code or 'HR000x000' in code or 'DE000-000' in code:
        return "Nulové rozměry (000x000, DE000-000)"

    # Nerozpoznaný formát
    return "Nerozpoznaný formát"


def main():
    print("=" * 100)
    print("VŠECHNY PŘESKOČENÉ POLOŽKY Z KATALOGU")
    print("=" * 100)

    # Load Excel
    df = pd.read_excel(EXCEL_PATH)
    print(f"\n📊 Celkem řádků v katalogu: {len(df)}")

    # Parse all codes
    parsed = []
    skipped = []

    for code in df['Pol.']:
        result = parse_material_code(code)
        if result:
            parsed.append(code)
        else:
            skipped.append(code)

    print(f"✅ Parsovatelné: {len(parsed)}")
    print(f"⊘  Přeskočené:   {len(skipped)}")

    # Categorize skipped items
    categorized = defaultdict(list)

    for code in skipped:
        reason = categorize_skipped_reason(str(code))
        categorized[reason].append(str(code))

    # Display by category
    print("\n" + "=" * 100)
    print("PŘESKOČENÉ POLOŽKY PODLE DŮVODŮ")
    print("=" * 100)

    for reason, codes in sorted(categorized.items(), key=lambda x: -len(x[1])):
        print(f"\n📦 {reason}: {len(codes)}× položek")
        print("-" * 100)

        for i, code in enumerate(codes, 1):
            print(f"  {i:4d}. {code}")

        print()

    # Summary
    print("=" * 100)
    print("📊 SOUHRN")
    print("=" * 100)

    total_skipped = len(skipped)

    print(f"\nCelkem přeskočeno: {total_skipped} položek\n")
    print("Rozložení:")
    for reason, codes in sorted(categorized.items(), key=lambda x: -len(x[1])):
        percentage = (len(codes) / total_skipped * 100) if total_skipped > 0 else 0
        print(f"  {reason:45s}: {len(codes):4d}× ({percentage:5.1f}%)")

    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()
