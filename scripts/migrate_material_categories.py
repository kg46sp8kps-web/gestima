#!/usr/bin/env python3
"""
Migration: Zjednodušení MaterialGroup (13 → 6 základních typů)

Cíl:
- Redukovat MaterialGroup z 13 specifických norem na 6 základních typů materiálů
- Přidat material_group_id FK do MaterialPriceCategory
- Update všech souvisejících záznamů (MaterialNorm, MaterialItem)

PŘED:
  MaterialGroup: C45, S235, 11xxx, 42CrMo4, 16MnCr5, ... (13 záznamů)
  MaterialPriceCategory: OCEL-KRUHOVA, NEREZ-KRUHOVA, ... (13 záznamů)

PO:
  MaterialGroup: OCEL, NEREZ, HLINIK, MOSAZ, PLASTY, OCEL-NASTROJOVA (6 záznamů)
  MaterialPriceCategory: OCEL-KRUHOVA (FK→OCEL), NEREZ-KRUHOVA (FK→NEREZ), ...
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import async_session_maker, engine


# Mapping: stará MaterialGroup → nová MaterialGroup
OLD_TO_NEW_GROUP_MAPPING = {
    # Ocel konstrukční + legovaná → OCEL
    "11xxx": "OCEL",
    "C45": "OCEL",
    "S235": "OCEL",
    "42CrMo4": "OCEL",
    "16MnCr5": "OCEL",

    # Nerez → NEREZ
    "X5CrNi18-10": "NEREZ",  # 304
    "X2CrNiMo17-12-2": "NEREZ",  # 316L

    # Hliník → HLINIK
    "6060": "HLINIK",
    "7075": "HLINIK",

    # Mosaz → MOSAZ
    "CuZn37": "MOSAZ",
    "CuZn39Pb3": "MOSAZ",

    # Plasty → PLASTY
    "PA6": "PLASTY",
    "POM": "PLASTY",
}

# Nové MaterialGroup definice
NEW_MATERIAL_GROUPS = [
    {
        "code": "OCEL",
        "name": "Ocel konstrukční a legovaná",
        "density": 7.85,
        "material_type": "ocel",
    },
    {
        "code": "NEREZ",
        "name": "Nerezová ocel (austenit.)",
        "density": 7.95,
        "material_type": "nerez",
    },
    {
        "code": "HLINIK",
        "name": "Hliníkové slitiny",
        "density": 2.70,
        "material_type": "hlinik",
    },
    {
        "code": "MOSAZ",
        "name": "Mosaz a bronz",
        "density": 8.45,
        "material_type": "mosaz",
    },
    {
        "code": "PLASTY",
        "name": "Technické plasty (PA, POM)",
        "density": 1.30,
        "material_type": "plasty",
    },
    {
        "code": "OCEL-NASTROJOVA",
        "name": "Ocel nástrojová",
        "density": 7.85,
        "material_type": "ocel_nastrojova",
    },
]

# MaterialPriceCategory → MaterialGroup mapping
PRICE_CATEGORY_TO_GROUP = {
    "OCEL-KRUHOVA": "OCEL",
    "OCEL-PLOCHA": "OCEL",
    "OCEL-DESKY": "OCEL",
    "OCEL-TRUBKA": "OCEL",
    "NEREZ-KRUHOVA": "NEREZ",
    "NEREZ-PLOCHA": "NEREZ",
    "HLINIK-KRUHOVA": "HLINIK",
    "HLINIK-PLOCHA": "HLINIK",
    "HLINIK-DESKY": "HLINIK",
    "MOSAZ-BRONZ": "MOSAZ",
    "PLASTY-TYCE": "PLASTY",
    "PLASTY-DESKY": "PLASTY",
    "OCEL-NASTROJOVA": "OCEL-NASTROJOVA",
}


async def run_migration():
    """Provede migraci databáze"""

    print("=" * 60)
    print("MIGRATION: Zjednodušení MaterialGroup (13 → 6)")
    print("=" * 60)

    async with async_session_maker() as db:
        try:
            # ========== KROK 1: Backup starých MaterialGroup IDs ==========
            print("\n[1/8] Zálohování starých MaterialGroup IDs...")

            result = await db.execute(text("""
                SELECT id, code, name, density
                FROM material_groups
                WHERE deleted_at IS NULL
            """))
            old_groups = {row.code: row for row in result.fetchall()}
            print(f"✓ Nalezeno {len(old_groups)} starých MaterialGroup záznamů")

            # ========== KROK 2: Vytvořit nové MaterialGroup (6 záznamů) ==========
            print("\n[2/8] Vytváření nových MaterialGroup (6 základních typů)...")

            new_group_ids = {}
            for group_def in NEW_MATERIAL_GROUPS:
                result = await db.execute(text("""
                    INSERT INTO material_groups (code, name, density, created_at, updated_at, created_by, updated_by, version)
                    VALUES (:code, :name, :density, :now, :now, 'migration', 'migration', 1)
                    RETURNING id
                """), {
                    "code": group_def["code"],
                    "name": group_def["name"],
                    "density": group_def["density"],
                    "now": datetime.utcnow(),
                })
                new_id = result.fetchone()[0]
                new_group_ids[group_def["code"]] = new_id
                print(f"  ✓ {group_def['code']:20s} (ID={new_id}, {group_def['density']} kg/dm³)")

            # ========== KROK 3: Přidat material_group_id do MaterialPriceCategory ==========
            print("\n[3/8] Přidávání material_group_id FK do MaterialPriceCategory...")

            await db.execute(text("""
                ALTER TABLE material_price_categories
                ADD COLUMN material_group_id INTEGER REFERENCES material_groups(id)
            """))
            print("  ✓ Sloupec material_group_id přidán")

            # ========== KROK 4: Update MaterialPriceCategory s novými group IDs ==========
            print("\n[4/8] Propojování MaterialPriceCategory s novými MaterialGroup...")

            for category_code, group_code in PRICE_CATEGORY_TO_GROUP.items():
                group_id = new_group_ids[group_code]
                await db.execute(text("""
                    UPDATE material_price_categories
                    SET material_group_id = :group_id,
                        updated_at = :now,
                        updated_by = 'migration',
                        version = version + 1
                    WHERE code = :category_code
                """), {
                    "group_id": group_id,
                    "category_code": category_code,
                    "now": datetime.utcnow(),
                })
                print(f"  ✓ {category_code:20s} → {group_code}")

            # ========== KROK 5: Update MaterialNorm s novými group IDs ==========
            print("\n[5/8] Aktualizace MaterialNorm záznamů...")

            norm_count = 0
            for old_code, new_code in OLD_TO_NEW_GROUP_MAPPING.items():
                if old_code not in old_groups:
                    continue

                old_id = old_groups[old_code].id
                new_id = new_group_ids[new_code]

                result = await db.execute(text("""
                    UPDATE material_norms
                    SET material_group_id = :new_id,
                        updated_at = :now,
                        updated_by = 'migration',
                        version = version + 1
                    WHERE material_group_id = :old_id AND deleted_at IS NULL
                """), {
                    "old_id": old_id,
                    "new_id": new_id,
                    "now": datetime.utcnow(),
                })
                count = result.rowcount
                if count > 0:
                    norm_count += count
                    print(f"  ✓ {old_code:20s} → {new_code:15s} ({count} norem)")

            print(f"  ✓ Celkem aktualizováno {norm_count} MaterialNorm záznamů")

            # ========== KROK 6: Update MaterialItem s novými group IDs ==========
            print("\n[6/8] Aktualizace MaterialItem záznamů...")

            item_count = 0
            for old_code, new_code in OLD_TO_NEW_GROUP_MAPPING.items():
                if old_code not in old_groups:
                    continue

                old_id = old_groups[old_code].id
                new_id = new_group_ids[new_code]

                result = await db.execute(text("""
                    UPDATE material_items
                    SET material_group_id = :new_id,
                        updated_at = :now,
                        updated_by = 'migration',
                        version = version + 1
                    WHERE material_group_id = :old_id AND deleted_at IS NULL
                """), {
                    "old_id": old_id,
                    "new_id": new_id,
                    "now": datetime.utcnow(),
                })
                count = result.rowcount
                if count > 0:
                    item_count += count
                    print(f"  ✓ {old_code:20s} → {new_code:15s} ({count} položek)")

            print(f"  ✓ Celkem aktualizováno {item_count} MaterialItem záznamů")

            # ========== KROK 7: Soft delete starých MaterialGroup ==========
            print("\n[7/8] Soft delete starých MaterialGroup záznamů...")

            for old_code in OLD_TO_NEW_GROUP_MAPPING.keys():
                if old_code not in old_groups:
                    continue

                old_id = old_groups[old_code].id

                await db.execute(text("""
                    UPDATE material_groups
                    SET deleted_at = :now,
                        deleted_by = 'migration'
                    WHERE id = :old_id
                """), {
                    "old_id": old_id,
                    "now": datetime.utcnow(),
                })

            print(f"  ✓ Soft deleted {len(OLD_TO_NEW_GROUP_MAPPING)} starých záznamů")

            # ========== KROK 8: Commit změn ==========
            print("\n[8/8] Commitování změn...")
            await db.commit()
            print("  ✓ Všechny změny úspěšně commitnuty")

            # ========== Souhrn ==========
            print("\n" + "=" * 60)
            print("✅ MIGRACE DOKONČENA")
            print("=" * 60)
            print(f"MaterialGroup:        13 → 6 základních typů")
            print(f"MaterialPriceCategory: +material_group_id FK")
            print(f"MaterialNorm:         {norm_count} záznamů aktualizováno")
            print(f"MaterialItem:         {item_count} záznamů aktualizováno")
            print()

            # Zobrazit nové skupiny
            print("Nové MaterialGroup:")
            for code, group_id in new_group_ids.items():
                group_def = next(g for g in NEW_MATERIAL_GROUPS if g["code"] == code)
                print(f"  {code:20s} (ID={group_id:2d}, {group_def['density']:4.2f} kg/dm³)")

        except Exception as e:
            print(f"\n❌ CHYBA při migraci: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    print("⚠️  VAROVÁNÍ: Tato migrace upraví strukturu databáze!")
    print("   - Vytvoří 6 nových MaterialGroup")
    print("   - Přidá material_group_id FK do MaterialPriceCategory")
    print("   - Update všech MaterialNorm a MaterialItem záznamů")
    print("   - Soft delete 13 starých MaterialGroup záznamů")
    print()

    response = input("Pokračovat? (ano/ne): ")
    if response.lower() not in ["ano", "a", "yes", "y"]:
        print("Migrace zrušena.")
        sys.exit(0)

    asyncio.run(run_migration())
