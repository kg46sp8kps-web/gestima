"""
GESTIMA - Seed materiálů do databáze
Naplní databázi základními materiálovými skupinami s cenami
"""

import asyncio
import sys
from pathlib import Path

# Přidat root do path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import async_session
from app.models.material import MaterialGroup


# Materiály podle tabulky od Ladislava
MATERIALS = [
    {
        "code": "automatova_ocel",
        "name": "Automatová ocel",
        "density": 7.85,
        "price_per_kg": 49.4,
        "color": "#42A5F5",
        "notes": "11SMn30, 11SMnPb30 - snadné obrábění"
    },
    {
        "code": "konstrukcni_ocel",
        "name": "Konstrukční ocel - plochá tyč",
        "density": 7.85,
        "price_per_kg": 40.9,
        "color": "#2196F3",
        "notes": "S235, S355 - plochá tyč"
    },
    {
        "code": "konstrukcni_ocel_desky",
        "name": "Konstrukční ocel - desky/bloky",
        "density": 7.85,
        "price_per_kg": 30,
        "color": "#1E88E5",
        "notes": "S235, S355 - desky a bloky"
    },
    {
        "code": "konstrukcni_ocel_trubka",
        "name": "Konstrukční ocel - trubka",
        "density": 7.85,
        "price_per_kg": 28.3,
        "color": "#1976D2",
        "notes": "Bezešvé trubky"
    },
    {
        "code": "nerez_kruhova",
        "name": "Nerez - kruhová tyč",
        "density": 7.90,
        "price_per_kg": 104.6,
        "color": "#FFD54F",
        "notes": "1.4301, 1.4307 - kruhová tyč"
    },
    {
        "code": "nerez_plocha",
        "name": "Nerez - plochá tyč",
        "density": 7.90,
        "price_per_kg": 168,
        "color": "#FFC107",
        "notes": "1.4301, 1.4307 - plochá tyč"
    },
    {
        "code": "hlinik_desky",
        "name": "Hliník - desky a bloky",
        "density": 2.70,
        "price_per_kg": 108,
        "color": "#66BB6A",
        "notes": "AlMgSi - desky a bloky"
    },
    {
        "code": "hlinik_kruhova",
        "name": "Hliník - kruhová tyč",
        "density": 2.70,
        "price_per_kg": 150.5,
        "color": "#4CAF50",
        "notes": "AlMgSi - kruhová tyč"
    },
    {
        "code": "hlinik_plocha",
        "name": "Hliník - plochá tyč",
        "density": 2.70,
        "price_per_kg": 146.8,
        "color": "#43A047",
        "notes": "AlMgSi - plochá tyč"
    },
    {
        "code": "plasty_desky",
        "name": "Plasty (POM/PA6) - desky",
        "density": 1.40,
        "price_per_kg": 336.9,
        "color": "#81C784",
        "notes": "POM, PA6 - desky"
    },
    {
        "code": "plasty_kruhova",
        "name": "Plasty (POM/PA6) - kruhová tyč",
        "density": 1.40,
        "price_per_kg": 177.4,
        "color": "#66BB6A",
        "notes": "POM, PA6 - kruhová tyč"
    },
    {
        "code": "ocel_nastrojova_kruhova",
        "name": "Ocel nástrojová - kruhová tyč",
        "density": 7.85,
        "price_per_kg": 95,
        "color": "#1565C0",
        "notes": "19 552, 19 830 - kalitelná"
    },
    {
        "code": "nerez_austeniticka_trubka",
        "name": "Nerez austenitická - trubka",
        "density": 7.90,
        "price_per_kg": 290,
        "color": "#FFA726",
        "notes": "1.4301, 1.4307 - bezešvé trubky"
    },
    {
        "code": "ocel_nastrojova_plocha",
        "name": "Ocel nástrojová - plochá tyč",
        "density": 7.85,
        "price_per_kg": 90,
        "color": "#0D47A1",
        "notes": "19 552, 19 830 - plochá tyč"
    },
    {
        "code": "hlinik_plocha_135",
        "name": "Hliník - plochá tyč (premium)",
        "density": 2.70,
        "price_per_kg": 135,
        "color": "#388E3C",
        "notes": "AlMgSi - plochá tyč (nákup 100+ kg)"
    },
]


async def seed_materials():
    """Naplní databázi materiály"""
    async with async_session() as session:
        # Zkontrolovat jestli už nejsou materiály v DB
        from sqlalchemy import select
        result = await session.execute(select(MaterialGroup))
        existing = result.scalars().all()
        
        if existing:
            print(f"⚠️  Databáze už obsahuje {len(existing)} materiálů")
            print("Chceš je přepsat? (y/n): ", end="")
            response = input().strip().lower()
            if response != 'y':
                print("❌ Seed zrušen")
                return
            
            # Smazat existující
            for mat in existing:
                await session.delete(mat)
            await session.commit()
            print("🗑️  Existující materiály smazány")
        
        # Přidat nové materiály
        for mat_data in MATERIALS:
            material = MaterialGroup(**mat_data)
            session.add(material)
        
        await session.commit()
        print(f"✅ Přidáno {len(MATERIALS)} materiálů do databáze")
        
        # Zobrazit přehled
        print("\n📊 Přehled materiálů:")
        print("-" * 80)
        for mat in MATERIALS:
            print(f"  {mat['code']:35} {mat['price_per_kg']:6.1f} Kč/kg  ({mat['name']})")
        print("-" * 80)


if __name__ == "__main__":
    print("🌱 GESTIMA - Seed materiálů")
    print("=" * 80)
    asyncio.run(seed_materials())
    print("\n✅ Hotovo!")
