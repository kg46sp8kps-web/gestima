"""GESTIMA - Katalog výběru nástrojů pro CNC obrábění

Reference: Sandvik Coromant, Iscar, Kennametal, Walter Tools
Materiálové skupiny: ISO P/M/K/N/H (odvozeno z interních 8-digit kódů)

Struktura: {(operation_type, operation, iso_group): [tool_specs]}
Každý tool_spec obsahuje: dia_min, dia_max, tool_code, tool_name, notes

Design: Data-driven, NO hardcoded tool assignment!
Pattern: Copy structure from cutting_conditions_catalog.py
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Import canonical material mapping (Single Source of Truth)
from app.services.cutting_conditions_catalog import MATERIAL_GROUP_MAP


def get_iso_group_from_material(material_group: str) -> str:
    """
    Convert 8-digit material code to ISO group (P/M/K/N/H).

    Uses canonical mapping from cutting_conditions_catalog.MATERIAL_GROUP_MAP
    to ensure consistency across all services.

    Args:
        material_group: 8-digit code (e.g., "20910004")

    Returns:
        ISO group: P, M, K, N, or H (default P if unknown)
    """
    material_info = MATERIAL_GROUP_MAP.get(material_group)
    if material_info:
        return material_info["iso"]

    logger.warning(f"Material group {material_group} not mapped, defaulting to ISO P")
    return "P"


# ====================================================================
# TOOL CATALOG
# ====================================================================
# Key: (operation_type, operation, iso_group)
# Value: List of tool specs sorted by diameter range
#
# Tool spec fields:
#   - dia_min/dia_max: diameter range [mm]
#   - tool_code: unique identifier (e.g., "CNMG_INSERT", "HSS_DRILL_8")
#   - tool_name: display name (e.g., "CNMG hrubovací nůž")
#   - notes: additional info (optional)
#
# Sources:
#   Sandvik Coromant - Main catalog 2024
#   Iscar - Machining catalog
#   Kennametal - Tooling systems
#   Walter Tools - Tiger-tec catalog
# ====================================================================

def _build_tool_catalog() -> Dict[tuple, List[Dict[str, Any]]]:
    """Build complete tool selection catalog."""
    catalog = {}

    # ========================================================================
    # TURNING TOOLS
    # ========================================================================

    # --- ROUGHING (hrubovani) ---
    # Reference: Sandvik CNMG, Iscar CNMG, Kennametal KC9xxx series
    # ISO P (Steel) - most common
    catalog[("turning", "hrubovani", "P")] = [
        {
            "dia_min": 10,
            "dia_max": 999,
            "tool_code": "CNMG_INSERT",
            "tool_name": "CNMG hrubovací nůž",
            "notes": "Standard roughing insert 80° diamond, GC4325 coating",
        },
    ]

    catalog[("turning", "hrubovani", "M")] = [
        {
            "dia_min": 10,
            "dia_max": 999,
            "tool_code": "CNMG_INOX",
            "tool_name": "CNMG nerez nůž",
            "notes": "Stainless steel grade, GC2220 coating",
        },
    ]

    catalog[("turning", "hrubovani", "N")] = [
        {
            "dia_min": 10,
            "dia_max": 999,
            "tool_code": "CNMG_ALU",
            "tool_name": "CNMG nůž pro hliník",
            "notes": "Sharp edge for non-ferrous, GC1115 grade",
        },
    ]

    # --- FINISHING (dokoncovani) ---
    # Reference: Sandvik DNMG, WNMG for precision
    catalog[("turning", "dokoncovani", "P")] = [
        {
            "dia_min": 10,
            "dia_max": 999,
            "tool_code": "DNMG_INSERT",
            "tool_name": "DNMG dokončovací nůž",
            "notes": "55° diamond insert, fine finish Ra 1.6-3.2, GC4315 coating",
        },
    ]

    catalog[("turning", "dokoncovani", "M")] = [
        {
            "dia_min": 10,
            "dia_max": 999,
            "tool_code": "DNMG_INOX",
            "tool_name": "DNMG nerez dokončovací",
            "notes": "Stainless finish grade, GC2220",
        },
    ]

    catalog[("turning", "dokoncovani", "N")] = [
        {
            "dia_min": 10,
            "dia_max": 999,
            "tool_code": "DNMG_ALU",
            "tool_name": "DNMG dokončovací hliník",
            "notes": "Polished edge, GC1115",
        },
    ]

    # ========================================================================
    # DRILLING TOOLS
    # ========================================================================

    # --- CENTER DRILLING (navrtani) ---
    catalog[("drilling", "navrtani", "P")] = [
        {
            "dia_min": 1,
            "dia_max": 5,
            "tool_code": "CENTER_DRILL_3",
            "tool_name": "Navrták Ø3 HSS",
            "notes": "60° center drill, DIN 333",
        },
    ]

    # --- DRILLING (vrtani) ---
    # ISO P (Steel) - HSS for small, carbide for mid, indexable for large
    catalog[("drilling", "vrtani", "P")] = [
        {
            "dia_min": 1,
            "dia_max": 10,
            "tool_code": "HSS_DRILL",
            "tool_name": "Vrták HSS",
            "notes": "HSS TiN coated, DIN 338, jobber length",
        },
        {
            "dia_min": 10,
            "dia_max": 20,
            "tool_code": "CARBIDE_DRILL",
            "tool_name": "Vrták VHM",
            "notes": "Solid carbide drill, TiAlN coating, internal coolant",
        },
        {
            "dia_min": 20,
            "dia_max": 40,
            "tool_code": "INDEX_DRILL",
            "tool_name": "Vrták s výměnnými břity",
            "notes": "Indexable drill (Sandvik CoroDrill, Iscar SumoCham)",
        },
        {
            "dia_min": 40,
            "dia_max": 100,
            "tool_code": "INDEX_DRILL_LARGE",
            "tool_name": "Vrták indexable Ø40+",
            "notes": "Large diameter indexable, modular system",
        },
    ]

    catalog[("drilling", "vrtani", "M")] = [
        {
            "dia_min": 1,
            "dia_max": 10,
            "tool_code": "HSS_DRILL_INOX",
            "tool_name": "Vrták HSS nerez",
            "notes": "HSS-Co 5%, split point",
        },
        {
            "dia_min": 10,
            "dia_max": 20,
            "tool_code": "CARBIDE_DRILL_INOX",
            "tool_name": "Vrták VHM nerez",
            "notes": "Solid carbide, AlTiN coating, 130° point",
        },
        {
            "dia_min": 20,
            "dia_max": 40,
            "tool_code": "INDEX_DRILL_INOX",
            "tool_name": "Vrták indexable nerez",
            "notes": "Stainless grade inserts",
        },
    ]

    catalog[("drilling", "vrtani", "N")] = [
        {
            "dia_min": 1,
            "dia_max": 10,
            "tool_code": "HSS_DRILL_ALU",
            "tool_name": "Vrták HSS hliník",
            "notes": "Polished flutes, 118° point",
        },
        {
            "dia_min": 10,
            "dia_max": 20,
            "tool_code": "CARBIDE_DRILL_ALU",
            "tool_name": "Vrták VHM hliník",
            "notes": "Sharp cutting edge, high helix",
        },
        {
            "dia_min": 20,
            "dia_max": 40,
            "tool_code": "INDEX_DRILL_ALU",
            "tool_name": "Vrták indexable hliník",
            "notes": "Non-ferrous grade inserts",
        },
    ]

    # --- DEEP DRILLING (vrtani_hluboke) ---
    catalog[("drilling", "vrtani_hluboke", "P")] = [
        {
            "dia_min": 3,
            "dia_max": 20,
            "tool_code": "DEEP_DRILL_GUN",
            "tool_name": "Dělovka",
            "notes": "Gun drill for depth >4×D, high-pressure coolant",
        },
        {
            "dia_min": 20,
            "dia_max": 50,
            "tool_code": "DEEP_DRILL_BTA",
            "tool_name": "BTA vrtání",
            "notes": "BTA system for large deep holes",
        },
    ]

    # --- REAMING (vystruzovani) ---
    catalog[("drilling", "vystruzovani", "P")] = [
        {
            "dia_min": 3,
            "dia_max": 20,
            "tool_code": "HSS_REAMER",
            "tool_name": "Výstružník HSS",
            "notes": "Machine reamer, tolerance H7, Ra 1.6",
        },
        {
            "dia_min": 20,
            "dia_max": 50,
            "tool_code": "CARBIDE_REAMER",
            "tool_name": "Výstružník VHM",
            "notes": "Solid carbide, tolerance H7, Ra 0.8-1.6",
        },
    ]

    # ========================================================================
    # THREADING TOOLS
    # ========================================================================

    # --- EXTERNAL THREADING (zavitovani OD) ---
    catalog[("threading", "zavitovani", "P")] = [
        {
            "dia_min": 6,
            "dia_max": 100,
            "tool_code": "THREAD_INSERT_OD",
            "tool_name": "Závitový nůž vnější",
            "notes": "Threading insert (Sandvik 266, Iscar Penta), ISO metric",
        },
    ]

    # --- INTERNAL THREADING (zavitovani ID) ---
    catalog[("threading", "zavitovani_id", "P")] = [
        {
            "dia_min": 8,
            "dia_max": 50,
            "tool_code": "THREAD_INSERT_ID",
            "tool_name": "Závitový nůž vnitřní",
            "notes": "Internal threading insert",
        },
    ]

    # --- TAPPING (zavit_tap) ---
    catalog[("threading", "zavit_tap", "P")] = [
        {
            "dia_min": 3,
            "dia_max": 16,
            "tool_code": "HSS_TAP",
            "tool_name": "Závitník HSS",
            "notes": "HSS-E machine tap, DIN 371/376, blind or through hole",
        },
        {
            "dia_min": 16,
            "dia_max": 30,
            "tool_code": "CARBIDE_TAP",
            "tool_name": "Závitník VHM",
            "notes": "Solid carbide tap for high-speed tapping",
        },
    ]

    catalog[("threading", "zavit_tap", "M")] = [
        {
            "dia_min": 3,
            "dia_max": 16,
            "tool_code": "HSS_TAP_INOX",
            "tool_name": "Závitník HSS nerez",
            "notes": "HSS-Co tap for stainless, TiCN coating",
        },
    ]

    # ========================================================================
    # GROOVING & PARTING
    # ========================================================================

    # --- GROOVING (zapichovani) ---
    catalog[("grooving", "zapichovani", "P")] = [
        {
            "dia_min": 10,
            "dia_max": 200,
            "tool_code": "GROOVING_INSERT",
            "tool_name": "Zapichovací nůž",
            "notes": "Grooving insert (Sandvik CoroCut, Iscar DGN), width 2-6mm",
        },
    ]

    # --- PARTING OFF (upichnuti) ---
    catalog[("parting", "upichnuti", "P")] = [
        {
            "dia_min": 10,
            "dia_max": 80,
            "tool_code": "PARTING_INSERT",
            "tool_name": "Upichovací nůž",
            "notes": "Parting insert (Sandvik Q-Cut, Iscar Tang-Grip), width 3-5mm",
        },
    ]

    # ========================================================================
    # MILLING TOOLS (2.5D)
    # ========================================================================

    # --- FACE MILLING (planovani) ---
    catalog[("milling", "planovani", "P")] = [
        {
            "dia_min": 50,
            "dia_max": 150,
            "tool_code": "FACE_MILL",
            "tool_name": "Čelní fréza",
            "notes": "Face mill (Sandvik CoroMill 390, Iscar HELi2000), 6-10 inserts",
        },
    ]

    # --- ROUGHING MILLING (hrubovani) ---
    catalog[("milling", "hrubovani", "P")] = [
        {
            "dia_min": 6,
            "dia_max": 12,
            "tool_code": "ENDMILL_6",
            "tool_name": "Válcová fréza Ø6",
            "notes": "Solid carbide end mill, 4-flute, TiAlN coating",
        },
        {
            "dia_min": 12,
            "dia_max": 20,
            "tool_code": "ENDMILL_12",
            "tool_name": "Válcová fréza Ø12",
            "notes": "Solid carbide end mill, 4-flute, roughing",
        },
        {
            "dia_min": 20,
            "dia_max": 40,
            "tool_code": "ENDMILL_16",
            "tool_name": "Válcová fréza Ø16",
            "notes": "Solid carbide or indexable end mill",
        },
        {
            "dia_min": 40,
            "dia_max": 100,
            "tool_code": "ENDMILL_INDEX",
            "tool_name": "Fréza indexable Ø40+",
            "notes": "Indexable end mill (Walter Xtra-tec, Sandvik CoroMill)",
        },
    ]

    catalog[("milling", "hrubovani", "N")] = [
        {
            "dia_min": 6,
            "dia_max": 12,
            "tool_code": "ENDMILL_6_ALU",
            "tool_name": "Válcová fréza Ø6 hliník",
            "notes": "2-3 flute, polished, high helix 45°",
        },
        {
            "dia_min": 12,
            "dia_max": 20,
            "tool_code": "ENDMILL_12_ALU",
            "tool_name": "Válcová fréza Ø12 hliník",
            "notes": "3-flute, optimized for aluminum",
        },
    ]

    # --- FINISHING MILLING (dokoncovani) ---
    catalog[("milling", "dokoncovani", "P")] = [
        {
            "dia_min": 6,
            "dia_max": 12,
            "tool_code": "ENDMILL_6_FINISH",
            "tool_name": "Válcová fréza Ø6 dokončovací",
            "notes": "6-flute ball nose or flat end, Ra 1.6",
        },
        {
            "dia_min": 12,
            "dia_max": 20,
            "tool_code": "ENDMILL_12_FINISH",
            "tool_name": "Válcová fréza Ø12 dokončovací",
            "notes": "6-flute, fine finish coating",
        },
    ]

    # --- SLOTTING (drazkovani) ---
    catalog[("milling", "drazkovani", "P")] = [
        {
            "dia_min": 3,
            "dia_max": 20,
            "tool_code": "SLOT_CUTTER",
            "tool_name": "Drážkovací fréza",
            "notes": "Slot cutter, 2-flute, center cutting",
        },
    ]

    # --- POCKETING (pocket_rough / pocket_finish) ---
    # Uses standard end mills (same as hrubovani/dokoncovani)
    catalog[("milling", "pocket_rough", "P")] = catalog[("milling", "hrubovani", "P")]
    catalog[("milling", "pocket_finish", "P")] = catalog[("milling", "dokoncovani", "P")]

    # --- MILLING DRILLING (mill_drill) ---
    # Uses standard drills (same as vrtani)
    catalog[("milling", "mill_drill", "P")] = catalog[("drilling", "vrtani", "P")]
    catalog[("milling", "mill_drill", "M")] = catalog[("drilling", "vrtani", "M")]
    catalog[("milling", "mill_drill", "N")] = catalog[("drilling", "vrtani", "N")]

    # --- MILLING TAPPING (mill_tap) ---
    # Uses standard taps (same as zavit_tap)
    catalog[("milling", "mill_tap", "P")] = catalog[("threading", "zavit_tap", "P")]
    catalog[("milling", "mill_tap", "M")] = catalog[("threading", "zavit_tap", "M")]

    # ========================================================================
    # LIVE TOOLING (4-axis lathe with Y-axis milling)
    # ========================================================================

    # --- RADIAL DRILLING (lt_drill) ---
    catalog[("live_tooling", "lt_drill", "P")] = catalog[("drilling", "vrtani", "P")]

    # --- RADIAL MILLING (lt_mill) ---
    catalog[("live_tooling", "lt_mill", "P")] = catalog[("milling", "hrubovani", "P")]

    # --- FLATS (lt_flat) ---
    catalog[("live_tooling", "lt_flat", "P")] = [
        {
            "dia_min": 10,
            "dia_max": 50,
            "tool_code": "ENDMILL_FLAT",
            "tool_name": "Fréza pro plochy",
            "notes": "End mill for milling flats on turned parts",
        },
    ]

    return catalog


# Singleton catalog (built once)
TOOL_CATALOG = _build_tool_catalog()


def select_tool(
    operation_type: str,
    operation: str,
    material_group: str,
    diameter: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Select appropriate tool from catalog.

    Lookup strategy:
    1. Convert material_group (8-digit) to ISO group (P/M/K/N/H)
    2. Lookup (operation_type, operation, iso_group) in catalog
    3. Filter by diameter range if diameter provided
    4. Fallback to ISO P (steel) if material not found

    Args:
        operation_type: turning, drilling, threading, milling, grooving, parting, live_tooling
        operation: hrubovani, dokoncovani, vrtani, zavitovani, etc.
        material_group: 8-digit code (e.g., "20910004")
        diameter: optional diameter [mm] to filter tool range

    Returns:
        Dict with tool_code, tool_name, notes
        Empty dict if no tool found

    Example:
        >>> select_tool("drilling", "vrtani", "20910004", 15.0)
        {"tool_code": "CARBIDE_DRILL", "tool_name": "Vrták VHM", "notes": "..."}
    """
    # Convert material to ISO group
    iso_group = get_iso_group_from_material(material_group)

    # Lookup key
    key = (operation_type, operation, iso_group)
    tool_specs = TOOL_CATALOG.get(key)

    if not tool_specs:
        # Fallback: try ISO P (steel - most common)
        logger.debug(f"No tools for {key}, trying ISO P fallback")
        fallback_key = (operation_type, operation, "P")
        tool_specs = TOOL_CATALOG.get(fallback_key)

    if not tool_specs:
        logger.warning(
            f"No tools found for operation_type={operation_type}, "
            f"operation={operation}, material={material_group}"
        )
        return {}

    # Filter by diameter if provided
    if diameter is not None:
        matching = [
            tool for tool in tool_specs
            if tool["dia_min"] <= diameter <= tool["dia_max"]
        ]
        if matching:
            # Return first match (tools sorted by dia range)
            return dict(matching[0])
        else:
            logger.warning(
                f"No tool found for diameter {diameter}mm in range "
                f"(operation={operation_type}/{operation})"
            )
            # Fallback: return last tool (largest range)
            return dict(tool_specs[-1])

    # No diameter filter: return first tool (smallest dia range)
    return dict(tool_specs[0])


def get_all_tools_for_operation(
    operation_type: str,
    operation: str,
    material_group: str,
) -> List[Dict[str, Any]]:
    """
    Get all available tools for an operation (all diameter ranges).

    Useful for UI tool selection dropdowns.

    Returns:
        List of tool specs, empty list if none found
    """
    iso_group = get_iso_group_from_material(material_group)
    key = (operation_type, operation, iso_group)
    tool_specs = TOOL_CATALOG.get(key, [])

    if not tool_specs:
        # Fallback to ISO P
        fallback_key = (operation_type, operation, "P")
        tool_specs = TOOL_CATALOG.get(fallback_key, [])

    return [dict(tool) for tool in tool_specs]  # Return copies


def get_tool_catalog_stats() -> Dict[str, Any]:
    """
    Get statistics about tool catalog.

    Returns:
        Dict with counts: total_entries, operations_covered, materials_covered
    """
    operations = set()
    materials = set()

    for (op_type, operation, iso) in TOOL_CATALOG.keys():
        operations.add(f"{op_type}/{operation}")
        materials.add(iso)

    return {
        "total_entries": len(TOOL_CATALOG),
        "operations_covered": len(operations),
        "materials_covered": sorted(materials),
        "operations_list": sorted(operations),
    }
