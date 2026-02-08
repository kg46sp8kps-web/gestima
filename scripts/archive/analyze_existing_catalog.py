#!/usr/bin/env python3
"""
Analýza existujícího katalogu materiálů (data/archive/materials.xlsx)

Cíl:
- Zjistit strukturu katalogu
- Identifikovat užitečná data
- Navrhnout import do MaterialItem
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd


def analyze_catalog():
    """Analyzuje existující katalog materiálů"""

    catalog_path = Path(__file__).parent.parent / "data" / "archive" / "materials.xlsx"

    if not catalog_path.exists():
        print(f"❌ Soubor nenalezen: {catalog_path}")
        return

    print("=" * 80)
    print(f"ANALÝZA KATALOGU: {catalog_path.name}")
    print("=" * 80)

    try:
        # Load Excel file
        excel_file = pd.ExcelFile(catalog_path)

        print(f"\n📊 Počet listů: {len(excel_file.sheet_names)}")
        print(f"Názvy listů: {excel_file.sheet_names}\n")

        # Analyze each sheet
        for sheet_name in excel_file.sheet_names:
            print("\n" + "=" * 80)
            print(f"LIST: {sheet_name}")
            print("=" * 80)

            df = pd.read_excel(catalog_path, sheet_name=sheet_name)

            print(f"\n📏 Rozměry: {len(df)} řádků × {len(df.columns)} sloupců")

            print(f"\n📋 Sloupce:")
            for i, col in enumerate(df.columns, 1):
                non_null = df[col].notna().sum()
                null_count = len(df) - non_null
                print(f"  {i:2d}. {col:30s} ({non_null} hodnot, {null_count} prázdných)")

            print(f"\n🔍 Náhled prvních 10 řádků:")
            print(df.head(10).to_string())

            print(f"\n📊 Statistiky:")

            # Numeric columns summary
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                print(f"\nČíselné sloupce:")
                for col in numeric_cols:
                    print(f"  {col}:")
                    print(f"    Min: {df[col].min()}")
                    print(f"    Max: {df[col].max()}")
                    print(f"    Mean: {df[col].mean():.2f}" if df[col].notna().any() else "    Mean: N/A")

            # Categorical columns summary
            object_cols = df.select_dtypes(include=['object']).columns
            if len(object_cols) > 0:
                print(f"\nTextové sloupce:")
                for col in object_cols[:5]:  # Limit to first 5
                    unique_count = df[col].nunique()
                    if unique_count < 20:
                        print(f"  {col}: {unique_count} unikátních hodnot")
                        print(f"    Hodnoty: {df[col].unique()[:10].tolist()}")
                    else:
                        print(f"  {col}: {unique_count} unikátních hodnot")
                        print(f"    Top 5: {df[col].value_counts().head().to_dict()}")

            # Check for material norms
            df_str = df.astype(str)
            has_en = df_str.apply(lambda x: x.str.contains(r'EN\s*\d+', case=False, na=False, regex=True)).any().any()
            has_din = df_str.apply(lambda x: x.str.contains(r'DIN\s*\d+', case=False, na=False, regex=True)).any().any()
            has_csn = df_str.apply(lambda x: x.str.contains(r'ČSN|CSN', case=False, na=False, regex=True)).any().any()

            print(f"\n🔍 Detekce norem:")
            print(f"  EN normy:  {'✓' if has_en else '✗'}")
            print(f"  DIN normy: {'✓' if has_din else '✗'}")
            print(f"  ČSN normy: {'✓' if has_csn else '✗'}")

            # Check for dimensions
            dimension_keywords = ['průměr', 'diameter', 'tloušťka', 'thickness', 'šířka', 'width', 'délka', 'length']
            found_dimensions = []
            for keyword in dimension_keywords:
                for col in df.columns:
                    if keyword.lower() in str(col).lower():
                        found_dimensions.append(col)
                        break

            if found_dimensions:
                print(f"\n📐 Rozměrové sloupce: {found_dimensions}")

        print("\n" + "=" * 80)
        print("✅ ANALÝZA DOKONČENA")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ CHYBA: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    analyze_catalog()
