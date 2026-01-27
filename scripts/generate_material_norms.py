#!/usr/bin/env python3
"""
Generuj MaterialNorm záznamy pro import

Načte parsovaná data z material_codes_preview.csv,
extrahuje unikátní W.Nr. materiály a doplní k nim:
- ČSN normu
- EN ISO označení
- AISI (pokud existuje)

Výstup: SQL seed pro material_norms tabulku
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from typing import Dict, Optional

# Paths
PARSED_CSV = Path(__file__).parent.parent / "temp" / "material_codes_preview.csv"
OUTPUT_SQL = Path(__file__).parent.parent / "temp" / "material_norms_seed.sql"


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
    "1.0050": {
        "en_iso": "E295",
        "csn": "11500",
        "aisi": None,
        "note": "Ocel konstrukční"
    },
    "1.0503": {
        "en_iso": "C45",
        "csn": "12050",
        "aisi": "1045",
        "note": "Ocel konstrukční uhlíková"
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
    "1.0330": {
        "en_iso": "DC01",
        "csn": "11320",
        "aisi": None,
        "note": "Ocel pro tváření za studena"
    },

    # ===== OCELI AUTOMATOVÉ (1.1xxx) =====
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

    # ===== OCELI NÁSTROJOVÉ (1.2xxx) =====
    "1.2311": {
        "en_iso": "40CrMnMo7",
        "csn": "19436",
        "aisi": "P20",
        "note": "Ocel nástrojová pro formy"
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
    "1.2842": {
        "en_iso": "90MnCrV8",
        "csn": "19830",
        "aisi": "O2",
        "note": "Ocel nástrojová na olej"
    },

    # ===== OCELI NÍZKOLEGOVANÉ (1.3xxx, 1.5xxx, 1.6xxx, 1.7xxx) =====
    "1.5217": {
        "en_iso": "55NiCrMoV7",
        "csn": "15330",
        "aisi": None,
        "note": "Ocel nízkolegovaná pro tepelné zpracování"
    },
    "1.6582": {
        "en_iso": "34CrNiMo6",
        "csn": "15330",
        "aisi": "4340",
        "note": "Ocel nízkolegovaná"
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

    # ===== NEREZ (1.4xxx) =====
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
    "1.4571": {
        "en_iso": "X6CrNiMoTi17-12-2",
        "csn": "17352",
        "aisi": "316Ti",
        "note": "Nerez stabilizovaná titanem"
    },
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
    "1.4057": {
        "en_iso": "X17CrNi16-2",
        "csn": "17031",
        "aisi": "431",
        "note": "Nerez feritická"
    },
    "1.4418": {
        "en_iso": "X4CrNiMo16-5-1",
        "csn": "17349",
        "aisi": None,
        "note": "Nerez martenzitická"
    },

    # ===== MĚĎ A SLITINY (2.0xxx) =====
    "2.0060": {
        "en_iso": "Cu-ETP",
        "csn": "42301",
        "aisi": "C11000",
        "note": "Měď elektrolytická"
    },
    "2.0401": {
        "en_iso": "SF-Cu",
        "csn": "42301",
        "aisi": "C10200",
        "note": "Měď bez kyslíku"
    },

    # ===== MOSAZ (2.1xxx) =====
    "2.1053": {
        "en_iso": "CuZn37",
        "csn": "42320",
        "aisi": "C27400",
        "note": "Mosaz"
    },
    "2.1182": {
        "en_iso": "CuZn40Pb2",
        "csn": "42328",
        "aisi": "C38500",
        "note": "Mosaz automatová"
    },

    # ===== OCELI KONSTRUKČNÍ (pokračování) =====
    "1.0039": {
        "en_iso": "S235JRH",
        "csn": "11373",
        "aisi": None,
        "note": "Ocel konstrukční pro trubky"
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
    "1.0501": {
        "en_iso": "C35",
        "csn": "12035",
        "aisi": "1035",
        "note": "Ocel uhlíková"
    },
    "1.0535": {
        "en_iso": "C45E",
        "csn": "12050.4",
        "aisi": "1045",
        "note": "Ocel uhlíková kalitelná"
    },
    "1.0762": {
        "en_iso": "C75",
        "csn": "12075",
        "aisi": "1075",
        "note": "Ocel uhlíková pružinová"
    },

    # ===== OCELI AUTOMATOVÉ (pokračování) =====
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
    "1.1545": {
        "en_iso": "9SMn36",
        "csn": "12040",
        "aisi": None,
        "note": "Ocel automatová"
    },

    # ===== OCELI NÁSTROJOVÉ (pokračování) =====
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
    "1.2316": {
        "en_iso": "X38CrMo16",
        "csn": "19436",
        "aisi": "420",
        "note": "Ocel nástrojová korozivzdorná"
    },
    "1.2721": {
        "en_iso": "50NiCr13",
        "csn": None,
        "aisi": None,
        "note": "Ocel nástrojová"
    },
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

    # ===== NEREZ (pokračování) =====
    "1.4034": {
        "en_iso": "X46Cr13",
        "csn": "17027",
        "aisi": "420",
        "note": "Nerez martenzitická"
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
    "1.4878": {
        "en_iso": "X12CrNiTi18-9",
        "csn": "17249",
        "aisi": "321H",
        "note": "Nerez žáropevná"
    },

    # ===== OCELI LEGOVANÉ (pokračování) =====
    "1.5122": {
        "en_iso": "20MnCr5",
        "csn": "14220",
        "aisi": "5120",
        "note": "Ocel cementační"
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
    "1.7102": {
        "en_iso": "16MnCrS5",
        "csn": "14220",
        "aisi": None,
        "note": "Ocel cementační"
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

    # ===== MĚĎ A SLITINY (pokračování) =====
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

    # ===== MOSAZ (pokračování) =====
    "2.1030": {
        "en_iso": "CuZn39Pb3",
        "csn": "42328",
        "aisi": "C38500",
        "note": "Mosaz automatová"
    },
    "2.1090": {
        "en_iso": "CuZn40Mn2Fe1",
        "csn": "42328",
        "aisi": None,
        "note": "Mosaz speciální"
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


def extract_unique_materials() -> Dict[str, int]:
    """Extrahuj unikátní W.Nr. materiály z parsovaných dat"""

    if not PARSED_CSV.exists():
        print(f"❌ Parsovaná data nenalezena: {PARSED_CSV}")
        print("   Spusť nejdřív: python scripts/analyze_material_codes.py")
        return {}

    df = pd.read_csv(PARSED_CSV)

    # Filter only metal materials (have W.Nr. format)
    metal_df = df[df['material_type'] == 'metal']

    # Extract materials with format X.YYYY
    wnr_materials = metal_df[metal_df['material'].str.contains(r'^\d\.\d{4}', na=False)]

    # Count occurrences
    material_counts = wnr_materials['material'].value_counts().to_dict()

    return material_counts


def generate_sql_seed(materials: Dict[str, int]) -> str:
    """Generuj SQL seed pro material_norms tabulku"""

    sql_lines = []
    sql_lines.append("-- Material Norms Seed (auto-generated)")
    sql_lines.append("-- Generated: 2026-01-27")
    sql_lines.append("-- Source: DIN EN 10027, ČSN EN 10027, AISI standards\n")
    sql_lines.append("-- Usage: Run via sqlite3 or SQL migration\n")

    # Track material_group_id mapping (simplified - assume they exist)
    group_mapping = {
        "1.0": 1,  # Ocel konstrukční
        "1.1": 2,  # Ocel automatová
        "1.2": 3,  # Ocel nástrojová
        "1.3": 4,  # Ocel nízkolegovaná
        "1.4": 5,  # Nerez
        "1.5": 4,  # Ocel nízkolegovaná
        "1.6": 4,  # Ocel nízkolegovaná
        "1.7": 4,  # Ocel nízkolegovaná
        "2.0": 6,  # Měď
        "2.1": 7,  # Mosaz
        "2.2": 8,  # Bronz
        "3.0": 9,  # Hliník
        "3.1": 9,
        "3.2": 9,
        "3.3": 9,
        "3.4": 9,
    }

    found_count = 0
    missing_count = 0

    sql_lines.append("INSERT INTO material_norms (w_nr, en_iso, csn, aisi, material_group_id, note, version, created_at, updated_at)")
    sql_lines.append("VALUES")

    inserts = []

    for material, count in sorted(materials.items()):
        if material in MATERIAL_NORMS:
            norm = MATERIAL_NORMS[material]

            # Determine material_group_id
            prefix = material[:3]  # "1.0", "1.4", etc.
            group_id = group_mapping.get(prefix, 1)

            # Format values (NULL for None)
            w_nr = f"'{material}'"
            en_iso = f"'{norm['en_iso']}'" if norm['en_iso'] else "NULL"
            csn = f"'{norm['csn']}'" if norm['csn'] else "NULL"
            aisi = f"'{norm['aisi']}'" if norm['aisi'] else "NULL"
            note = f"'{norm['note']}'" if norm['note'] else "NULL"

            insert = f"  ({w_nr}, {en_iso}, {csn}, {aisi}, {group_id}, {note}, 1, datetime('now'), datetime('now'))"
            inserts.append(insert)
            found_count += 1
        else:
            missing_count += 1

    sql_lines.append(",\n".join(inserts) + ";")

    sql_lines.append(f"\n-- Stats:")
    sql_lines.append(f"--   Found in database:  {found_count}")
    sql_lines.append(f"--   Missing (TODO):     {missing_count}")

    return "\n".join(sql_lines)


def generate_missing_report(materials: Dict[str, int]) -> str:
    """Generuj report chybějících norem"""

    lines = []
    lines.append("=" * 80)
    lines.append("CHYBĚJÍCÍ MATERIÁLOVÉ NORMY")
    lines.append("=" * 80)
    lines.append("")
    lines.append("Následující W.Nr. materiály z katalogu nemají doplněné normy:")
    lines.append("")

    missing = []
    for material, count in sorted(materials.items()):
        if material not in MATERIAL_NORMS:
            missing.append((material, count))

    if missing:
        lines.append(f"{'W.Nr.':<12s} | {'Počet variant':>14s} | Poznámka")
        lines.append("-" * 80)

        for material, count in missing:
            lines.append(f"{material:<12s} | {count:>14d}× | TODO: doplnit EN ISO, ČSN, AISI")

        lines.append("")
        lines.append(f"Celkem chybí: {len(missing)} materiálů")
    else:
        lines.append("✅ Všechny materiály mají doplněné normy!")

    lines.append("")
    lines.append("=" * 80)

    return "\n".join(lines)


def main():
    print("=" * 80)
    print("GENEROVÁNÍ MATERIAL NORMS SEED")
    print("=" * 80)

    # 1. Extract unique materials
    print("\n1️⃣ Načítání parsovaných materiálů...")
    materials = extract_unique_materials()

    if not materials:
        print("❌ Žádné materiály nenalezeny")
        return

    print(f"✅ Nalezeno {len(materials)} unikátních W.Nr. materiálů")

    # 2. Generate SQL seed
    print("\n2️⃣ Generování SQL seed...")
    sql_seed = generate_sql_seed(materials)

    OUTPUT_SQL.parent.mkdir(exist_ok=True)
    OUTPUT_SQL.write_text(sql_seed, encoding='utf-8')

    print(f"✅ SQL seed uložen: {OUTPUT_SQL}")

    # 3. Generate missing report
    print("\n3️⃣ Kontrola chybějících norem...")
    missing_report = generate_missing_report(materials)
    print(missing_report)

    # 4. Summary
    found = sum(1 for m in materials if m in MATERIAL_NORMS)
    missing = len(materials) - found
    coverage = (found / len(materials) * 100) if materials else 0

    print(f"\n📊 SOUHRN:")
    print(f"  Celkem materiálů:     {len(materials)}")
    print(f"  S normami:            {found} ({coverage:.1f}%)")
    print(f"  Bez norem (TODO):     {missing}")

    print("\n✅ HOTOVO")
    print(f"   SQL seed: {OUTPUT_SQL}")
    print(f"   Použití: sqlite3 gestima.db < {OUTPUT_SQL}")
    print("=" * 80)


if __name__ == "__main__":
    main()
