"""
Extract unique material norm combinations from Infor SLItems.

This script loads all items from Infor and extracts unique combinations of:
- RybMatNormaNazev1 (W.Nr./Werkstoffnummer)
- RybMatNormaNazev2 (ČSN)
- RybMatNormaNazev3 (EN ISO)
- RybMatNormaNazev4 (AISI)

Then it maps them to MaterialGroup based on heuristics and imports to material_norms.

Usage:
    python scripts/extract_material_norms_from_infor.py [--analyze-only] [--import]
"""

import asyncio
import os
import sys
import csv
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()


# MaterialGroup mapping rules (GESTIMA-specific)
#
# OCEL: Mapujeme podle ČSN (primární zdroj)
# - ČSN 11xxx = Ocel konstrukční (kromě 11109 = automatová)
# - ČSN 12xxx = Ocel konstrukční
# - ČSN 13xxx = Ocel legovaná (pružinová)
# - ČSN 14xxx = Ocel legovaná (cementační/ložisková)
# - ČSN 15xxx = Ocel legovaná (nitridační)
# - ČSN 16xxx = Ocel legovaná (ložisková)
# - ČSN 17xxx = Nerez
# - ČSN 19xxx = Ocel nástrojová
#
# NEŽELEZNÉ KOVY: Mapujeme podle W.Nr.
# - W.Nr. 2.0xxx = Měď
# - W.Nr. 2.1xxx+ = Mosaz
# - W.Nr. 3.xxxx = Hliník

# W.Nr mapping - pouze pro neželezné kovy
WNR_MAPPING = {
    # 2.0xxx = Měď čistá
    "2.0": (2, "Měď"),
    # 2.1xxx+ = Mosaz (slitiny Cu-Zn)
    "2.1": (3, "Mosaz"),
    "2.2": (3, "Mosaz"),
    "2.3": (3, "Mosaz"),
    "2.4": (3, "Mosaz"),
    # 3.xxxx = Hliník
    "3.": (1, "Hliník"),
}

# ČSN mapping - primární zdroj pro OCEL
# Speciální případy (exact match) mají přednost
CSN_EXACT = {
    "11109": (4, "Ocel automatová"),  # 11SMn30 - automatová
}

CSN_MAPPING = {
    "11": (5, "Ocel konstrukční"),    # 11xxx = konstrukční nelegovaná (S235, DC01, E295...)
    "12": (5, "Ocel konstrukční"),    # 12xxx = konstrukční k zušlechťování (C35, C45, C55)
    "13": (6, "Ocel legovaná"),       # 13xxx = pružinová
    "14": (6, "Ocel legovaná"),       # 14xxx = cementační/ložisková (100Cr6, 16MnCr5)
    "15": (6, "Ocel legovaná"),       # 15xxx = nitridační (42CrMo4, 51CrV4)
    "16": (6, "Ocel legovaná"),       # 16xxx = ložisková (34CrNiMo6)
    "17": (8, "Nerez"),               # 17xxx = korozivzdorná (X5CrNi18-10)
    "19": (7, "Ocel nástrojová"),     # 19xxx = nástrojová (40CrMnMo7, X153CrMoV12)
}


def determine_material_group(w_nr: str, csn: str, en_iso: str, aisi: str) -> Tuple[Optional[int], str]:
    """
    Determine MaterialGroup based on norm values.

    GESTIMA mapping logic:
    1. W.Nr. 2.xxxx, 3.xxxx → Neželezné kovy (podle W.Nr.)
    2. W.Nr. 1.xxxx (ocel) → mapuj podle ČSN
    3. AISI 3xx, 4xx → Nerez (fallback)

    Returns (group_id, reason_string)
    """
    # 1. NEŽELEZNÉ KOVY: W.Nr. 2.xxxx = Měď/Mosaz, 3.xxxx = Hliník
    if w_nr:
        w_nr_clean = w_nr.strip()
        if w_nr_clean.startswith("2.") or w_nr_clean.startswith("3."):
            for prefix, (group_id, group_name) in WNR_MAPPING.items():
                if w_nr_clean.startswith(prefix):
                    return (group_id, f"W.Nr {w_nr_clean} → {group_name}")

    # 2. OCEL: Mapuj podle ČSN
    if csn:
        csn_clean = csn.strip().replace(" ", "")  # Remove spaces (e.g. "42 3001" → "423001")

        # 2a. Exact match (speciální případy jako 11109 = automatová)
        if csn_clean in CSN_EXACT:
            group_id, group_name = CSN_EXACT[csn_clean]
            return (group_id, f"ČSN {csn_clean} → {group_name}")

        # 2b. Prefix match (11xxx, 12xxx, etc.)
        if len(csn_clean) >= 2:
            prefix = csn_clean[:2]
            if prefix in CSN_MAPPING:
                group_id, group_name = CSN_MAPPING[prefix]
                return (group_id, f"ČSN {csn_clean} → {group_name}")

    # 3. AISI fallback pro nerez (304, 316, 410, etc.)
    if aisi:
        aisi_clean = aisi.strip().upper()
        if aisi_clean.startswith("3") or aisi_clean.startswith("4"):
            return (8, f"AISI {aisi_clean} → Nerez")

    # 4. W.Nr. fallback pro ocel (když chybí ČSN)
    if w_nr:
        w_nr_clean = w_nr.strip()
        if w_nr_clean.startswith("1.2"):
            return (7, f"W.Nr {w_nr_clean} → Ocel nástrojová (fallback)")
        if w_nr_clean.startswith("1.4"):
            return (8, f"W.Nr {w_nr_clean} → Nerez (fallback)")
        if w_nr_clean.startswith("1."):
            return (5, f"W.Nr {w_nr_clean} → Ocel konstrukční (fallback)")

    return (None, "UNKNOWN - manual review needed")


async def load_norms_from_infor() -> List[Dict]:
    """Load all unique norm combinations from Infor SLItems."""
    from app.services.infor_api_client import InforAPIClient

    base_url = os.getenv("INFOR_API_URL", "")
    config = os.getenv("INFOR_CONFIG", "Test")
    username = os.getenv("INFOR_USERNAME", "")
    password = os.getenv("INFOR_PASSWORD", "")

    if not all([base_url, username, password]):
        print("❌ Missing Infor credentials in .env file!")
        print("Required: INFOR_API_URL, INFOR_USERNAME, INFOR_PASSWORD")
        return []

    print(f"🔌 Connecting to Infor API (config={config})...")

    client = InforAPIClient(
        base_url=base_url,
        config=config,
        username=username,
        password=password,
        verify_ssl=False
    )

    properties = [
        "Item",               # Master - obsahuje W.Nr. na začátku (např. 1.4301-D20-xxx)
        "RybMatNormaNazev1",  # W.Nr (pomocné)
        "RybMatNormaNazev2",  # ČSN
        "RybMatNormaNazev3",  # EN ISO
        "RybMatNormaNazev4",  # AISI
    ]

    # Load materials separately by W.Nr. prefix (pagination bug workaround)
    # Split 1.xxxx into sub-prefixes to get all steel types
    prefixes = [
        "1.0",   # Konstrukční nelegovaná (1.00xx-1.09xx)
        "1.1",   # Konstrukční k zušlechťování (1.1xxx)
        "1.2",   # Nástrojová (1.2xxx)
        "1.3",   # Speciální (1.3xxx - rychlořezná, ložisková)
        "1.4",   # Nerez (1.4xxx)
        "1.5",   # Legovaná (1.5xxx)
        "1.6",   # Legovaná (1.6xxx)
        "1.7",   # Legovaná (1.7xxx)
        "1.8",   # Legovaná (1.8xxx)
        "2.",    # Měď/Mosaz
        "3.",    # Hliník
    ]
    MAX_PER_PREFIX = 5000  # Reasonable limit per sub-prefix

    all_items = []

    for prefix in prefixes:
        filter_expr = f"FamilyCode = 'Materiál' AND Item LIKE '{prefix}%'"
        print(f"📦 Loading materials starting with '{prefix}' ...")

        prefix_items = []
        bookmark = None
        page = 0

        while True:
            page += 1
            result = await client.load_collection(
                ido_name="SLItems",
                properties=properties,
                filter=filter_expr,
                record_cap=500,
                bookmark=bookmark,
                distinct=True
            )

            items = result.get("data", [])
            prefix_items.extend(items)

            print(f"   Page {page}: +{len(items)} records (prefix total: {len(prefix_items)})")

            # Safety limit per prefix
            if len(prefix_items) >= MAX_PER_PREFIX:
                print(f"   ⚠️ Limit {MAX_PER_PREFIX} reached for prefix '{prefix}'")
                break

            if not result.get("has_more") or not result.get("bookmark") or len(items) == 0:
                break

            bookmark = result.get("bookmark")

        print(f"   ✓ Prefix '{prefix}': {len(prefix_items)} items")
        all_items.extend(prefix_items)

    print(f"\n📊 TOTAL: {len(all_items)} materials loaded")
    return all_items


def analyze_norms(items: List[Dict]) -> Dict:
    """Analyze norm data and create mapping.

    W.Nr. is extracted from Item field (e.g. "1.4301-D20-xxx" → "1.4301")
    RybMatNormaNazev1-4 provide additional norm mappings (ČSN, EN ISO, AISI)
    """

    # Deduplicate by W.Nr. (primary key)
    unique_norms = {}

    for item in items:
        # Extract W.Nr. from Item field (first part before dash)
        # e.g. "1.4301-D20-xxx" → "1.4301"
        item_code = (item.get("Item") or "").strip()
        w_nr_from_item = item_code.split("-")[0] if item_code else ""

        # Also get from RybMatNormaNazev1 as fallback
        w_nr_ryb = (item.get("RybMatNormaNazev1") or "").strip()

        # Use Item-extracted W.Nr. as primary
        w_nr = w_nr_from_item or w_nr_ryb

        csn = (item.get("RybMatNormaNazev2") or "").strip()
        en_iso = (item.get("RybMatNormaNazev3") or "").strip()
        aisi = (item.get("RybMatNormaNazev4") or "").strip()

        # Skip if no W.Nr.
        if not w_nr:
            continue

        # Create unique key based on W.Nr. (primary identifier)
        key = w_nr

        if key not in unique_norms:
            group_id, reason = determine_material_group(w_nr, csn, en_iso, aisi)
            unique_norms[key] = {
                "w_nr": w_nr,
                "csn": csn or None,
                "en_iso": en_iso or None,
                "aisi": aisi or None,
                "material_group_id": group_id,
                "mapping_reason": reason
            }
        else:
            # Update with additional norm data if found (fill in blanks)
            existing = unique_norms[key]
            if csn and not existing["csn"]:
                existing["csn"] = csn
            if en_iso and not existing["en_iso"]:
                existing["en_iso"] = en_iso
            if aisi and not existing["aisi"]:
                existing["aisi"] = aisi

    return unique_norms


def print_analysis(unique_norms: Dict):
    """Print analysis of norm data."""

    print("\n" + "=" * 100)
    print(f"📊 MATERIAL NORMS ANALYSIS ({len(unique_norms)} unique combinations)")
    print("=" * 100)

    # Group by material group
    by_group = defaultdict(list)
    unmapped = []

    for key, data in unique_norms.items():
        if data["material_group_id"]:
            by_group[data["material_group_id"]].append(data)
        else:
            unmapped.append(data)

    # Print by group
    group_names = {
        1: "Hliník",
        2: "Měď",
        3: "Mosaz",
        4: "Ocel automatová",
        5: "Ocel konstrukční",
        6: "Ocel legovaná",
        7: "Ocel nástrojová",
        8: "Nerez",
        9: "Plasty",
    }

    for group_id in sorted(by_group.keys()):
        norms = by_group[group_id]
        print(f"\n🏷️  {group_names.get(group_id, 'Unknown')} (ID={group_id}): {len(norms)} norms")
        print("-" * 80)

        for norm in norms[:10]:  # Show first 10
            print(f"   W.Nr: {norm['w_nr'] or '-':15} | "
                  f"ČSN: {norm['csn'] or '-':10} | "
                  f"EN: {norm['en_iso'] or '-':20} | "
                  f"AISI: {norm['aisi'] or '-':10}")

        if len(norms) > 10:
            print(f"   ... and {len(norms) - 10} more")

    # Unmapped
    if unmapped:
        print(f"\n⚠️  UNMAPPED ({len(unmapped)} norms need manual review):")
        print("-" * 80)
        for norm in unmapped[:20]:
            print(f"   W.Nr: {norm['w_nr'] or '-':15} | "
                  f"ČSN: {norm['csn'] or '-':10} | "
                  f"EN: {norm['en_iso'] or '-':20} | "
                  f"AISI: {norm['aisi'] or '-':10}")


def export_to_csv(unique_norms: Dict, filename: str = "material_norms_export.csv"):
    """Export norm data to CSV for review."""

    filepath = os.path.join(os.path.dirname(__file__), filename)

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "w_nr", "csn", "en_iso", "aisi",
            "material_group_id", "mapping_reason"
        ])

        for key, data in sorted(unique_norms.items()):
            writer.writerow([
                data["w_nr"] or "",
                data["csn"] or "",
                data["en_iso"] or "",
                data["aisi"] or "",
                data["material_group_id"] or "",
                data["mapping_reason"]
            ])

    print(f"\n✅ Exported to {filepath}")


async def import_to_database(unique_norms: Dict):
    """Import norms to material_norms table."""

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.material_norm import MaterialNorm

    # Connect to database
    engine = create_engine("sqlite:///gestima.db")
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Check existing norms
        existing = session.query(MaterialNorm).count()
        print(f"\n📊 Current material_norms count: {existing}")

        imported = 0
        skipped = 0

        for key, data in unique_norms.items():
            if not data["material_group_id"]:
                skipped += 1
                continue

            # Check if exists
            exists = session.query(MaterialNorm).filter(
                MaterialNorm.w_nr == data["w_nr"],
                MaterialNorm.csn == data["csn"],
                MaterialNorm.en_iso == data["en_iso"],
                MaterialNorm.aisi == data["aisi"],
            ).first()

            if exists:
                skipped += 1
                continue

            # Create new
            norm = MaterialNorm(
                w_nr=data["w_nr"],
                csn=data["csn"],
                en_iso=data["en_iso"],
                aisi=data["aisi"],
                material_group_id=data["material_group_id"],
                note=f"Imported from Infor: {data['mapping_reason']}"
            )
            session.add(norm)
            imported += 1

        session.commit()

        print(f"✅ Imported: {imported} norms")
        print(f"⏭️  Skipped: {skipped} (already exist or unmapped)")

    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Extract and import material norms from Infor")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze, don't import")
    parser.add_argument("--import", dest="do_import", action="store_true", help="Import to database")
    parser.add_argument("--csv", type=str, help="Load from CSV file instead of Infor")
    args = parser.parse_args()

    if args.csv:
        # Load from CSV
        print(f"📄 Loading from CSV: {args.csv}")
        items = []
        with open(args.csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                items.append({
                    "RybMatNormaNazev1": row.get("w_nr") or row.get("RybMatNormaNazev1"),
                    "RybMatNormaNazev2": row.get("csn") or row.get("RybMatNormaNazev2"),
                    "RybMatNormaNazev3": row.get("en_iso") or row.get("RybMatNormaNazev3"),
                    "RybMatNormaNazev4": row.get("aisi") or row.get("RybMatNormaNazev4"),
                })
    else:
        # Load from Infor
        items = await load_norms_from_infor()

    if not items:
        print("❌ No data loaded!")
        return

    # Analyze
    unique_norms = analyze_norms(items)
    print_analysis(unique_norms)

    # Export to CSV for review
    export_to_csv(unique_norms)

    # Import if requested
    if args.do_import:
        await import_to_database(unique_norms)
    else:
        print("\n💡 To import to database, run with --import flag")


if __name__ == "__main__":
    asyncio.run(main())
