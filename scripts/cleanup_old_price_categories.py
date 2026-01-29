#!/usr/bin/env python3
"""
CLEANUP: Smazat staré MaterialPriceCategories bez material_group_id

Tyto kategorie byly vytvořeny starým seed_price_categories.py scriptem
a nemají material_group_id → parser je nemůže najít.

Usage:
    python scripts/cleanup_old_price_categories.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, delete
from app.database import async_session
from app.models.material import MaterialPriceCategory, MaterialPriceTier


async def cleanup():
    """Smazat staré kategorie bez material_group_id"""

    async with async_session() as db:
        print("=" * 80)
        print("CLEANUP: Staré MaterialPriceCategories (bez material_group_id)")
        print("=" * 80)
        print()

        # 1. Najít kategorie bez material_group_id
        result = await db.execute(
            select(MaterialPriceCategory)
            .where(MaterialPriceCategory.material_group_id.is_(None))
        )
        old_categories = result.scalars().all()

        if not old_categories:
            print("✅ Žádné staré kategorie nenalezeny (vše OK)")
            return

        print(f"⚠️  Nalezeno {len(old_categories)} starých kategorií BEZ material_group_id:")
        print()
        for cat in old_categories:
            print(f"  - {cat.code:30} {cat.name}")

        print()
        print("Tyto kategorie byly vytvořeny starým seed_price_categories.py")
        print("a NEMAJÍ material_group_id → parser je nemůže najít.")
        print()

        # Check for --force flag
        force = '--force' in sys.argv

        if not force:
            # Ask for confirmation
            print("Pro automatické smazání spusť: python scripts/cleanup_old_price_categories.py --force")
            confirm = input("Smazat tyto kategorie? (ano/ne): ").strip().lower()

            if confirm not in ['ano', 'a', 'yes', 'y']:
                print("❌ Zrušeno uživatelem")
                return
        else:
            print("⚡ --force flag detected, mazání bez potvrzení...")

        # 2. Smazat price tiers pro tyto kategorie
        for cat in old_categories:
            await db.execute(
                delete(MaterialPriceTier)
                .where(MaterialPriceTier.price_category_id == cat.id)
            )

        # 3. Smazat kategorie
        await db.execute(
            delete(MaterialPriceCategory)
            .where(MaterialPriceCategory.material_group_id.is_(None))
        )

        await db.commit()

        print()
        print(f"✅ Smazáno {len(old_categories)} starých kategorií")
        print()
        print("Nyní spusť: python gestima.py setup")
        print("Pro vytvoření nových kategorií s material_group_id")


if __name__ == "__main__":
    asyncio.run(cleanup())
