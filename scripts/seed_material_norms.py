"""GESTIMA - Seed Material Norms (norma → MaterialGroup mapping + aliases)"""

import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import MaterialNorm, MaterialGroup


# Format: (w_nr, en_iso, csn, aisi, material_group_code, note)
# W.Nr = Werkstoffnummer (German material number: 1.4301, 1.0503)
# EN ISO = European norm (C45, X5CrNi18-10, 11SMnPb30)
# ČSN = Czech norm (12050, 11109, 17240)
# AISI = American Iron and Steel Institute (304, 1045, 4140)

NORMS_DATA = [
    # ========== OCEL (všechny typy) ==========
    # MaterialGroup: "OCEL"
    ("1.0715", "11SMnPb30", "11109", None, "OCEL", "Ocel automatová s Mn, S a Pb"),
    ("1.0038", "S235JR", None, None, "OCEL", "Konstrukční ocel nelegovaná S235"),
    ("1.0503", "C45", "12050", "1045", "OCEL", "Ocel konstrukční uhlíková (0.45% C)"),
    ("1.1191", "C45E", None, None, "OCEL", "C45 pro tepelné zpracování"),
    ("1.7225", "42CrMo4", "15142", "4140", "OCEL", "Ocel legovaná chromem a molybdenem"),
    ("1.7131", "16MnCr5", "14220", "5115", "OCEL", "Ocel cementační s Mn a Cr"),
    (None, "S235", None, None, "OCEL", "Konstrukční ocel S235 (alternativní zápis)"),
    (None, "C45", None, None, "OCEL", "Konstrukční ocel C45 (alternativní zápis)"),

    # ========== NEREZ (všechny typy) ==========
    # MaterialGroup: "NEREZ"
    ("1.4301", "X5CrNi18-10", "17240", "304", "NEREZ", "Nerez austenit. 18% Cr, 10% Ni (304)"),
    ("1.4303", "X5CrNi18-9", None, "304L", "NEREZ", "Low carbon variant (304L)"),
    ("1.4307", None, None, "304L", "NEREZ", "Low carbon variant podle EN"),
    ("1.4404", "X2CrNiMo17-12-2", "17350", "316L", "NEREZ", "Nerez austenit. s Mo (316L)"),
    ("1.4401", "X5CrNiMo17-12-2", None, "316", "NEREZ", "Standardní carbon 316"),

    # ========== HLINÍK ==========
    # MaterialGroup: "HLINIK"
    (None, "6060", None, None, "HLINIK", "Hliník AlMgSi (běžný konstrukční)"),
    (None, "EN AW-6060", None, None, "HLINIK", "Plné označení podle EN 573-3"),
    (None, "7075", None, None, "HLINIK", "Dural AlZnMgCu (letectví)"),
    (None, "EN AW-7075", None, None, "HLINIK", "Plné označení podle EN 573-3"),

    # ========== MOSAZ ==========
    # MaterialGroup: "MOSAZ"
    ("2.0321", "CuZn37", None, None, "MOSAZ", "Mosaz Ms63 (63% Cu, 37% Zn)"),
    (None, "CW508L", None, "C27400", "MOSAZ", "Materiálové číslo podle EN 12163"),
    ("2.0401", "CuZn39Pb3", None, "C38500", "MOSAZ", "Mosaz automatová s 3% Pb"),
    (None, "CW614N", None, None, "MOSAZ", "Materiálové číslo podle EN 12164"),

    # ========== PLASTY ==========
    # MaterialGroup: "PLASTY"
    (None, "PA6", None, None, "PLASTY", "Polyamid 6 (Nylon 6)"),
    (None, "POM", None, None, "PLASTY", "Polyoxymethylen (Acetal)"),
    (None, "POM-C", None, None, "PLASTY", "Kopolymer (běžnější)"),
    (None, "POM-H", None, None, "PLASTY", "Homopolymer (lepší mechanika)"),
]


async def seed_material_norms(session: AsyncSession):
    """
    Seed MaterialNorm záznamy (conversion table: 4 columns → MaterialGroup).

    Logika:
    1. Pro každý řádek najde MaterialGroup podle code
    2. Vytvoří MaterialNorm záznam s 4 sloupci (w_nr, en_iso, csn, aisi)
    3. Každý řádek = 1 převodní záznam (min. 1 sloupec vyplněn)
    """
    print("🌱 Seeding MaterialNorms...")

    # Načíst existující MaterialGroups
    result = await session.execute(
        select(MaterialGroup).where(MaterialGroup.deleted_at.is_(None))
    )
    groups = {g.code: g for g in result.scalars().all()}

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

        # Check duplikát (same group + same norms)
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
        print("   These norms were skipped. Create MaterialGroups first or update seed data.")


async def main():
    """Run seed script directly"""
    async with async_session() as session:
        await seed_material_norms(session)


if __name__ == "__main__":
    asyncio.run(main())
