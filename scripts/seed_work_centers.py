"""
GESTIMA - Seed pracovišť do databáze (ADR-021)

Naplní databázi základními pracovišti (fyzickými stroji + virtuálními stanicemi).
Sequential numbering: 80XXXXXX
"""

import asyncio
import sys
from pathlib import Path

# Přidat root do path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import async_session
from app.models.work_center import WorkCenter
from app.models.enums import WorkCenterType


# Pracoviště dle ADR-021 (fyzické stroje + virtuální stanice)
WORK_CENTERS = [
    # === CNC Soustruhy ===
    {
        "work_center_number": "80000001",
        "name": "MASTURN 32",
        "work_center_type": WorkCenterType.CNC_LATHE,
        "hourly_rate_amortization": 400.0,
        "hourly_rate_labor": 300.0,
        "hourly_rate_tools": 150.0,
        "hourly_rate_overhead": 150.0,
        "max_workpiece_diameter": 32.0,
        "max_workpiece_length": 200.0,
        "priority": 10,
        "is_active": True,
        "notes": "CNC soustruh pro malé díly",
        "created_by": "system_seed"
    },
    {
        "work_center_number": "80000002",
        "name": "SMARTURN 160",
        "work_center_type": WorkCenterType.CNC_LATHE,
        "hourly_rate_amortization": 450.0,
        "hourly_rate_labor": 300.0,
        "hourly_rate_tools": 180.0,
        "hourly_rate_overhead": 170.0,
        "max_workpiece_diameter": 160.0,
        "max_workpiece_length": 400.0,
        "priority": 11,
        "is_active": True,
        "notes": "CNC soustruh pro střední díly",
        "created_by": "system_seed"
    },
    {
        "work_center_number": "80000003",
        "name": "NLX 2000",
        "work_center_type": WorkCenterType.CNC_LATHE,
        "hourly_rate_amortization": 550.0,
        "hourly_rate_labor": 350.0,
        "hourly_rate_tools": 200.0,
        "hourly_rate_overhead": 200.0,
        "max_workpiece_diameter": 200.0,
        "max_workpiece_length": 500.0,
        "axes": 5,
        "priority": 12,
        "is_active": True,
        "notes": "DMG MORI 5-osý soustružnický centrum",
        "created_by": "system_seed"
    },
    {
        "work_center_number": "80000004",
        "name": "NZX 2000",
        "work_center_type": WorkCenterType.CNC_LATHE,
        "hourly_rate_amortization": 600.0,
        "hourly_rate_labor": 350.0,
        "hourly_rate_tools": 220.0,
        "hourly_rate_overhead": 230.0,
        "max_workpiece_diameter": 200.0,
        "max_workpiece_length": 600.0,
        "axes": 5,
        "priority": 13,
        "is_active": True,
        "notes": "DMG MORI s Y-osou a protivřetenem",
        "created_by": "system_seed"
    },

    # === CNC Frézky ===
    {
        "work_center_number": "80000005",
        "name": "FV20 (klasická fréza)",
        "work_center_type": WorkCenterType.CNC_MILL_3AX,
        "hourly_rate_amortization": 300.0,
        "hourly_rate_labor": 280.0,
        "hourly_rate_tools": 120.0,
        "hourly_rate_overhead": 100.0,
        "axes": 3,
        "priority": 20,
        "is_active": True,
        "notes": "Klasická 3-osá fréza",
        "created_by": "system_seed"
    },
    {
        "work_center_number": "80000006",
        "name": "MCV 750",
        "work_center_type": WorkCenterType.CNC_MILL_3AX,
        "hourly_rate_amortization": 400.0,
        "hourly_rate_labor": 300.0,
        "hourly_rate_tools": 150.0,
        "hourly_rate_overhead": 150.0,
        "max_workpiece_length": 750.0,
        "axes": 3,
        "priority": 21,
        "is_active": True,
        "notes": "Vertikální centrum 3-axis",
        "created_by": "system_seed"
    },
    {
        "work_center_number": "80000007",
        "name": "TAJMAC H40",
        "work_center_type": WorkCenterType.CNC_MILL_4AX,
        "hourly_rate_amortization": 500.0,
        "hourly_rate_labor": 350.0,
        "hourly_rate_tools": 200.0,
        "hourly_rate_overhead": 200.0,
        "axes": 4,
        "priority": 22,
        "is_active": True,
        "notes": "4-osé horizontální centrum",
        "created_by": "system_seed"
    },
    {
        "work_center_number": "80000008",
        "name": "MILLTAP 700 + WH3",
        "work_center_type": WorkCenterType.CNC_MILL_3AX,
        "hourly_rate_amortization": 450.0,
        "hourly_rate_labor": 300.0,
        "hourly_rate_tools": 180.0,
        "hourly_rate_overhead": 170.0,
        "max_workpiece_length": 700.0,
        "axes": 3,
        "priority": 23,
        "is_active": True,
        "notes": "DMG s robotickým podavačem WH3",
        "created_by": "system_seed"
    },
    {
        "work_center_number": "80000009",
        "name": "MILLTAP 700 5AX + WH3",
        "work_center_type": WorkCenterType.CNC_MILL_5AX,
        "hourly_rate_amortization": 600.0,
        "hourly_rate_labor": 380.0,
        "hourly_rate_tools": 250.0,
        "hourly_rate_overhead": 270.0,
        "max_workpiece_length": 700.0,
        "axes": 5,
        "priority": 24,
        "is_active": True,
        "notes": "5-osá frézka s robotem WH3",
        "created_by": "system_seed"
    },
    {
        "work_center_number": "80000010",
        "name": "MILLTAP 700 5AX",
        "work_center_type": WorkCenterType.CNC_MILL_5AX,
        "hourly_rate_amortization": 550.0,
        "hourly_rate_labor": 380.0,
        "hourly_rate_tools": 230.0,
        "hourly_rate_overhead": 240.0,
        "max_workpiece_length": 700.0,
        "axes": 5,
        "priority": 25,
        "is_active": True,
        "notes": "5-osá frézka (manuální nakládání)",
        "created_by": "system_seed"
    },

    # === Pily ===
    {
        "work_center_number": "80000011",
        "name": "BOMAR STG240A",
        "work_center_type": WorkCenterType.SAW,
        "hourly_rate_amortization": 150.0,
        "hourly_rate_labor": 250.0,
        "hourly_rate_tools": 80.0,
        "hourly_rate_overhead": 70.0,
        "max_workpiece_diameter": 240.0,
        "setup_base_min": 10.0,
        "priority": 30,
        "is_active": True,
        "notes": "Automatická pásová pila do průměru 240mm",
        "created_by": "system_seed"
    },
    {
        "work_center_number": "80000012",
        "name": "BOMAR STG250",
        "work_center_type": WorkCenterType.SAW,
        "hourly_rate_amortization": 160.0,
        "hourly_rate_labor": 250.0,
        "hourly_rate_tools": 85.0,
        "hourly_rate_overhead": 75.0,
        "max_workpiece_diameter": 250.0,
        "setup_base_min": 10.0,
        "priority": 31,
        "is_active": True,
        "notes": "Pásová pila do průměru 250mm",
        "created_by": "system_seed"
    },

    # === Ostatní (virtuální pracoviště) ===
    {
        "work_center_number": "80000013",
        "name": "KONTROLA",
        "work_center_type": WorkCenterType.QUALITY_CONTROL,
        "hourly_rate_labor": 350.0,
        "hourly_rate_overhead": 100.0,
        "setup_base_min": 0.0,
        "priority": 40,
        "is_active": True,
        "notes": "Kontrolní pracoviště (CMM, měřidla)",
        "created_by": "system_seed"
    },
    {
        "work_center_number": "80000014",
        "name": "VS20 (vrtačka)",
        "work_center_type": WorkCenterType.DRILL,
        "hourly_rate_amortization": 80.0,
        "hourly_rate_labor": 250.0,
        "hourly_rate_tools": 50.0,
        "hourly_rate_overhead": 50.0,
        "priority": 35,
        "is_active": True,
        "notes": "Sloupová vrtačka",
        "created_by": "system_seed"
    },
    {
        "work_center_number": "80000015",
        "name": "MECHANIK",
        "work_center_type": WorkCenterType.MANUAL_ASSEMBLY,
        "hourly_rate_labor": 300.0,
        "hourly_rate_overhead": 80.0,
        "priority": 50,
        "is_active": True,
        "notes": "Manuální montáž a dokončovací práce",
        "created_by": "system_seed"
    },
    {
        "work_center_number": "80000016",
        "name": "KOOPERACE",
        "work_center_type": WorkCenterType.EXTERNAL,
        "priority": 99,
        "is_active": True,
        "notes": "Externí kooperace (outsourcing)",
        "created_by": "system_seed"
    },
]


async def seed_work_centers(session=None):
    """Naplnění databáze pracovišti

    Args:
        session: Optional AsyncSession (pro testy). If None, vytvoří vlastní.

    Returns:
        int: Počet vytvořených pracovišť
    """
    # Use provided session or create own
    own_session = session is None
    if own_session:
        session = async_session()
        session = await session.__aenter__()

    try:
        created = 0
        skipped = 0

        for wc_data in WORK_CENTERS:
            # Kontrola existence podle work_center_number
            from sqlalchemy import select
            result = await session.execute(
                select(WorkCenter).where(
                    WorkCenter.work_center_number == wc_data["work_center_number"]
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                skipped += 1
                print(f"⏭️  {wc_data['work_center_number']} {wc_data['name']} - již existuje")
                continue

            # Vytvoření nového pracoviště
            work_center = WorkCenter(**wc_data)
            session.add(work_center)
            created += 1
            print(f"✅ {wc_data['work_center_number']} {wc_data['name']} - vytvořeno")

        # Commit only if we own the session
        if own_session:
            await session.commit()

        print(f"\n📊 Seed pracovišť dokončen:")
        print(f"   ✅ Vytvořeno: {created}")
        print(f"   ⏭️  Přeskočeno: {skipped}")
        print(f"   📦 Celkem: {len(WORK_CENTERS)}")

        return created
    finally:
        if own_session:
            await session.__aexit__(None, None, None)


if __name__ == "__main__":
    print("🚀 Seed pracovišť do GESTIMA databáze (ADR-021)\n")
    asyncio.run(seed_work_centers())
