#!/usr/bin/env python3
"""
Analyze existing material catalog Excel file
"""
import pandas as pd
from pathlib import Path

catalog_path = Path(__file__).parent.parent / "data/archive/materials.xlsx"

print("=" * 80)
print("ANALÝZA EXISTUJÍCÍHO KATALOGU MATERIÁLŮ")
print("=" * 80)

# Read Excel
df = pd.read_excel(catalog_path)

print(f"\nCelkem řádků: {len(df)}")
print(f"Celkem sloupců: {len(df.columns)}")

print(f"\nSloupce:")
for i, col in enumerate(df.columns, 1):
    print(f"  {i:2d}. {col}")

print(f"\nPrvních 10 řádků:")
print(df.head(10).to_string())

print(f"\nTypy dat:")
print(df.dtypes)

print(f"\nChybějící hodnoty:")
print(df.isnull().sum())

print(f"\nUnikátní hodnoty ve sloupcích:")
for col in df.columns:
    unique_count = df[col].nunique()
    print(f"  {col:30s}: {unique_count:4d} unikátních")
    if unique_count <= 20:
        print(f"    → {sorted(df[col].dropna().unique())}")
