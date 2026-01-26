"""
GESTIMA - Seed strojů do databáze
Naplní databázi základními stroji
"""

import asyncio
import sys
from pathlib import Path

# Přidat root do path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import async_session
from app.models.machine import MachineDB


# Základní stroje pro testování
MACHINES = [
    {
        "code": "NLX2000",
        "name": "DMG MORI NLX2000",
        "type": "lathe",
        "subtype": "horizontal",
        "max_bar_dia": 52.0,
        "max_cut_diameter": 200.0,
        "max_workpiece_dia": 200.0,
        "max_workpiece_length": 250.0,
        "min_workpiece_dia": 3.0,
        "bar_feed_max_length": 3000.0,
        "has_bar_feeder": True,
        "has_milling": True,
        "max_milling_tools": 12,
        "has_sub_spindle": True,
        "axes": 5,
        "suitable_for_series": True,
        "suitable_for_single": False,
        # Hourly rate breakdown (ADR-016): total 1200 Kč/h
        "hourly_rate_amortization": 500.0,
        "hourly_rate_labor": 300.0,
        "hourly_rate_tools": 200.0,
        "hourly_rate_overhead": 200.0,
        "setup_base_min": 30.0,
        "setup_per_tool_min": 3.0,
        "priority": 10,
        "active": True,
        "notes": "Hlavní sériový soustruh s bar feederem",
        "created_by": "system_seed"
    },
    {
        "code": "CTX450",
        "name": "DMG CTX 450",
        "type": "lathe",
        "subtype": "horizontal",
        "max_bar_dia": 65.0,
        "max_cut_diameter": 450.0,
        "max_workpiece_dia": 450.0,
        "max_workpiece_length": 600.0,
        "min_workpiece_dia": 10.0,
        "has_bar_feeder": False,
        "has_milling": True,
        "max_milling_tools": 8,
        "has_sub_spindle": False,
        "axes": 4,
        "suitable_for_series": False,
        "suitable_for_single": True,
        # Hourly rate breakdown: total 1000 Kč/h
        "hourly_rate_amortization": 400.0,
        "hourly_rate_labor": 300.0,
        "hourly_rate_tools": 150.0,
        "hourly_rate_overhead": 150.0,
        "setup_base_min": 45.0,
        "setup_per_tool_min": 5.0,
        "priority": 20,
        "active": True,
        "notes": "Univerzální soustruh pro kusovou výrobu",
        "created_by": "system_seed"
    },
    {
        "code": "DMU50",
        "name": "DMG DMU 50",
        "type": "mill",
        "subtype": "vertical",
        "max_workpiece_dia": 500.0,
        "max_workpiece_length": 450.0,
        "has_bar_feeder": False,
        "has_milling": True,
        "has_sub_spindle": False,
        "axes": 5,
        "suitable_for_series": True,
        "suitable_for_single": True,
        # Hourly rate breakdown: total 1400 Kč/h
        "hourly_rate_amortization": 600.0,
        "hourly_rate_labor": 350.0,
        "hourly_rate_tools": 250.0,
        "hourly_rate_overhead": 200.0,
        "setup_base_min": 40.0,
        "setup_per_tool_min": 4.0,
        "priority": 15,
        "active": True,
        "notes": "5-osá frézka pro složité díly",
        "created_by": "system_seed"
    },
    {
        "code": "SPRINT32",
        "name": "INDEX Sprint 32",
        "type": "lathe",
        "subtype": "horizontal",
        "max_bar_dia": 32.0,
        "max_cut_diameter": 80.0,
        "max_workpiece_dia": 80.0,
        "max_workpiece_length": 100.0,
        "min_workpiece_dia": 2.0,
        "bar_feed_max_length": 3000.0,
        "has_bar_feeder": True,
        "has_milling": True,
        "max_milling_tools": 8,
        "has_sub_spindle": True,
        "axes": 4,
        "suitable_for_series": True,
        "suitable_for_single": False,
        # Hourly rate breakdown: total 1100 Kč/h
        "hourly_rate_amortization": 450.0,
        "hourly_rate_labor": 280.0,
        "hourly_rate_tools": 200.0,
        "hourly_rate_overhead": 170.0,
        "setup_base_min": 25.0,
        "setup_per_tool_min": 2.5,
        "priority": 12,
        "active": True,
        "notes": "Rychlý soustruh pro malé díly, vysoká produktivita",
        "created_by": "system_seed"
    },
    {
        "code": "MAZAK510",
        "name": "Mazak VTC-510",
        "type": "mill",
        "subtype": "vertical",
        "max_workpiece_dia": 510.0,
        "max_workpiece_length": 510.0,
        "has_bar_feeder": False,
        "has_milling": True,
        "has_sub_spindle": False,
        "axes": 3,
        "suitable_for_series": True,
        "suitable_for_single": True,
        # Hourly rate breakdown: total 900 Kč/h
        "hourly_rate_amortization": 350.0,
        "hourly_rate_labor": 250.0,
        "hourly_rate_tools": 150.0,
        "hourly_rate_overhead": 150.0,
        "setup_base_min": 35.0,
        "setup_per_tool_min": 3.0,
        "priority": 30,
        "active": True,
        "notes": "3-osá frézka pro jednoduché díly",
        "created_by": "system_seed"
    }
]


async def seed_machines():
    """Naplnění databáze stroji"""
    async with async_session() as session:
        created = 0
        skipped = 0

        for machine_data in MACHINES:
            # Kontrola existence podle kódu
            from sqlalchemy import select
            result = await session.execute(
                select(MachineDB).where(MachineDB.code == machine_data["code"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                skipped += 1
                print(f"⏭️  {machine_data['code']} - již existuje")
                continue

            # Vytvoření nového stroje
            machine = MachineDB(**machine_data)
            session.add(machine)
            created += 1
            print(f"✅ {machine_data['code']} - vytvořeno")

        # Commit
        await session.commit()

        print(f"\n📊 Seed strojů dokončen:")
        print(f"   ✅ Vytvořeno: {created}")
        print(f"   ⏭️  Přeskočeno: {skipped}")
        print(f"   📦 Celkem: {len(MACHINES)}")


if __name__ == "__main__":
    print("🚀 Seed strojů do GESTIMA databáze\n")
    asyncio.run(seed_machines())
