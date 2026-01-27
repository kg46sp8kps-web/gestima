#!/usr/bin/env python3
"""GESTIMA - Seed Material Norms (auto-generated from Excel catalog)

Generated: 2026-01-27
Source: data/materialy_export_import.xlsx
Norms database: DIN EN 10027, ČSN EN 10027, AISI standards
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
# Stats: 83 materials with norms, 0 TODO (missing norms)
from app.models import MaterialNorm, MaterialGroup


# Format: (w_nr, en_iso, csn, aisi, material_group_code, note)
NORMS_DATA = [
    ("1.0036", "S235JR", "11373", None, "OCEL-KONS", "Ocel konstrukční pro svařování"),
    ("1.0039", "S235JRH", "11373", None, "OCEL-KONS", "Ocel konstrukční pro trubky"),
    ("1.0050", "E295", "11500", None, "OCEL-KONS", "Ocel konstrukční"),
    ("1.0060", "S355MC", "11523", None, "OCEL-KONS", "Ocel pro tváření za studena"),
    ("1.0070", "S235J2", "11373", None, "OCEL-KONS", "Ocel konstrukční"),
    ("1.0308", "C10", "12010", "1010", "OCEL-KONS", "Ocel uhlíková nízkouhlíková"),
    ("1.0330", "DC01", "11320", None, "OCEL-KONS", "Ocel pro tváření za studena"),
    ("1.0501", "C35", "12035", "1035", "OCEL-KONS", "Ocel uhlíková"),
    ("1.0503", "C45", "12050", "1045", "OCEL-KONS", "Ocel konstrukční uhlíková"),
    ("1.0535", "C45E", "12050.4", "1045", "OCEL-KONS", "Ocel uhlíková kalitelná"),
    ("1.0570", "S355J2", "11523", None, "OCEL-KONS", "Ocel konstrukční pro svařování"),
    ("1.0577", "S355J0", "11523", None, "OCEL-KONS", "Ocel konstrukční"),
    ("1.0715", "C60", "12060", "1060", "OCEL-KONS", "Ocel uhlíková"),
    ("1.0762", "C75", "12075", "1075", "OCEL-KONS", "Ocel uhlíková pružinová"),
    ("1.1013", "S235JRG2", "11373", None, "OCEL-AUTO", "Ocel pro svařování"),
    ("1.1141", "11SMn30", "12050", "1215", "OCEL-AUTO", "Ocel automatová"),
    ("1.1191", "11SMnPb30", "12050", "12L13", "OCEL-AUTO", "Ocel automatová"),
    ("1.1545", "9SMn36", "12040", None, "OCEL-AUTO", "Ocel automatová"),
    ("1.2080", "X210Cr12", "19830", "D3", "OCEL-NAST", "Ocel nástrojová na studeno"),
    ("1.2083", "X42Cr13", "17027", "420", "OCEL-NAST", "Ocel nástrojová korozivzdorná"),
    ("1.2101", "100Cr6", "14109", "52100", "OCEL-NAST", "Ocel ložisková"),
    ("1.2162", "21CrMoV5-11", None, None, "OCEL-NAST", "Ocel nástrojová na teplo"),
    ("1.2210", "115CrV3", "19121", None, "OCEL-NAST", "Ocel nástrojová"),
    ("1.2311", "40CrMnMo7", "19436", "P20", "OCEL-NAST", "Ocel nástrojová pro formy"),
    ("1.2316", "X38CrMo16", "19436", "420", "OCEL-NAST", "Ocel nástrojová korozivzdorná"),
    ("1.2379", "X153CrMoV12", "19573", "D2", "OCEL-NAST", "Ocel nástrojová pro studenou práci"),
    ("1.2436", "X210Cr12", "19830", "D3", "OCEL-NAST", "Ocel nástrojová"),
    ("1.2721", "50NiCr13", None, None, "OCEL-NAST", "Ocel nástrojová"),
    ("1.2842", "90MnCrV8", "19830", "O2", "OCEL-NAST", "Ocel nástrojová na olej"),
    ("1.3343", "HS6-5-2", "19830", "M2", "OCEL-LEG", "Rychlořezná ocel"),
    ("1.3355", "HS6-5-2-5", None, "M35", "OCEL-LEG", "Rychlořezná ocel kobaltová"),
    ("1.3505", "100Cr6", "14109", "52100", "OCEL-LEG", "Ocel ložisková"),
    ("1.3912", "X46Cr13", "17027", "420", "OCEL-LEG", "Ocel nástrojová"),
    ("1.4021", "X20Cr13", "17022", "420", "NEREZ", "Nerez martenzitická"),
    ("1.4028", "X30Cr13", "17023", "420", "NEREZ", "Nerez martenzitická"),
    ("1.4034", "X46Cr13", "17027", "420", "NEREZ", "Nerez martenzitická"),
    ("1.4104", "X14CrMoS17", "17027", "430F", "NEREZ", "Nerez feritická automatová"),
    ("1.4112", "X90CrMoV18", None, "440B", "NEREZ", "Nerez martenzitická vysokouhlíková"),
    ("1.4301", "X5CrNi18-10", "17240", "304", "NEREZ", "Nerez austenitická"),
    ("1.4305", "X8CrNiS18-9", "17247", "303", "NEREZ", "Nerez automatová"),
    ("1.4404", "X2CrNiMo17-12-2", "17349", "316L", "NEREZ", "Nerez molybdenová nízko-uhlíková"),
    ("1.4418", "X4CrNiMo16-5-1", "17349", None, "NEREZ", "Nerez martenzitická"),
    ("1.4435", "X2CrNiMo18-14-3", "17349", "316L", "NEREZ", "Nerez molybdenová"),
    ("1.4541", "X6CrNiTi18-10", "17248", "321", "NEREZ", "Nerez stabilizovaná titanem"),
    ("1.4542", "X5CrNiCuNb16-4", None, "630", "NEREZ", "Nerez precipitačně vytvrditelná"),
    ("1.4571", "X6CrNiMoTi17-12-2", "17352", "316Ti", "NEREZ", "Nerez stabilizovaná titanem"),
    ("1.4878", "X12CrNiTi18-9", "17249", "321H", "NEREZ", "Nerez žáropevná"),
    ("1.5122", "20MnCr5", "14220", "5120", "OCEL-LEG", "Ocel cementační"),
    ("1.5713", "39CrMoV13-9", None, None, "OCEL-LEG", "Ocel nástrojová na teplo"),
    ("1.5752", "14NiCr14", "14220", None, "OCEL-LEG", "Ocel cementační"),
    ("1.5864", "21CrMoV5-7", None, None, "OCEL-LEG", "Ocel nástrojová"),
    ("1.6582", "34CrNiMo6", "15330", "4340", "OCEL-LEG", "Ocel nízkolegovaná"),
    ("1.7102", "16MnCrS5", "14220", None, "OCEL-LEG", "Ocel cementační"),
    ("1.7131", "16MnCr5", "14220", "5115", "OCEL-LEG", "Ocel cementační"),
    ("1.7225", "42CrMo4", "15142", "4140", "OCEL-LEG", "Ocel legovaná Cr-Mo"),
    ("1.7707", "30CrMoV9", None, None, "OCEL-LEG", "Ocel legovaná"),
    ("1.7733", "28Mn6", None, None, "OCEL-LEG", "Ocel manganová"),
    ("1.8159", "50CrV4", "15260", "6150", "OCEL-LEG", "Ocel pružinová"),
    ("1.8162", "51CrV4", "15260", "6150", "OCEL-LEG", "Ocel pružinová"),
    ("1.8519", "X10CrAlSi25", None, None, "OCEL-LEG", "Ocel žáropevná"),
    ("2.0060", "Cu-ETP", "42301", "C11000", "MED", "Měď elektrolytická"),
    ("2.0280", "CuZn10", "42320", None, "MED", "Mosaz"),
    ("2.0321", "CuNi10Fe1Mn", "42390", "C70600", "MED", "Měďonikl"),
    ("2.0401", "SF-Cu", "42301", "C10200", "MED", "Měď bez kyslíku"),
    ("2.0402", "CuAg0,1", "42301", None, "MED", "Měď stříbrem legovaná"),
    ("2.0966", "CuNi18Zn20", "42392", "C75200", "MED", "Niklová mosaz (nové stříbro)"),
    ("2.0975", "CuNi12Zn24", "42392", None, "MED", "Niklová mosaz"),
    ("2.1030", "CuZn39Pb3", "42328", "C38500", "MOSAZ", "Mosaz automatová"),
    ("2.1053", "CuZn37", "42320", "C27400", "MOSAZ", "Mosaz"),
    ("2.1090", "CuZn40Mn2Fe1", "42328", None, "MOSAZ", "Mosaz speciální"),
    ("2.1182", "CuZn40Pb2", "42328", "C38500", "MOSAZ", "Mosaz automatová"),
    ("2.1293", "CuZn36Pb2As", "42328", None, "MOSAZ", "Mosaz automatová"),
    ("3.0615", "AlMgSi0,5", "42440", "6060", "HLINIK", "Hliník slitina"),
    ("3.1325", "AlMg3", "42421", "5754", "HLINIK", "Hliník slitina"),
    ("3.1355", "AlMg4,5Mn", "42461", "5083", "HLINIK", "Hliník slitina"),
    ("3.1645", "AlMg5", "42465", "5086", "HLINIK", "Hliník slitina"),
    ("3.2306", "AlCu4MgSi", "42404", "2014", "HLINIK", "Hliník slitina dural"),
    ("3.2315", "AlMg3Mn", "42445", "5454", "HLINIK", "Hliník slitina"),
    ("3.3206", "AlCuMg2", "42401", "2024", "HLINIK", "Hliník slitina dural"),
    ("3.3535", "AlMg3", "42421", "5754", "HLINIK", "Hliník slitina"),
    ("3.3547", "AlMg5", "42465", "5086", "HLINIK", "Hliník slitina"),
    ("3.4345", "AlMgSi1", "42440", "6082", "HLINIK", "Hliník slitina"),
    ("3.4365", "AlZn5,5MgCu", "42490", "7075", "HLINIK", "Hliník slitina vysokopevnostní"),
]


async def seed_material_norms(session: AsyncSession):
    """
    Seed MaterialNorm záznamy (conversion table: 4 columns → MaterialGroup).
    """
    print("🌱 Seeding MaterialNorms...")

    # Načíst existující MaterialGroups
    result = await session.execute(
        select(MaterialGroup).where(MaterialGroup.deleted_at.is_(None))
    )
    groups = {g.code: g for g in result.scalars().all()}
    print(f"  📦 Available MaterialGroups: {len(groups)}")

    # Načíst existující MaterialNorms
    result = await session.execute(
        select(MaterialNorm).where(MaterialNorm.deleted_at.is_(None))
    )
    existing_norms = list(result.scalars().all())

    created_count = 0
    skipped_count = 0
    missing_groups = set()

    for w_nr, en_iso, csn, aisi, group_code, note in NORMS_DATA:
        # Najít MaterialGroup
        group = groups.get(group_code)
        if not group:
            missing_groups.add(group_code)
            skipped_count += 1
            continue

        # Check: At least one norm column must be filled
        if not any([w_nr, en_iso, csn, aisi]):
            print(f"⚠️  Skipping invalid row: {note} (no norm filled)")
            skipped_count += 1
            continue

        # Check duplikát
        is_duplicate = False
        for existing in existing_norms:
            if (existing.material_group_id == group.id and
                existing.w_nr == w_nr and
                existing.en_iso == en_iso and
                existing.csn == csn and
                existing.aisi == aisi):
                is_duplicate = True
                break

        if is_duplicate:
            skipped_count += 1
            continue

        # Vytvořit MaterialNorm
        norm = MaterialNorm(
            w_nr=w_nr.upper() if w_nr else None,
            en_iso=en_iso.upper() if en_iso else None,
            csn=csn.upper() if csn else None,
            aisi=aisi.upper() if aisi else None,
            material_group_id=group.id,
            note=note
        )
        session.add(norm)
        existing_norms.append(norm)
        created_count += 1

    await session.commit()

    print(f"✅ MaterialNorms seeded: {created_count} created, {skipped_count} skipped")

    if missing_groups:
        print(f"⚠️  Missing MaterialGroups: {', '.join(missing_groups)}")


async def main():
    """Run seed script directly"""
    async with async_session() as session:
        await seed_material_norms(session)


if __name__ == "__main__":
    asyncio.run(main())
