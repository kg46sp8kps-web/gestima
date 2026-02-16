#!/usr/bin/env python3
"""GESTIMA - Seed Material Norms (Infor CloudSuite catalog)

Data extracted from: data/materialy_export_import.xlsx
Via: scripts/archive/extract_material_norms_from_infor.py
82 unique material norms from production Infor catalog.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import MaterialNorm, MaterialGroup


# Format: (w_nr, csn, en_iso, aisi, group_name)
# group_name must match MaterialGroup.name exactly
NORMS_DATA = [
    # === OCEL KONSTRUKČNÍ (15) ===
    ("1.0036", "11373", "S235JRG1", None, "Ocel konstrukční"),
    ("1.0038", "11375", "S235JR(G2)", None, "Ocel konstrukční"),
    ("1.0039", "11375", "S235JRH", None, "Ocel konstrukční"),
    ("1.0050", "11500", "E295", None, "Ocel konstrukční"),
    ("1.0060", "11600", "E335", None, "Ocel konstrukční"),
    ("1.0070", "11700", "E360", None, "Ocel konstrukční"),
    ("1.0330", "11321", "DC01", None, "Ocel konstrukční"),
    ("1.0501", "12040", "C35", None, "Ocel konstrukční"),
    ("1.0503", "12050", "C45", None, "Ocel konstrukční"),
    ("1.0535", "12060", "C55", None, "Ocel konstrukční"),
    ("1.0570", "11523", "S355J2G3", None, "Ocel konstrukční"),
    ("1.0577", "11503", "S355J2", None, "Ocel konstrukční"),
    ("1.0762", None, "ETG100", None, "Ocel konstrukční"),
    ("1.1141", "12023", "C15E", None, "Ocel konstrukční"),
    ("1.1213", "12051", "C53", None, "Ocel konstrukční"),

    # === OCEL AUTOMATOVÁ (1) ===
    ("1.0715", "11109", "11SMn30", None, "Ocel automatová"),

    # === OCEL NÁSTROJOVÁ (14) ===
    ("1.1545", "19191", "C105U", None, "Ocel nástrojová"),
    ("1.1730", "19083", "C45U", None, "Ocel nástrojová"),
    ("1.2080", "19436", "X210Cr12", None, "Ocel nástrojová"),
    ("1.2101", "19452", "62SiMnCr4", None, "Ocel nástrojová"),
    ("1.2162", "19487", "21MnCr5", None, "Ocel nástrojová"),
    ("1.2210", "19421", "115CrV3", None, "Ocel nástrojová"),
    ("1.2311", "19520", "40CrMnMo7", None, "Ocel nástrojová"),
    ("1.2316", None, None, None, "Ocel nástrojová"),
    ("1.2379", "19573", "X153CrMoV12", None, "Ocel nástrojová"),
    ("1.2436", "19437", "X210CrW12", None, "Ocel nástrojová"),
    ("1.2721", "19614", "50NiCr13", None, "Ocel nástrojová"),
    ("1.2842", "19312 (19313)", "90MnCrV8", None, "Ocel nástrojová"),
    ("1.3343", "19830", "HS6-5-2C", None, "Ocel nástrojová"),
    ("1.3355", "19824", "HS18-0-1", None, "Ocel nástrojová"),

    # === OCEL LEGOVANÁ (13) ===
    ("1.3505", "14109", "100Cr6", None, "Ocel legovaná"),
    ("1.5122", "13240", None, None, "Ocel legovaná"),
    ("1.5713", "16240", None, "3135", "Ocel legovaná"),
    ("1.5752", "16420", "15NiCr13", "3310", "Ocel legovaná"),
    ("1.5864", "16640", None, None, "Ocel legovaná"),
    ("1.6582", "16342 (16343)", "34CrNiMo6", "4340", "Ocel legovaná"),
    ("1.7131", "14220", "16MnCr5", "5115", "Ocel legovaná"),
    ("1.7225", "15341", "42CrMo4", "4140", "Ocel legovaná"),
    ("1.7707", "15241 (15240)", "30CrMoV9", "- (6135)", "Ocel legovaná"),
    ("1.7733", "15236", "24CrMoV5-5", None, "Ocel legovaná"),
    ("1.8159", "15260", "51CrV4", "6150", "Ocel legovaná"),
    ("1.8162", "15231", None, None, "Ocel legovaná"),
    ("1.8519", "15330", "31CrMoV9", None, "Ocel legovaná"),

    # === NEREZ (16) ===
    ("1.2083", "17024", "X40Cr14", None, "Nerez"),
    ("1.3912", "17745", "FeNi36", None, "Nerez"),
    ("1.4021", "17022", "X20Cr13", None, "Nerez"),
    ("1.4034", "17029", "X46Cr 13", "420", "Nerez"),
    ("1.4057", "17145", "X19CrNi17-2", None, "Nerez"),
    ("1.4104", "17140", "X14CrMoS17", None, "Nerez"),
    ("1.4112", "17042 (17151)", "X90CrMoV18", None, "Nerez"),
    ("1.4301", "17240 (17241)", "X5CrNi18-10", "304", "Nerez"),
    ("1.4305", "17243", "X8CrNiS18-9", "303", "Nerez"),
    ("1.4404", "17346", "GX2CrNiMoN17-11-2", "316", "Nerez"),
    ("1.4418", None, "X4CrNiMo16-5-1", None, "Nerez"),
    ("1.4435", "17349", "X2CrNiMo18-14-3", "316L", "Nerez"),
    ("1.4541", "17247", "X6CrNiTi18-10", "321", "Nerez"),
    ("1.4542", None, "X5CrNiCuNb 16-4", "630", "Nerez"),
    ("1.4571", "17347 (17348)", "X6CrNiMoTi17-12-2", "316Ti", "Nerez"),
    ("1.4878", "17248", "X8CrNiTi18-10", "321", "Nerez"),

    # === MĚĎ (6) ===
    ("2.0060", "42 3001", "CW004A", None, "Měď"),
    ("2.0280", "42 3212", "CW506L", None, "Měď"),
    ("2.0321", "42 3213", "CW508L", None, "Měď"),
    ("2.0401", None, "CW614N", None, "Měď"),
    ("2.0966", "42 3047", "CW307G", None, "Měď"),
    ("2.0975", None, "W307G", None, "Měď"),

    # === MOSAZ (5) ===
    ("2.1030", "42 3018", "CW453K", None, "Mosaz"),
    ("2.1053", None, "CC493K", None, "Mosaz"),
    ("2.1090", None, "CC493K", None, "Mosaz"),
    ("2.1182", None, "CC496K", None, "Mosaz"),
    ("2.1293", None, "CW106C", None, "Mosaz"),

    # === HLINÍK (12) ===
    ("3.0615", None, "AW 6012", None, "Hliník"),
    ("3.1325", "424201", "AW 2017", None, "Hliník"),
    ("3.1355", "424203", "AW 2024", None, "Hliník"),
    ("3.1645", "( 42 4254 )", "AW 2007", None, "Hliník"),
    ("3.2306", None, "AW-6060", None, "Hliník"),
    ("3.2315", "424400", "AW 6082", None, "Hliník"),
    ("3.3206", "42 4401", "AW 6060", None, "Hliník"),
    ("3.3535", "424413", "AW 5754", None, "Hliník"),
    ("3.3547", "424415", "AW 5083", None, "Hliník"),
    ("3.4345", None, "AW 7022", None, "Hliník"),
    ("3.4365", "424222", "AW 7075", None, "Hliník"),
    ("3.C330", None, "AW 7021", None, "Hliník"),
]


async def seed_material_norms(session: AsyncSession):
    """
    Seed MaterialNorm záznamy z Infor katalogu.
    Idempotentní: smaže stávající normy a vytvoří znovu.
    """
    print("🌱 Seeding MaterialNorms (82 norms from Infor catalog)...")

    # Načíst existující MaterialGroups (indexed by name)
    result = await session.execute(
        select(MaterialGroup).where(MaterialGroup.deleted_at.is_(None))
    )
    groups_by_name = {g.name: g for g in result.scalars().all()}
    print(f"  📦 Available MaterialGroups: {len(groups_by_name)}")

    # Load existing norms indexed by w_nr for upsert
    result = await session.execute(select(MaterialNorm))
    existing_by_wnr = {n.w_nr: n for n in result.scalars().all() if n.w_nr}

    created_count = 0
    updated_count = 0
    skipped_count = 0
    missing_groups = set()

    for w_nr, csn, en_iso, aisi, group_name in NORMS_DATA:
        group = groups_by_name.get(group_name)
        if not group:
            missing_groups.add(group_name)
            skipped_count += 1
            continue

        # At least w_nr must be filled (it always is in Infor data)
        if not w_nr:
            skipped_count += 1
            continue

        existing = existing_by_wnr.get(w_nr)
        if existing:
            # Update existing — sync group_id and norm fields
            changed = False
            if existing.material_group_id != group.id:
                existing.material_group_id = group.id
                changed = True
            if existing.en_iso != en_iso:
                existing.en_iso = en_iso
                changed = True
            if existing.csn != csn:
                existing.csn = csn
                changed = True
            if existing.aisi != aisi:
                existing.aisi = aisi
                changed = True
            if changed:
                updated_count += 1
            else:
                skipped_count += 1
        else:
            norm = MaterialNorm(
                w_nr=w_nr,
                en_iso=en_iso,
                csn=csn,
                aisi=aisi,
                material_group_id=group.id,
                note=None,
            )
            session.add(norm)
            created_count += 1

    await session.commit()

    print(f"✅ MaterialNorms seeded: {created_count} created, {updated_count} updated, {skipped_count} unchanged")

    if missing_groups:
        print(f"⚠️  Missing MaterialGroups: {', '.join(missing_groups)}")


async def main():
    """Run seed script directly"""
    async with async_session() as session:
        await seed_material_norms(session)


if __name__ == "__main__":
    asyncio.run(main())
