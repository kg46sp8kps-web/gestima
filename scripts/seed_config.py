"""
GESTIMA - Seed system configuration (ADR-016)
Naplní SystemConfig tabulku koeficienty pro kalkulace
"""

import asyncio
import sys
from pathlib import Path

# Přidat root do path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import async_session
from app.models.config import SystemConfig


# Výchozí koeficienty (všechny jako multiplikátory >= 1.0)
CONFIG_DEFAULTS = [
    {
        "key": "overhead_coefficient",
        "value_float": 1.20,
        "description": "Administrativní režie (1.20 = +20% na náklady strojů)",
        "created_by": "system_seed"
    },
    {
        "key": "margin_coefficient",
        "value_float": 1.25,
        "description": "Marže na práci (1.25 = +25%)",
        "created_by": "system_seed"
    },
    {
        "key": "stock_coefficient",
        "value_float": 1.15,
        "description": "Skladový koeficient na materiál (1.15 = +15%)",
        "created_by": "system_seed"
    },
    {
        "key": "coop_coefficient",
        "value_float": 1.10,
        "description": "Kooperační koeficient (1.10 = +10%)",
        "created_by": "system_seed"
    }
]


async def seed_config():
    """Naplnění SystemConfig tabulky"""
    async with async_session() as session:
        created = 0
        updated = 0

        for config_data in CONFIG_DEFAULTS:
            # Kontrola existence podle klíče
            from sqlalchemy import select
            result = await session.execute(
                select(SystemConfig).where(SystemConfig.key == config_data["key"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Aktualizovat hodnotu (pokud se liší)
                if existing.value_float != config_data["value_float"]:
                    existing.value_float = config_data["value_float"]
                    existing.description = config_data["description"]
                    updated += 1
                    print(f"🔄 {config_data['key']} - aktualizováno na {config_data['value_float']}")
                else:
                    print(f"⏭️  {config_data['key']} - již existuje")
                continue

            # Vytvoření nového config záznamu
            config = SystemConfig(**config_data)
            session.add(config)
            created += 1
            print(f"✅ {config_data['key']} = {config_data['value_float']} - vytvořeno")

        # Commit
        await session.commit()

        print(f"\n📊 Seed system config dokončen:")
        print(f"   ✅ Vytvořeno: {created}")
        print(f"   🔄 Aktualizováno: {updated}")
        print(f"   📦 Celkem konfiguračních položek: {len(CONFIG_DEFAULTS)}")


if __name__ == "__main__":
    print("🚀 Seed system config do GESTIMA databáze\n")
    asyncio.run(seed_config())
