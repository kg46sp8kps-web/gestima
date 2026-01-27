#!/usr/bin/env python3
"""
Migration: Přidání katalogových polí do MaterialItem (ADR-XXX: Supplier Catalog)

Cíl:
- Přidat weight_per_meter, standard_length, norms, supplier_code do material_items
- Umožnit import dat z dodavatelských katalogů (TheSteel.com, Ferona, ...)

PŘED:
  MaterialItem: code, name, shape, diameter, width, thickness, supplier, ...

PO:
  MaterialItem: + weight_per_meter, standard_length, norms, supplier_code
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import async_session


async def run_migration():
    """Provede migraci databáze"""

    print("=" * 80)
    print("MIGRATION: Přidání katalogových polí do MaterialItem")
    print("=" * 80)

    async with async_session() as db:
        try:
            # ========== KROK 1: Zkontrolovat zda sloupce neexistují ==========
            print("\n[1/3] Kontrola existujících sloupců...")

            result = await db.execute(text("""
                PRAGMA table_info(material_items)
            """))
            columns = {row.name for row in result.fetchall()}
            print(f"✓ Nalezeno {len(columns)} existujících sloupců")

            # Zjistit které sloupce chybí
            new_columns = {
                "weight_per_meter": "FLOAT",
                "standard_length": "FLOAT",
                "norms": "VARCHAR(200)",
                "supplier_code": "VARCHAR(50)",
            }

            missing_columns = {col: dtype for col, dtype in new_columns.items() if col not in columns}

            if not missing_columns:
                print("✓ Všechny katalogové sloupce již existují, migrace není potřeba.")
                return

            print(f"✓ Chybějící sloupce: {', '.join(missing_columns.keys())}")

            # ========== KROK 2: Přidat chybějící sloupce ==========
            print("\n[2/3] Přidávání chybějících sloupců...")

            for col_name, col_type in missing_columns.items():
                await db.execute(text(f"""
                    ALTER TABLE material_items
                    ADD COLUMN {col_name} {col_type}
                """))
                print(f"  ✓ {col_name:20s} ({col_type})")

            # ========== KROK 3: Commit změn ==========
            print("\n[3/3] Commitování změn...")
            await db.commit()
            print("  ✓ Všechny změny úspěšně commitnuty")

            # ========== Souhrn ==========
            print("\n" + "=" * 80)
            print("✅ MIGRACE DOKONČENA")
            print("=" * 80)
            print(f"Přidané sloupce: {len(missing_columns)}")
            for col_name in missing_columns.keys():
                print(f"  - {col_name}")
            print()
            print("MaterialItem nyní podporuje katalogová data:")
            print("  - weight_per_meter (kg/m) - hmotnost na metr")
            print("  - standard_length (mm) - standardní délka dodávky (6000mm)")
            print("  - norms (text) - normy (EN 10025, EN 10060, ...)")
            print("  - supplier_code (text) - kód dodavatele (T125110001)")
            print()

        except Exception as e:
            print(f"\n❌ CHYBA při migraci: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    print("⚠️  VAROVÁNÍ: Tato migrace upraví strukturu material_items tabulky!")
    print("   - Přidá 4 nové sloupce (nullable)")
    print("   - Nezmění žádná existující data")
    print("   - Umožní import katalogových dat z dodavatelů")
    print()

    response = input("Pokračovat? (ano/ne): ")
    if response.lower() not in ["ano", "a", "yes", "y"]:
        print("Migrace zrušena.")
        sys.exit(0)

    asyncio.run(run_migration())
