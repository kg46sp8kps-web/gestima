#!/usr/bin/env python3
"""
Generuj kompletní MaterialNorms seed z Excel katalogu

Workflow:
1. Načte parsovaná data z temp/material_codes_preview.csv
2. Extrahuje unikátní W.Nr. materiály
3. Pro každý W.Nr. najde EN ISO, ČSN, AISI normy z databáze
4. Vytvoří kompletní seed script pro MaterialNorms
5. Identifikuje MaterialGroup pro každou normu

Output: scripts/seed_material_norms_complete.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import csv
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict, Counter


# ========== PATHS ==========
PARSED_CSV = Path(__file__).parent.parent / "temp" / "material_codes_preview.csv"
OUTPUT_SEED = Path(__file__).parent / "seed_material_norms_complete.py"


# ========== MATERIAL NORMS DATABASE ==========
# Source: DIN EN 10027, ČSN EN 10027, AISI standards
MATERIAL_NORMS = {
    # ===== OCELI KONSTRUKČNÍ (1.0xxx) =====
    "1.0036": {
        "en_iso": "S235JR",
        "csn": "11373",
        "aisi": None,
        "note": "Ocel konstrukční pro svařování"
    },
    "1.0038": {
        "en_iso": "S235JRG1",
        "csn": "11373.1",
        "aisi": None,
        "note": "Ocel konstrukční jemnozrnná"
    },
    "1.0039": {
        "en_iso": "S235JRH",
        "csn": "11373",
        "aisi": None,
        "note": "Ocel konstrukční pro trubky"
    },
    "1.0050": {
        "en_iso": "E295",
        "csn": "11500",
        "aisi": None,
        "note": "Ocel konstrukční"
    },
    "1.0060": {
        "en_iso": "S355MC",
        "csn": "11523",
        "aisi": None,
        "note": "Ocel pro tváření za studena"
    },
    "1.0070": {
        "en_iso": "S235J2",
        "csn": "11373",
        "aisi": None,
        "note": "Ocel konstrukční"
    },
    "1.0308": {
        "en_iso": "C10",
        "csn": "12010",
        "aisi": "1010",
        "note": "Ocel uhlíková nízkouhlíková"
    },
    "1.0330": {
        "en_iso": "DC01",
        "csn": "11320",
        "aisi": None,
        "note": "Ocel pro tváření za studena"
    },
    "1.0501": {
        "en_iso": "C35",
        "csn": "12035",
        "aisi": "1035",
        "note": "Ocel uhlíková"
    },
    "1.0503": {
        "en_iso": "C45",
        "csn": "12050",
        "aisi": "1045",
        "note": "Ocel konstrukční uhlíková"
    },
    "1.0535": {
        "en_iso": "C45E",
        "csn": "12050.4",
        "aisi": "1045",
        "note": "Ocel uhlíková kalitelná"
    },
    "1.0570": {
        "en_iso": "S355J2",
        "csn": "11523",
        "aisi": None,
        "note": "Ocel konstrukční pro svařování"
    },
    "1.0577": {
        "en_iso": "S355J0",
        "csn": "11523",
        "aisi": None,
        "note": "Ocel konstrukční"
    },
    "1.0715": {
        "en_iso": "C60",
        "csn": "12060",
        "aisi": "1060",
        "note": "Ocel uhlíková"
    },
    "1.0762": {
        "en_iso": "C75",
        "csn": "12075",
        "aisi": "1075",
        "note": "Ocel uhlíková pružinová"
    },

    # ===== OCELI AUTOMATOVÉ (1.1xxx) =====
    "1.1013": {
        "en_iso": "S235JRG2",
        "csn": "11373",
        "aisi": None,
        "note": "Ocel pro svařování"
    },
    "1.1141": {
        "en_iso": "11SMn30",
        "csn": "12050",
        "aisi": "1215",
        "note": "Ocel automatová"
    },
    "1.1191": {
        "en_iso": "11SMnPb30",
        "csn": "12050",
        "aisi": "12L13",
        "note": "Ocel automatová"
    },
    "1.1213": {
        "en_iso": "11SMnPb37",
        "csn": "12053",
        "aisi": None,
        "note": "Ocel automatová"
    },
    "1.1545": {
        "en_iso": "9SMn36",
        "csn": "12040",
        "aisi": None,
        "note": "Ocel automatová"
    },

    # ===== OCELI NÁSTROJOVÉ (1.2xxx) =====
    "1.2080": {
        "en_iso": "X210Cr12",
        "csn": "19830",
        "aisi": "D3",
        "note": "Ocel nástrojová na studeno"
    },
    "1.2083": {
        "en_iso": "X42Cr13",
        "csn": "17027",
        "aisi": "420",
        "note": "Ocel nástrojová korozivzdorná"
    },
    "1.2101": {
        "en_iso": "100Cr6",
        "csn": "14109",
        "aisi": "52100",
        "note": "Ocel ložisková"
    },
    "1.2162": {
        "en_iso": "21CrMoV5-11",
        "csn": None,
        "aisi": None,
        "note": "Ocel nástrojová na teplo"
    },
    "1.2210": {
        "en_iso": "115CrV3",
        "csn": "19121",
        "aisi": None,
        "note": "Ocel nástrojová"
    },
    "1.2311": {
        "en_iso": "40CrMnMo7",
        "csn": "19436",
        "aisi": "P20",
        "note": "Ocel nástrojová pro formy"
    },
    "1.2316": {
        "en_iso": "X38CrMo16",
        "csn": "19436",
        "aisi": "420",
        "note": "Ocel nástrojová korozivzdorná"
    },
    "1.2379": {
        "en_iso": "X153CrMoV12",
        "csn": "19573",
        "aisi": "D2",
        "note": "Ocel nástrojová pro studenou práci"
    },
    "1.2436": {
        "en_iso": "X210Cr12",
        "csn": "19830",
        "aisi": "D3",
        "note": "Ocel nástrojová"
    },
    "1.2721": {
        "en_iso": "50NiCr13",
        "csn": None,
        "aisi": None,
        "note": "Ocel nástrojová"
    },
    "1.2842": {
        "en_iso": "90MnCrV8",
        "csn": "19830",
        "aisi": "O2",
        "note": "Ocel nástrojová na olej"
    },

    # ===== OCELI RYCHLOŘEZNÉ (1.3xxx) =====
    "1.3343": {
        "en_iso": "HS6-5-2",
        "csn": "19830",
        "aisi": "M2",
        "note": "Rychlořezná ocel"
    },
    "1.3355": {
        "en_iso": "HS6-5-2-5",
        "csn": None,
        "aisi": "M35",
        "note": "Rychlořezná ocel kobaltová"
    },
    "1.3505": {
        "en_iso": "100Cr6",
        "csn": "14109",
        "aisi": "52100",
        "note": "Ocel ložisková"
    },
    "1.3912": {
        "en_iso": "X46Cr13",
        "csn": "17027",
        "aisi": "420",
        "note": "Ocel nástrojová"
    },

    # ===== NEREZ (1.4xxx) =====
    "1.4021": {
        "en_iso": "X20Cr13",
        "csn": "17022",
        "aisi": "420",
        "note": "Nerez martenzitická"
    },
    "1.4028": {
        "en_iso": "X30Cr13",
        "csn": "17023",
        "aisi": "420",
        "note": "Nerez martenzitická"
    },
    "1.4034": {
        "en_iso": "X46Cr13",
        "csn": "17027",
        "aisi": "420",
        "note": "Nerez martenzitická"
    },
    "1.4057": {
        "en_iso": "X17CrNi16-2",
        "csn": "17031",
        "aisi": "431",
        "note": "Nerez feritická"
    },
    "1.4104": {
        "en_iso": "X14CrMoS17",
        "csn": "17027",
        "aisi": "430F",
        "note": "Nerez feritická automatová"
    },
    "1.4112": {
        "en_iso": "X90CrMoV18",
        "csn": None,
        "aisi": "440B",
        "note": "Nerez martenzitická vysokouhlíková"
    },
    "1.4301": {
        "en_iso": "X5CrNi18-10",
        "csn": "17240",
        "aisi": "304",
        "note": "Nerez austenitická"
    },
    "1.4305": {
        "en_iso": "X8CrNiS18-9",
        "csn": "17247",
        "aisi": "303",
        "note": "Nerez automatová"
    },
    "1.4404": {
        "en_iso": "X2CrNiMo17-12-2",
        "csn": "17349",
        "aisi": "316L",
        "note": "Nerez molybdenová nízko-uhlíková"
    },
    "1.4418": {
        "en_iso": "X4CrNiMo16-5-1",
        "csn": "17349",
        "aisi": None,
        "note": "Nerez martenzitická"
    },
    "1.4435": {
        "en_iso": "X2CrNiMo18-14-3",
        "csn": "17349",
        "aisi": "316L",
        "note": "Nerez molybdenová"
    },
    "1.4541": {
        "en_iso": "X6CrNiTi18-10",
        "csn": "17248",
        "aisi": "321",
        "note": "Nerez stabilizovaná titanem"
    },
    "1.4542": {
        "en_iso": "X5CrNiCuNb16-4",
        "csn": None,
        "aisi": "630",
        "note": "Nerez precipitačně vytvrditelná"
    },
    "1.4571": {
        "en_iso": "X6CrNiMoTi17-12-2",
        "csn": "17352",
        "aisi": "316Ti",
        "note": "Nerez stabilizovaná titanem"
    },
    "1.4878": {
        "en_iso": "X12CrNiTi18-9",
        "csn": "17249",
        "aisi": "321H",
        "note": "Nerez žáropevná"
    },

    # ===== OCELI LEGOVANÉ (1.5xxx - 1.8xxx) =====
    "1.5122": {
        "en_iso": "20MnCr5",
        "csn": "14220",
        "aisi": "5120",
        "note": "Ocel cementační"
    },
    "1.5217": {
        "en_iso": "55NiCrMoV7",
        "csn": "15330",
        "aisi": None,
        "note": "Ocel nízkolegovaná pro tepelné zpracování"
    },
    "1.5713": {
        "en_iso": "39CrMoV13-9",
        "csn": None,
        "aisi": None,
        "note": "Ocel nástrojová na teplo"
    },
    "1.5752": {
        "en_iso": "14NiCr14",
        "csn": "14220",
        "aisi": None,
        "note": "Ocel cementační"
    },
    "1.5864": {
        "en_iso": "21CrMoV5-7",
        "csn": None,
        "aisi": None,
        "note": "Ocel nástrojová"
    },
    "1.6582": {
        "en_iso": "34CrNiMo6",
        "csn": "15330",
        "aisi": "4340",
        "note": "Ocel nízkolegovaná"
    },
    "1.7102": {
        "en_iso": "16MnCrS5",
        "csn": "14220",
        "aisi": None,
        "note": "Ocel cementační"
    },
    "1.7131": {
        "en_iso": "16MnCr5",
        "csn": "14220",
        "aisi": "5115",
        "note": "Ocel cementační"
    },
    "1.7225": {
        "en_iso": "42CrMo4",
        "csn": "15142",
        "aisi": "4140",
        "note": "Ocel legovaná Cr-Mo"
    },
    "1.7707": {
        "en_iso": "30CrMoV9",
        "csn": None,
        "aisi": None,
        "note": "Ocel legovaná"
    },
    "1.7733": {
        "en_iso": "28Mn6",
        "csn": None,
        "aisi": None,
        "note": "Ocel manganová"
    },
    "1.8159": {
        "en_iso": "50CrV4",
        "csn": "15260",
        "aisi": "6150",
        "note": "Ocel pružinová"
    },
    "1.8162": {
        "en_iso": "51CrV4",
        "csn": "15260",
        "aisi": "6150",
        "note": "Ocel pružinová"
    },
    "1.8519": {
        "en_iso": "X10CrAlSi25",
        "csn": None,
        "aisi": None,
        "note": "Ocel žáropevná"
    },

    # ===== MĚĎ A SLITINY (2.0xxx) =====
    "2.0060": {
        "en_iso": "Cu-ETP",
        "csn": "42301",
        "aisi": "C11000",
        "note": "Měď elektrolytická"
    },
    "2.0280": {
        "en_iso": "CuZn10",
        "csn": "42320",
        "aisi": None,
        "note": "Mosaz"
    },
    "2.0321": {
        "en_iso": "CuNi10Fe1Mn",
        "csn": "42390",
        "aisi": "C70600",
        "note": "Měďonikl"
    },
    "2.0401": {
        "en_iso": "SF-Cu",
        "csn": "42301",
        "aisi": "C10200",
        "note": "Měď bez kyslíku"
    },
    "2.0402": {
        "en_iso": "CuAg0,1",
        "csn": "42301",
        "aisi": None,
        "note": "Měď stříbrem legovaná"
    },
    "2.0966": {
        "en_iso": "CuNi18Zn20",
        "csn": "42392",
        "aisi": "C75200",
        "note": "Niklová mosaz (nové stříbro)"
    },
    "2.0975": {
        "en_iso": "CuNi12Zn24",
        "csn": "42392",
        "aisi": None,
        "note": "Niklová mosaz"
    },

    # ===== MOSAZ (2.1xxx) =====
    "2.1030": {
        "en_iso": "CuZn39Pb3",
        "csn": "42328",
        "aisi": "C38500",
        "note": "Mosaz automatová"
    },
    "2.1053": {
        "en_iso": "CuZn37",
        "csn": "42320",
        "aisi": "C27400",
        "note": "Mosaz"
    },
    "2.1090": {
        "en_iso": "CuZn40Mn2Fe1",
        "csn": "42328",
        "aisi": None,
        "note": "Mosaz speciální"
    },
    "2.1182": {
        "en_iso": "CuZn40Pb2",
        "csn": "42328",
        "aisi": "C38500",
        "note": "Mosaz automatová"
    },
    "2.1293": {
        "en_iso": "CuZn36Pb2As",
        "csn": "42328",
        "aisi": None,
        "note": "Mosaz automatová"
    },

    # ===== HLINÍK (3.xxxx) =====
    "3.0255": {
        "en_iso": "AlMg4,5Mn0,7",
        "csn": "42461",
        "aisi": "5083",
        "note": "Hliník slitina"
    },
    "3.0615": {
        "en_iso": "AlMgSi0,5",
        "csn": "42440",
        "aisi": "6060",
        "note": "Hliník slitina"
    },
    "3.1325": {
        "en_iso": "AlMg3",
        "csn": "42421",
        "aisi": "5754",
        "note": "Hliník slitina"
    },
    "3.1355": {
        "en_iso": "AlMg4,5Mn",
        "csn": "42461",
        "aisi": "5083",
        "note": "Hliník slitina"
    },
    "3.1645": {
        "en_iso": "AlMg5",
        "csn": "42465",
        "aisi": "5086",
        "note": "Hliník slitina"
    },
    "3.2306": {
        "en_iso": "AlCu4MgSi",
        "csn": "42404",
        "aisi": "2014",
        "note": "Hliník slitina dural"
    },
    "3.2315": {
        "en_iso": "AlMg3Mn",
        "csn": "42445",
        "aisi": "5454",
        "note": "Hliník slitina"
    },
    "3.3206": {
        "en_iso": "AlCuMg2",
        "csn": "42401",
        "aisi": "2024",
        "note": "Hliník slitina dural"
    },
    "3.3535": {
        "en_iso": "AlMg3",
        "csn": "42421",
        "aisi": "5754",
        "note": "Hliník slitina"
    },
    "3.3547": {
        "en_iso": "AlMg5",
        "csn": "42465",
        "aisi": "5086",
        "note": "Hliník slitina"
    },
    "3.4345": {
        "en_iso": "AlMgSi1",
        "csn": "42440",
        "aisi": "6082",
        "note": "Hliník slitina"
    },
    "3.4365": {
        "en_iso": "AlZn5,5MgCu",
        "csn": "42490",
        "aisi": "7075",
        "note": "Hliník slitina vysokopevnostní"
    },
}


# ========== MATERIAL GROUP MAPPING ==========
def identify_material_group_code(wnr: str) -> str:
    """
    Mapuj W.Nr. na MaterialGroup code podle kategorie.

    Returns:
        MaterialGroup code (např. "OCEL-KONS", "OCEL-AUTO", "NEREZ")
    """
    if not wnr or '.' not in wnr:
        return "UNKNOWN"

    prefix = wnr[:3]  # "1.0", "1.4", "3.3"

    mapping = {
        "1.0": "OCEL-KONS",  # Ocel konstrukční
        "1.1": "OCEL-AUTO",  # Ocel automatová
        "1.2": "OCEL-NAST",  # Ocel nástrojová
        "1.3": "OCEL-LEG",   # Ocel rychlořezná / nízkolegovaná
        "1.4": "NEREZ",      # Nerez
        "1.5": "OCEL-LEG",   # Ocel legovaná
        "1.6": "OCEL-LEG",   # Ocel legovaná
        "1.7": "OCEL-LEG",   # Ocel legovaná
        "1.8": "OCEL-LEG",   # Ocel legovaná
        "2.0": "MED",        # Měď a slitiny
        "2.1": "MOSAZ",      # Mosaz
        "2.2": "BRONZ",      # Bronz
        "3.0": "HLINIK",     # Hliník
        "3.1": "HLINIK",
        "3.2": "HLINIK",
        "3.3": "HLINIK",
        "3.4": "HLINIK",
    }

    return mapping.get(prefix, "UNKNOWN")


def extract_materials_from_catalog() -> Dict[str, int]:
    """
    Extrahuj unikátní W.Nr. materiály z parsovaných dat.

    Returns:
        {w_nr: počet_variant}
    """
    if not PARSED_CSV.exists():
        print(f"❌ Parsovaná data nenalezena: {PARSED_CSV}")
        print("   Spusť nejdřív: python3 scripts/analyze_material_codes.py")
        return {}

    materials = []

    with open(PARSED_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            material_type = row.get('material_type', '')
            material_code = row.get('material', '')

            # Filter pouze kovové materiály (mají W.Nr. formát)
            if material_type == 'metal':
                # Filter W.Nr. format (X.YYYY)
                if '.' in material_code and material_code[0].isdigit():
                    materials.append(material_code)

    # Count occurrences
    material_counts = Counter(materials)

    return dict(material_counts)


def generate_seed_script(materials: Dict[str, int]) -> str:
    """
    Generuj kompletní seed script s MaterialNorms daty.

    Returns:
        Python source code pro seed script
    """
    lines = []

    # Header
    lines.append('"""GESTIMA - Seed Material Norms (auto-generated from Excel catalog)')
    lines.append('')
    lines.append('Generated: 2026-01-27')
    lines.append('Source: data/materialy_export_import.xlsx')
    lines.append('Norms database: DIN EN 10027, ČSN EN 10027, AISI standards')
    lines.append('"""')
    lines.append('')
    lines.append('import asyncio')
    lines.append('from sqlalchemy import select')
    lines.append('from sqlalchemy.ext.asyncio import AsyncSession')
    lines.append('')
    lines.append('from app.database import async_session')
    lines.append('from app.models import MaterialNorm, MaterialGroup')
    lines.append('')
    lines.append('')
    lines.append('# Format: (w_nr, en_iso, csn, aisi, material_group_code, note)')
    lines.append('NORMS_DATA = [')

    # Generate data tuples
    found = 0
    missing = 0

    for wnr in sorted(materials.keys()):
        group_code = identify_material_group_code(wnr)

        if wnr in MATERIAL_NORMS:
            norm = MATERIAL_NORMS[wnr]
            w_nr = f'"{wnr}"'
            en_iso = f'"{norm["en_iso"]}"' if norm["en_iso"] else 'None'
            csn = f'"{norm["csn"]}"' if norm["csn"] else 'None'
            aisi = f'"{norm["aisi"]}"' if norm["aisi"] else 'None'
            note = norm["note"]

            line = f'    ({w_nr}, {en_iso}, {csn}, {aisi}, "{group_code}", "{note}"),'
            lines.append(line)
            found += 1
        else:
            # Missing norm - placeholder
            line = f'    ("{wnr}", None, None, None, "{group_code}", "TODO: Doplnit normy"),'
            lines.append(line)
            missing += 1

    lines.append(']')
    lines.append('')
    lines.append('')

    # Seed function (copy from original)
    lines.append('async def seed_material_norms(session: AsyncSession):')
    lines.append('    """')
    lines.append('    Seed MaterialNorm záznamy (conversion table: 4 columns → MaterialGroup).')
    lines.append('    """')
    lines.append('    print("🌱 Seeding MaterialNorms...")')
    lines.append('')
    lines.append('    # Načíst existující MaterialGroups')
    lines.append('    result = await session.execute(')
    lines.append('        select(MaterialGroup).where(MaterialGroup.deleted_at.is_(None))')
    lines.append('    )')
    lines.append('    groups = {g.code: g for g in result.scalars().all()}')
    lines.append('    print(f"  📦 Available MaterialGroups: {len(groups)}")')
    lines.append('')
    lines.append('    # Načíst existující MaterialNorms')
    lines.append('    result = await session.execute(')
    lines.append('        select(MaterialNorm).where(MaterialNorm.deleted_at.is_(None))')
    lines.append('    )')
    lines.append('    existing_norms = list(result.scalars().all())')
    lines.append('')
    lines.append('    created_count = 0')
    lines.append('    skipped_count = 0')
    lines.append('    missing_groups = set()')
    lines.append('')
    lines.append('    for w_nr, en_iso, csn, aisi, group_code, note in NORMS_DATA:')
    lines.append('        # Najít MaterialGroup')
    lines.append('        group = groups.get(group_code)')
    lines.append('        if not group:')
    lines.append('            missing_groups.add(group_code)')
    lines.append('            skipped_count += 1')
    lines.append('            continue')
    lines.append('')
    lines.append('        # Check: At least one norm column must be filled')
    lines.append('        if not any([w_nr, en_iso, csn, aisi]):')
    lines.append('            print(f"⚠️  Skipping invalid row: {note} (no norm filled)")')
    lines.append('            skipped_count += 1')
    lines.append('            continue')
    lines.append('')
    lines.append('        # Check duplikát')
    lines.append('        is_duplicate = False')
    lines.append('        for existing in existing_norms:')
    lines.append('            if (existing.material_group_id == group.id and')
    lines.append('                existing.w_nr == w_nr and')
    lines.append('                existing.en_iso == en_iso and')
    lines.append('                existing.csn == csn and')
    lines.append('                existing.aisi == aisi):')
    lines.append('                is_duplicate = True')
    lines.append('                break')
    lines.append('')
    lines.append('        if is_duplicate:')
    lines.append('            skipped_count += 1')
    lines.append('            continue')
    lines.append('')
    lines.append('        # Vytvořit MaterialNorm')
    lines.append('        norm = MaterialNorm(')
    lines.append('            w_nr=w_nr.upper() if w_nr else None,')
    lines.append('            en_iso=en_iso.upper() if en_iso else None,')
    lines.append('            csn=csn.upper() if csn else None,')
    lines.append('            aisi=aisi.upper() if aisi else None,')
    lines.append('            material_group_id=group.id,')
    lines.append('            note=note')
    lines.append('        )')
    lines.append('        session.add(norm)')
    lines.append('        existing_norms.append(norm)')
    lines.append('        created_count += 1')
    lines.append('')
    lines.append('    await session.commit()')
    lines.append('')
    lines.append('    print(f"✅ MaterialNorms seeded: {created_count} created, {skipped_count} skipped")')
    lines.append('')
    lines.append('    if missing_groups:')
    lines.append('        print(f"⚠️  Missing MaterialGroups: {\', \'.join(missing_groups)}")')
    lines.append('')
    lines.append('')
    lines.append('async def main():')
    lines.append('    """Run seed script directly"""')
    lines.append('    async with async_session() as session:')
    lines.append('        await seed_material_norms(session)')
    lines.append('')
    lines.append('')
    lines.append('if __name__ == "__main__":')
    lines.append('    asyncio.run(main())')
    lines.append('')

    # Stats comment at line 12 (after imports)
    stats_line = f'# Stats: {found} materials with norms, {missing} TODO (missing norms)'
    lines.insert(12, stats_line)

    return '\n'.join(lines)


def main():
    print("=" * 100)
    print("GENEROVÁNÍ KOMPLETNÍHO SEED SCRIPTU PRO MATERIAL NORMS")
    print("=" * 100)

    # 1. Extract materials from catalog
    print("\n1️⃣ Načítání materiálů z Excel katalogu...")
    materials = extract_materials_from_catalog()

    if not materials:
        print("❌ Žádné W.Nr. materiály nenalezeny")
        return

    print(f"✅ Nalezeno {len(materials)} unikátních W.Nr. materiálů")

    # 2. Statistics
    found = sum(1 for m in materials if m in MATERIAL_NORMS)
    missing = len(materials) - found
    coverage = (found / len(materials) * 100) if materials else 0

    print(f"\n📊 POKRYTÍ NOREM:")
    print(f"  Celkem materiálů:     {len(materials)}")
    print(f"  S normami:            {found} ({coverage:.1f}%)")
    print(f"  Bez norem (TODO):     {missing}")

    # 3. Show missing materials
    if missing > 0:
        print(f"\n⚠️  Chybějící normy (prvních 20):")
        missing_list = [m for m in sorted(materials.keys()) if m not in MATERIAL_NORMS]
        for m in missing_list[:20]:
            count = materials[m]
            print(f"     {m} ({count}× variant)")
        if len(missing_list) > 20:
            print(f"     ... a dalších {len(missing_list) - 20}")

    # 4. Generate seed script
    print(f"\n2️⃣ Generování seed scriptu...")
    seed_code = generate_seed_script(materials)

    OUTPUT_SEED.write_text(seed_code, encoding='utf-8')

    print(f"✅ Seed script vytvořen: {OUTPUT_SEED}")
    print(f"   Řádků kódu: {len(seed_code.splitlines())}")
    print(f"   Velikost: {len(seed_code)} B")

    # 5. Summary
    print(f"\n" + "=" * 100)
    print("✅ HOTOVO")
    print("=" * 100)
    print(f"\nPoužití:")
    print(f"  python3 {OUTPUT_SEED}")
    print(f"\nDalší kroky:")
    print(f"  1. Zkontroluj vygenerovaný soubor")
    print(f"  2. Doplň chybějící normy pro {missing} materiálů (EN ISO, ČSN, AISI)")
    print(f"  3. Spusť seed script")
    print("=" * 100)


if __name__ == "__main__":
    main()
