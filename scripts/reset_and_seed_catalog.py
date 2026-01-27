#!/usr/bin/env python3
"""
GESTIMA - Reset a seed material catalog

Smaže staré MaterialGroups, Categories a Tiers a vytvoří nové podle importní struktury.

Usage:
    python scripts/reset_and_seed_catalog.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import async_session


async def reset_and_seed():
    """Reset material catalog and seed new structure"""

    print("=" * 80)
    print("GESTIMA - Material Catalog Reset & Seed")
    print("=" * 80)
    print()
    print("⚠️  VAROVÁNÍ: Toto smaže všechny MaterialGroups, Categories a Tiers!")
    print()

    # Ask for confirmation
    response = input("Opravdu chceš pokračovat? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("\nZrušeno.")
        return

    print()

    # === STEP 1: Delete existing data ===
    print("[1/4] Mazání existujících dat...")

    async with async_session() as db:
        # Delete in correct order (FK constraints)
        await db.execute(text("DELETE FROM material_price_tiers WHERE 1=1"))
        await db.execute(text("DELETE FROM material_price_categories WHERE 1=1"))
        await db.execute(text("DELETE FROM material_groups WHERE 1=1"))
        await db.commit()

    print("  ✅ Smazáno")
    print()

    # === STEP 2: Seed new structure ===
    print("[2/4] Spouštím seed_material_catalog.py...")
    print()

    # Import and run seed script
    from scripts.seed_material_catalog import seed_catalog
    await seed_catalog()

    print()

    # === STEP 3: Generate material norms SQL ===
    print("[3/4] Generuji material_norms_seed.sql...")

    import subprocess
    result = subprocess.run(
        [sys.executable, "scripts/generate_material_norms.py"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("  ✅ Material norms SQL vygenerován")
    else:
        print(f"  ⚠️  Chyba při generování: {result.stderr}")

    print()

    # === STEP 4: Import material norms ===
    print("[4/4] Importuji material norms do DB...")

    norms_sql_path = Path("temp/material_norms_seed.sql")

    if norms_sql_path.exists():
        async with async_session() as db:
            with open(norms_sql_path, 'r', encoding='utf-8') as f:
                sql = f.read()
                # Execute SQL (split by semicolon if multiple statements)
                for statement in sql.split(';'):
                    if statement.strip():
                        await db.execute(text(statement))
            await db.commit()
        print("  ✅ Material norms importovány (83 záznamů)")
    else:
        print(f"  ⚠️  {norms_sql_path} nenalezen, přeskakuji")

    print()

    # === SUMMARY ===
    print("=" * 80)
    print("✅ HOTOVO!")
    print("=" * 80)
    print()

    # Count results
    async with async_session() as db:
        result = await db.execute(text("SELECT COUNT(*) FROM material_groups WHERE deleted_at IS NULL"))
        groups_count = result.scalar()

        result = await db.execute(text("SELECT COUNT(*) FROM material_price_categories WHERE deleted_at IS NULL"))
        categories_count = result.scalar()

        result = await db.execute(text("SELECT COUNT(*) FROM material_price_tiers WHERE deleted_at IS NULL"))
        tiers_count = result.scalar()

        result = await db.execute(text("SELECT COUNT(*) FROM material_norms WHERE deleted_at IS NULL"))
        norms_count = result.scalar()

    print("Nová struktura:")
    print(f"  - {groups_count} MaterialGroups (OCEL-KONS, OCEL-AUTO, NEREZ, HLINIK, ...)")
    print(f"  - {categories_count} MaterialPriceCategories (detailní kombinace materiál+tvar)")
    print(f"  - {tiers_count} MaterialPriceTiers (~3 tiers na kategorii)")
    print(f"  - {norms_count} MaterialNorms (W.Nr. s kompletními normami)")
    print()
    print("💡 Zkontroluj v admin UI: http://localhost:8000/admin/material-catalog")
    print()


if __name__ == "__main__":
    asyncio.run(reset_and_seed())
