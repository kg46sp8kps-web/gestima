"""GESTIMA - Katalog řezných podmínek pro CNC obrábění

Reference: Sandvik Coromant, Iscar, Kennametal, TaeguTec
Materiálové skupiny: interní 8-digit kódy (ADR-017)

Hodnoty pro povlakované karbidové destičky (standard):
- Soustružení: ISO CNMG/DNMG, třídy GC4325/GC4315 (P), GC2220 (M), GC1125 (K)
- Vrtání: monolitní karbid, TiAlN povlak
- Frézování: CoroMill 390/490, karbid s povlakem
- Závitování: CoroThread 266, ISO profil

Struktura: {material_group: {(operation_type, operation, mode): {Vc, f, Ap}}}
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# === MATERIÁLOVÉ SKUPINY (8-digit kódy → cutting conditions ID) ===
MATERIAL_GROUP_MAP = {
    "20910000": {"name": "Hliník", "iso": "N", "density": 2.7},
    "20910001": {"name": "Měď", "iso": "N", "density": 8.9},
    "20910002": {"name": "Mosaz", "iso": "N", "density": 8.5},
    "20910003": {"name": "Ocel automatová", "iso": "P", "density": 7.85},
    "20910004": {"name": "Ocel konstrukční", "iso": "P", "density": 7.85},
    "20910005": {"name": "Ocel legovaná", "iso": "P", "density": 7.85},
    "20910006": {"name": "Ocel nástrojová", "iso": "H", "density": 7.85},
    "20910007": {"name": "Nerez", "iso": "M", "density": 7.9},
    "20910008": {"name": "Plasty", "iso": "N", "density": 1.2},
}

# === MAPOVÁNÍ W.Nr. (DIN) → interní kód ===
# Rozsah prefixů Werkstoffnummer → material_group
WERKSTOFF_PREFIX_MAP = {
    # Ocel automatová (11SMn30, 11SMnPb30, 9SMn28)
    "1.07": "20910003",
    "1.08": "20910003",
    # Ocel konstrukční (C45, C35, S355, E295)
    "1.00": "20910004",
    "1.01": "20910004",
    "1.02": "20910004",
    "1.03": "20910004",
    "1.04": "20910004",
    "1.05": "20910004",
    "1.10": "20910004",
    "1.11": "20910004",
    "1.12": "20910004",
    "1.13": "20910004",
    # Ocel legovaná (42CrMo4, 34CrNiMo6, 16MnCr5)
    "1.50": "20910005",
    "1.51": "20910005",
    "1.52": "20910005",
    "1.53": "20910005",
    "1.54": "20910005",
    "1.56": "20910005",
    "1.65": "20910005",
    "1.66": "20910005",
    "1.67": "20910005",
    "1.68": "20910005",
    "1.69": "20910005",
    "1.70": "20910005",
    "1.71": "20910005",
    "1.72": "20910005",
    "1.73": "20910005",
    "1.74": "20910005",
    "1.75": "20910005",
    "1.76": "20910005",
    "1.77": "20910005",
    # Ocel nástrojová (X210Cr12, 90MnCrV8, X37CrMoV5-1)
    "1.20": "20910006",
    "1.21": "20910006",
    "1.22": "20910006",
    "1.23": "20910006",
    "1.24": "20910006",
    "1.25": "20910006",
    "1.26": "20910006",
    "1.27": "20910006",
    "1.28": "20910006",
    "1.29": "20910006",
    # Nerez (X5CrNi18-10, X2CrNiMo17-12-2)
    "1.40": "20910007",
    "1.41": "20910007",
    "1.43": "20910007",
    "1.44": "20910007",
    "1.45": "20910007",
    "1.46": "20910007",
    # Hliník (AlMg3, AlSi1MgMn, AlCu4Mg1)
    "3.0": "20910000",
    "3.1": "20910000",
    "3.2": "20910000",
    "3.3": "20910000",
    "3.4": "20910000",
    # Měď (Cu-ETP, CuZn, CuSn)
    "2.0": "20910001",
    "2.1": "20910002",  # Mosaz (CuZn)
}


def resolve_material_group(material_spec: str) -> Optional[str]:
    """
    Převede W.Nr. nebo textový popis materiálu na interní 8-digit kód.

    Příklady:
        "1.1191" → "20910004" (konstrukční ocel, C45)
        "1.4301" → "20910007" (nerez, X5CrNi18-10)
        "3.3547" → "20910000" (hliník, AlMg4.5Mn)
        "C45"    → "20910004" (přes textový fallback)
    """
    if not material_spec:
        return None

    material_spec = material_spec.strip()

    # Přímý match na 8-digit kód
    if material_spec in MATERIAL_GROUP_MAP:
        return material_spec

    # W.Nr. formát: 1.xxxx
    import re
    wnr_match = re.search(r'(\d\.\d{4})', material_spec)
    if wnr_match:
        wnr = wnr_match.group(1)
        # Zkus prefix match (od nejdelšího)
        for prefix_len in [4, 3]:
            prefix = wnr[:prefix_len]
            if prefix in WERKSTOFF_PREFIX_MAP:
                return WERKSTOFF_PREFIX_MAP[prefix]

    # Textový fallback
    spec_lower = material_spec.lower()
    text_map = {
        "hliník": "20910000", "aluminium": "20910000", "aluminum": "20910000",
        "al": "20910000", "almg": "20910000", "alsi": "20910000",
        "měď": "20910001", "copper": "20910001", "cu-": "20910001",
        "mosaz": "20910002", "brass": "20910002", "cuzn": "20910002",
        "automatová": "20910003", "automatic": "20910003", "11smn": "20910003",
        "konstrukční": "20910004", "structural": "20910004",
        "c45": "20910004", "c35": "20910004", "s355": "20910004",
        "legovaná": "20910005", "alloy": "20910005",
        "42crmo": "20910005", "34crni": "20910005", "16mncr": "20910005",
        "nástrojová": "20910006", "tool steel": "20910006",
        "nerez": "20910007", "stainless": "20910007", "inox": "20910007",
        "x5crni": "20910007", "aisi 304": "20910007", "aisi 316": "20910007",
        "plast": "20910008", "plastic": "20910008", "pom": "20910008",
        "pa": "20910008", "ptfe": "20910008", "peek": "20910008",
    }
    for keyword, code in text_map.items():
        if keyword in spec_lower:
            return code

    # Default: konstrukční ocel (nejčastější)
    logger.warning(f"Material '{material_spec}' not mapped, defaulting to 20910004")
    return "20910004"


# ====================================================================
# KATALOG ŘEZNÝCH PODMÍNEK
# ====================================================================
# Klíč: (material_group, operation_type, operation, mode)
# Hodnoty: {"Vc": m/min, "f": mm/ot, "Ap": mm, "fz": mm/zub}
#
# Zdroje:
#   Sandvik Coromant - Hlavní katalog 2024
#   Iscar - Machining Calculator
#   Kennametal - NOVO Tooling System
#   TaeguTec - Smart Machining Guide
# ====================================================================

def _build_catalog() -> Dict[tuple, Dict[str, float]]:
    """Sestaví kompletní katalog řezných podmínek."""
    catalog = {}

    # === SOUSTRUŽENÍ ===
    # Referenční hodnoty: Sandvik GC4325 (P steel), GC2220 (M stainless),
    # GC1115 (N non-ferrous), GC4340 (H hardened)
    _turning_base = {
        #                        Vc_mid  f_mid   Ap_mid
        "20910000": {"Vc": 500, "f": 0.30, "Ap": 3.0},  # Hliník — vysoké Vc, měkký
        "20910001": {"Vc": 280, "f": 0.25, "Ap": 2.5},  # Měď
        "20910002": {"Vc": 320, "f": 0.28, "Ap": 2.5},  # Mosaz
        "20910003": {"Vc": 280, "f": 0.30, "Ap": 3.0},  # Automatová ocel (11SMn30)
        "20910004": {"Vc": 220, "f": 0.25, "Ap": 2.5},  # Konstrukční ocel (C45)
        "20910005": {"Vc": 180, "f": 0.22, "Ap": 2.0},  # Legovaná ocel (42CrMo4)
        "20910006": {"Vc": 120, "f": 0.18, "Ap": 1.5},  # Nástrojová ocel
        "20910007": {"Vc": 160, "f": 0.20, "Ap": 1.5},  # Nerez (austenitická)
        "20910008": {"Vc": 600, "f": 0.35, "Ap": 3.0},  # Plasty
    }

    # Faktory pro rough / finish / modes
    _mode_factors = {
        "low":  {"Vc": 0.75, "f": 0.75, "Ap": 0.70},
        "mid":  {"Vc": 1.00, "f": 1.00, "Ap": 1.00},
        "high": {"Vc": 1.25, "f": 1.20, "Ap": 1.30},
    }
    _finish_factors = {"Vc": 1.15, "f": 0.35, "Ap": 0.15}  # Finish = vyšší Vc, nízký f + Ap

    for mat_code, base in _turning_base.items():
        for mode, mf in _mode_factors.items():
            # Hrubování
            catalog[(mat_code, "turning", "hrubovani", mode)] = {
                "Vc": round(base["Vc"] * mf["Vc"]),
                "f": round(base["f"] * mf["f"], 3),
                "Ap": round(base["Ap"] * mf["Ap"], 1),
            }
            # Dokončování
            catalog[(mat_code, "turning", "dokoncovani", mode)] = {
                "Vc": round(base["Vc"] * _finish_factors["Vc"] * mf["Vc"]),
                "f": round(base["f"] * _finish_factors["f"] * mf["f"], 3),
                "Ap": round(base["Ap"] * _finish_factors["Ap"] * mf["Ap"], 2),
            }

    # === VRTÁNÍ ===
    # Reference: Sandvik CoroDrill 860, Iscar SumoCham
    _drilling_base = {
        "20910000": {"Vc": 150, "f": 0.25},
        "20910001": {"Vc": 100, "f": 0.20},
        "20910002": {"Vc": 120, "f": 0.22},
        "20910003": {"Vc": 110, "f": 0.25},
        "20910004": {"Vc": 90,  "f": 0.20},
        "20910005": {"Vc": 70,  "f": 0.18},
        "20910006": {"Vc": 45,  "f": 0.12},
        "20910007": {"Vc": 55,  "f": 0.15},
        "20910008": {"Vc": 180, "f": 0.30},
    }

    for mat_code, base in _drilling_base.items():
        for mode, mf in _mode_factors.items():
            # Navrtání (center drill) — nízké Vc, krátká hloubka
            catalog[(mat_code, "drilling", "navrtani", mode)] = {
                "Vc": round(base["Vc"] * 0.60 * mf["Vc"]),
                "f": round(base["f"] * 0.50 * mf["f"], 3),
            }
            # Vrtání standard
            catalog[(mat_code, "drilling", "vrtani", mode)] = {
                "Vc": round(base["Vc"] * mf["Vc"]),
                "f": round(base["f"] * mf["f"], 3),
            }
            # Hluboké vrtání (>4×D) — nižší Vc, nižší f
            catalog[(mat_code, "drilling", "vrtani_hluboke", mode)] = {
                "Vc": round(base["Vc"] * 0.70 * mf["Vc"]),
                "f": round(base["f"] * 0.70 * mf["f"], 3),
            }
            # Vystružování (reaming) — nízké Vc, nízký f, přesnost
            catalog[(mat_code, "drilling", "vystruzovani", mode)] = {
                "Vc": round(base["Vc"] * 0.40 * mf["Vc"]),
                "f": round(base["f"] * 0.60 * mf["f"], 3),
            }

    # === ZÁVITOVÁNÍ ===
    # Reference: Sandvik CoroThread 266, Iscar Penta
    _threading_base = {
        "20910000": {"Vc": 120},
        "20910001": {"Vc": 80},
        "20910002": {"Vc": 90},
        "20910003": {"Vc": 100},
        "20910004": {"Vc": 80},
        "20910005": {"Vc": 60},
        "20910006": {"Vc": 40},
        "20910007": {"Vc": 50},
        "20910008": {"Vc": 80},
    }

    for mat_code, base in _threading_base.items():
        for mode, mf in _mode_factors.items():
            catalog[(mat_code, "threading", "zavitovani", mode)] = {
                "Vc": round(base["Vc"] * mf["Vc"]),
            }

    # === ZÁPICHOVÁNÍ ===
    # Reference: Sandvik CoroCut, Iscar DGN/DTG
    _grooving_base = {
        "20910000": {"Vc": 250, "f": 0.10},
        "20910001": {"Vc": 150, "f": 0.08},
        "20910002": {"Vc": 180, "f": 0.09},
        "20910003": {"Vc": 160, "f": 0.10},
        "20910004": {"Vc": 130, "f": 0.08},
        "20910005": {"Vc": 100, "f": 0.07},
        "20910006": {"Vc": 70,  "f": 0.05},
        "20910007": {"Vc": 80,  "f": 0.06},
        "20910008": {"Vc": 300, "f": 0.12},
    }

    for mat_code, base in _grooving_base.items():
        for mode, mf in _mode_factors.items():
            catalog[(mat_code, "grooving", "zapichovani", mode)] = {
                "Vc": round(base["Vc"] * mf["Vc"]),
                "f": round(base["f"] * mf["f"], 3),
            }

    # === UPÍCHNUTÍ ===
    # Reference: Sandvik CoroCut Q-Cut, Iscar Tang-Grip
    _parting_base = {
        "20910000": {"Vc": 200, "f": 0.08},
        "20910001": {"Vc": 120, "f": 0.06},
        "20910002": {"Vc": 150, "f": 0.07},
        "20910003": {"Vc": 130, "f": 0.08},
        "20910004": {"Vc": 100, "f": 0.06},
        "20910005": {"Vc": 80,  "f": 0.05},
        "20910006": {"Vc": 55,  "f": 0.04},
        "20910007": {"Vc": 65,  "f": 0.05},
        "20910008": {"Vc": 250, "f": 0.10},
    }

    for mat_code, base in _parting_base.items():
        for mode, mf in _mode_factors.items():
            catalog[(mat_code, "parting", "upichnuti", mode)] = {
                "Vc": round(base["Vc"] * mf["Vc"]),
                "f": round(base["f"] * mf["f"], 3),
            }

    # === FRÉZOVÁNÍ ===
    # Reference: Sandvik CoroMill 390/490, Iscar HELi2000, Kennametal HARVI
    # fz = posuv na zub (mm/tooth)
    _milling_base = {
        "20910000": {"Vc": 350, "fz": 0.15, "Ap": 3.0},
        "20910001": {"Vc": 200, "fz": 0.10, "Ap": 2.0},
        "20910002": {"Vc": 250, "fz": 0.12, "Ap": 2.5},
        "20910003": {"Vc": 200, "fz": 0.12, "Ap": 2.5},
        "20910004": {"Vc": 160, "fz": 0.10, "Ap": 2.0},
        "20910005": {"Vc": 130, "fz": 0.08, "Ap": 1.5},
        "20910006": {"Vc": 80,  "fz": 0.06, "Ap": 1.0},
        "20910007": {"Vc": 100, "fz": 0.07, "Ap": 1.2},
        "20910008": {"Vc": 400, "fz": 0.18, "Ap": 4.0},
    }

    for mat_code, base in _milling_base.items():
        for mode, mf in _mode_factors.items():
            catalog[(mat_code, "milling", "frezovani", mode)] = {
                "Vc": round(base["Vc"] * mf["Vc"]),
                "fz": round(base["fz"] * mf["f"], 3),  # fz uses same factor as f
                "Ap": round(base["Ap"] * mf["Ap"], 1),
            }

    # === BROUŠENÍ ===
    # Reference: Norton/Saint-Gobain, Tyrolit
    _grinding_base = {
        "20910000": {"Vc": 35, "f": 0.005, "Ap": 0.02},
        "20910003": {"Vc": 30, "f": 0.004, "Ap": 0.015},
        "20910004": {"Vc": 30, "f": 0.004, "Ap": 0.015},
        "20910005": {"Vc": 28, "f": 0.003, "Ap": 0.010},
        "20910006": {"Vc": 25, "f": 0.003, "Ap": 0.010},
        "20910007": {"Vc": 22, "f": 0.003, "Ap": 0.008},
    }

    for mat_code, base in _grinding_base.items():
        for mode, mf in _mode_factors.items():
            catalog[(mat_code, "grinding", "brouseni", mode)] = {
                "Vc": round(base["Vc"] * mf["Vc"], 1),
                "f": round(base["f"] * mf["f"], 4),
                "Ap": round(base["Ap"] * mf["Ap"], 3),
            }

    return catalog


# Singleton katalog (built once)
CUTTING_CONDITIONS_CATALOG = _build_catalog()


def get_catalog_conditions(
    material_group: str,
    operation_type: str,
    operation: str,
    mode: str = "mid",
) -> Dict[str, Any]:
    """
    Vrátí řezné podmínky z katalogu.

    Args:
        material_group: 8-digit kód (20910004)
        operation_type: turning, drilling, threading, milling, grooving, parting, grinding
        operation: hrubovani, dokoncovani, vrtani, etc.
        mode: low, mid, high

    Returns:
        Dict s Vc, f, Ap, fz (co je relevantní pro danou operaci)
    """
    key = (material_group, operation_type, operation, mode)
    result = CUTTING_CONDITIONS_CATALOG.get(key)

    if not result:
        logger.debug(
            f"No catalog conditions for {key}, trying mid mode"
        )
        # Fallback: try mid mode
        mid_key = (material_group, operation_type, operation, "mid")
        result = CUTTING_CONDITIONS_CATALOG.get(mid_key)

    if not result:
        logger.warning(f"No catalog conditions for material={material_group}, "
                       f"op={operation_type}/{operation}")
        return {}

    return dict(result)  # Return copy


async def seed_cutting_conditions_to_db(db_session) -> int:
    """
    Naplní tabulku cutting_conditions daty z katalogu.

    Používá 8-digit materiálové kódy.
    Přepíše existující data (upsert by material_group + operation_type + operation + mode).

    Returns:
        Počet vložených řádků
    """
    from app.models.cutting_condition import CuttingConditionDB
    from sqlalchemy import delete

    count = 0
    try:
        # Smaž existující data
        await db_session.execute(delete(CuttingConditionDB))

        # Vlož nová data
        for (mat_group, op_type, operation, mode), conditions in CUTTING_CONDITIONS_CATALOG.items():
            mat_info = MATERIAL_GROUP_MAP.get(mat_group, {})
            record = CuttingConditionDB(
                material_group=mat_group,
                material_name=mat_info.get("name", ""),
                operation_type=op_type,
                operation=operation,
                mode=mode,
                Vc=conditions.get("Vc"),
                f=conditions.get("f") or conditions.get("fz"),
                Ap=conditions.get("Ap"),
                notes=f"Katalog v1.0 — {mat_info.get('iso', '?')} group",
            )
            db_session.add(record)
            count += 1

        await db_session.commit()
        logger.info(f"Seeded {count} cutting conditions to DB")
        return count

    except Exception as e:
        await db_session.rollback()
        logger.error(f"Failed to seed cutting conditions: {e}", exc_info=True)
        raise
