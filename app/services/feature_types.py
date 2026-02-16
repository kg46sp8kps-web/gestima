"""GESTIMA — Feature Types Catalog (Single Source of Truth)

Shared between:
- AI extraction prompt (what AI returns)
- Feature calculator (how to compute time)
- Frontend table (what user sees and edits)

NEVER define feature types elsewhere. Import from here.

Version: 1.0.0 (2026-02-15)
"""

from typing import Dict, Any, Optional, Tuple, List

# Feature group for UI display
FEATURE_GROUPS = {
    "dimensions": "Rozměry",
    "holes": "Díry a zahloubení",
    "threads": "Závity",
    "contours": "Kontury a tvary",
    "quality": "Kvalita povrchu",
    "info": "Informace (bez času)",
}

# SINGLE SOURCE OF TRUTH for all feature types
# key = feature type string (used in JSON, DB, frontend)
FEATURE_TYPES: Dict[str, Dict[str, Any]] = {
    # ═══ ROZMĚRY (Dimensions) ═══
    "outer_diameter": {
        "label_cs": "Vnější průměr",
        "label_en": "Outer diameter",
        "description": "Vnější průměrový stupeň na soustružení (hřídel, osazení). Pro stupňované hřídele — KAŽDÝ stupeň zvlášť.",
        "example": "ø60 h9, ø45×30mm",
        "group": "dimensions",
        "has_time": True,
        "operation": ("turning", "hrubovani"),
    },
    "inner_diameter": {
        "label_cs": "Vnitřní průměr",
        "label_en": "Inner diameter",
        "description": "Vnitřní vyvrtání/vysoustružení (H7, H6). NE vnější osazení!",
        "example": "ø30 H7, vnitřní ø25",
        "group": "dimensions",
        "has_time": True,
        "operation": ("turning", "hrubovani"),
    },
    "step": {
        "label_cs": "Stupeň/osazení",
        "label_en": "Step",
        "description": "Přechod mezi průměry nebo rozměry. Soustružení jednoho stupně.",
        "example": "ø40→ø30 osazení, stupeň 5mm",
        "group": "dimensions",
        "has_time": True,
        "operation": ("turning", "hrubovani"),
    },
    "length": {
        "label_cs": "Délka",
        "label_en": "Length",
        "description": "Obalový délkový rozměr dílu (informační, negeneruje čas).",
        "example": "L=150mm",
        "group": "info",
        "has_time": False,
        "operation": None,
    },
    "width": {
        "label_cs": "Šířka",
        "label_en": "Width",
        "description": "Obalový šířkový rozměr dílu (informační).",
        "example": "W=80mm",
        "group": "info",
        "has_time": False,
        "operation": None,
    },
    "height": {
        "label_cs": "Výška",
        "label_en": "Height",
        "description": "Obalový výškový rozměr dílu (informační).",
        "example": "H=30mm",
        "group": "info",
        "has_time": False,
        "operation": None,
    },
    "wall_thickness": {
        "label_cs": "Tloušťka stěny",
        "label_en": "Wall thickness",
        "description": "Tloušťka stěny trubky nebo profilu (informační).",
        "example": "t=3mm",
        "group": "info",
        "has_time": False,
        "operation": None,
    },

    # ═══ DÍRY A ZAHLOUBENÍ (Holes) ═══
    "through_hole": {
        "label_cs": "Průchozí díra",
        "label_en": "Through hole",
        "description": "Díra skrz celý materiál. Uveď průměr a počet.",
        "example": "ø8.5 průchozí, 4× ø5.3",
        "group": "holes",
        "has_time": True,
        "operation": ("drilling", "vrtani"),
    },
    "blind_hole": {
        "label_cs": "Slepá díra",
        "label_en": "Blind hole",
        "description": "Díra se dnem (neprochází). Uveď průměr a hloubku.",
        "example": "ø6 hloubka 15mm",
        "group": "holes",
        "has_time": True,
        "operation": ("drilling", "vrtani"),
    },
    "counterbore": {
        "label_cs": "Zahloubení",
        "label_en": "Counterbore",
        "description": "Stupňovaný otvor — díra + větší průměr nahoře (pro hlavu šroubu).",
        "example": "ø5.3/ø10×5 zahloubení",
        "group": "holes",
        "has_time": True,
        "operation": ("drilling", "vrtani"),
    },
    "countersink": {
        "label_cs": "Kuželové sražení díry",
        "label_en": "Countersink",
        "description": "Kuželové zahloubení pro šroub se zápustnou hlavou (90° nebo 120°).",
        "example": "ø8.5 se zahloubením 90°",
        "group": "holes",
        "has_time": True,
        "operation": ("drilling", "vrtani"),
    },
    "reamed_hole": {
        "label_cs": "Vystružovaná díra",
        "label_en": "Reamed hole",
        "description": "Přesná díra H7/H6 — dokončená vystružováním.",
        "example": "ø10 H7",
        "group": "holes",
        "has_time": True,
        "operation": ("drilling", "vystruzovani"),
    },

    # ═══ ZÁVITY (Threads) ═══
    "thread_external": {
        "label_cs": "Vnější závit",
        "label_en": "External thread",
        "description": "Závit na vnějším průměru (M×, stoupání, délka).",
        "example": "M10×1.5 délka 20mm",
        "group": "threads",
        "has_time": True,
        "operation": ("threading", "zavitovani"),
    },
    "thread_internal": {
        "label_cs": "Vnitřní závit",
        "label_en": "Internal thread",
        "description": "Závit uvnitř díry (M× v díře, stoupání, hloubka).",
        "example": "M6 hloubka 12mm, 4× M5",
        "group": "threads",
        "has_time": True,
        "operation": ("threading", "zavitovani"),
    },
    "thread": {
        "label_cs": "Závit (obecný)",
        "label_en": "Thread (general)",
        "description": "Obecný závit (AI může vrátit genericky).",
        "example": "M8",
        "group": "threads",
        "has_time": True,
        "operation": ("threading", "zavitovani"),
    },

    # ═══ KONTURY A TVARY (Contours) ═══
    "chamfer": {
        "label_cs": "Sražení hrany",
        "label_en": "Chamfer",
        "description": "Sražení ostré hrany (rozměr × úhel). Konstantní čas ~3s.",
        "example": "0.5×45°, 1×45° na obou stranách",
        "group": "contours",
        "has_time": True,
        "operation": None,  # constant time
    },
    "radius": {
        "label_cs": "Rádius/zaoblení",
        "label_en": "Radius/fillet",
        "description": "Zaoblení hrany nebo přechodu. POZOR: rádius na konci obdélníkové kapsy = pocket!",
        "example": "R2, R0.5 na přechodech",
        "group": "contours",
        "has_time": True,
        "operation": None,  # constant time
    },
    "fillet": {
        "label_cs": "Zaoblení (fillet)",
        "label_en": "Fillet",
        "description": "Zaoblení vnitřního rohu nebo přechodu.",
        "example": "R1.5 zaoblení",
        "group": "contours",
        "has_time": True,
        "operation": None,  # constant time
    },
    "groove": {
        "label_cs": "Zápich",
        "label_en": "Groove",
        "description": "Úzká drážka na soustruhu (mezi průměry, pro O-kroužek, pro výběh nástroje).",
        "example": "zápich 3×1.5mm, zápich pro O-kroužek",
        "group": "contours",
        "has_time": True,
        "operation": ("grooving", "zapichovani"),
    },
    "pocket": {
        "label_cs": "Kapsa",
        "label_en": "Pocket",
        "description": "Frézovaná kapsa (uzavřený výřez s dnem). VČETNĚ obdélníkových výřezů se zaoblenými rohy.",
        "example": "80×22×3.4mm kapsa, 2 kapsy",
        "group": "contours",
        "has_time": True,
        "operation": ("milling", "frezovani"),
    },
    "slot": {
        "label_cs": "Drážka průchozí",
        "label_en": "Slot",
        "description": "Průchozí drážka (otevřená na obou stranách). Šířka × délka.",
        "example": "drážka 8×40mm",
        "group": "contours",
        "has_time": True,
        "operation": ("milling", "frezovani"),
    },
    "keyway": {
        "label_cs": "Drážka pro pero",
        "label_en": "Keyway",
        "description": "Drážka pro pero/klín (šířka × hloubka × délka).",
        "example": "drážka pro pero 6×3.5×20",
        "group": "contours",
        "has_time": True,
        "operation": ("milling", "frezovani"),
    },
    "flat": {
        "label_cs": "Frézovaná plocha",
        "label_en": "Flat (milled surface)",
        "description": "Rovná frézovaná plocha na rotačním dílu (pro klíč, pro dosednutí).",
        "example": "2× frézovaná plocha šířka 15mm",
        "group": "contours",
        "has_time": True,
        "operation": ("milling", "frezovani"),
    },
    "taper": {
        "label_cs": "Kužel",
        "label_en": "Taper",
        "description": "Kuželová plocha (úhel nebo poměr).",
        "example": "kužel 1:10, 5° kužel",
        "group": "contours",
        "has_time": True,
        "operation": ("turning", "dokoncovani"),
    },
    "knurling": {
        "label_cs": "Vroubkování",
        "label_en": "Knurling",
        "description": "Vroubkování na povrchu pro lepší úchop.",
        "example": "vroubkování RAA 0.8 šířka 15mm",
        "group": "contours",
        "has_time": True,
        "operation": None,  # constant time
    },
    "face": {
        "label_cs": "Čelní plocha",
        "label_en": "Face",
        "description": "Zarovnání čela dílu na soustruhu.",
        "example": "čelní zarovnání ø60",
        "group": "contours",
        "has_time": True,
        "operation": ("turning", "hrubovani"),
    },

    # ═══ KVALITA POVRCHU (Quality) ═══
    "surface_finish": {
        "label_cs": "Drsnost povrchu",
        "label_en": "Surface finish",
        "description": "Požadovaná drsnost (Ra/Rz). Ovlivňuje potřebu dokončovacího přejezdu.",
        "example": "Ra 1.6, Ra 0.8 na vnitřním ø",
        "group": "quality",
        "has_time": False,  # Impacts time via finishing passes, but not directly calculated
        "operation": None,
    },
    "tolerance_dimensional": {
        "label_cs": "Rozměrová tolerance",
        "label_en": "Dimensional tolerance",
        "description": "Přesná kóta ± hodnota nebo ISO lícování. h9/g7 na vnějšku = tolerance, NE díra!",
        "example": "50 ±0.02, ø30 h7",
        "group": "quality",
        "has_time": False,
        "operation": None,
    },
    "tolerance_geometric": {
        "label_cs": "Geometrická tolerance",
        "label_en": "Geometric tolerance",
        "description": "Kolmost, rovnoběžnost, házení, válcovitost atd.",
        "example": "kolmost 0.02, házení 0.05",
        "group": "quality",
        "has_time": False,
        "operation": None,
    },
    "general_tolerance": {
        "label_cs": "Všeobecná tolerance",
        "label_en": "General tolerance",
        "description": "Třída tolerance z razítkového pole (ISO 2768).",
        "example": "ISO 2768-mK",
        "group": "quality",
        "has_time": False,
        "operation": None,
    },

    # ═══ INFORMACE (Info) ═══
    "material": {
        "label_cs": "Materiál",
        "label_en": "Material",
        "description": "Materiálové označení z razítkového pole.",
        "example": "1.4305, EN AW-6082 T6",
        "group": "info",
        "has_time": False,
        "operation": None,
    },
    "surface_treatment": {
        "label_cs": "Povrchová úprava",
        "label_en": "Surface treatment",
        "description": "Elox, zinkování, niklování, chromování atd.",
        "example": "elox přírodní, pozinkovat",
        "group": "info",
        "has_time": False,
        "operation": None,
    },
    "heat_treatment": {
        "label_cs": "Tepelné zpracování",
        "label_en": "Heat treatment",
        "description": "Kalení, popouštění, žíhání, cementování.",
        "example": "kalit 58±2 HRC",
        "group": "info",
        "has_time": False,
        "operation": None,
    },
    "hardness": {
        "label_cs": "Tvrdost",
        "label_en": "Hardness",
        "description": "Požadovaná tvrdost (HRC, HB).",
        "example": "58 HRC, 200 HB",
        "group": "info",
        "has_time": False,
        "operation": None,
    },
    "weight": {
        "label_cs": "Hmotnost",
        "label_en": "Weight",
        "description": "Hmotnost dílu (pokud uvedena na výkresu).",
        "example": "0.85 kg",
        "group": "info",
        "has_time": False,
        "operation": None,
    },
    "drawing_note": {
        "label_cs": "Poznámka výkresu",
        "label_en": "Drawing note",
        "description": "Důležitá poznámka z výkresu.",
        "example": "všeobecné tolerance ISO 2768-mK",
        "group": "info",
        "has_time": False,
        "operation": None,
    },
    "edge_break": {
        "label_cs": "Sražení hran (obecné)",
        "label_en": "Edge break (general)",
        "description": "Všeobecná poznámka o sražení hran (ne konkrétní sražení).",
        "example": "alle Kanten brechen 0.5",
        "group": "contours",
        "has_time": True,
        "operation": None,  # constant time
    },
    "deburr": {
        "label_cs": "Odjehlení",
        "label_en": "Deburr",
        "description": "Odjehlení celého dílu (konstantní čas).",
        "example": "gratfrei, odjehlít",
        "group": "contours",
        "has_time": True,
        "operation": None,  # constant time
    },
}

# Constant times (minutes per feature, for features without cutting conditions)
CONSTANT_TIMES: Dict[str, float] = {
    "chamfer": 0.05,
    "radius": 0.05,
    "fillet": 0.05,
    "edge_break": 0.02,
    "deburr": 0.1,
    "knurling": 0.3,
}


def get_feature_type_keys() -> List[str]:
    """Get ordered list of all feature type keys.

    Returns:
        List of feature type string identifiers.
    """
    return list(FEATURE_TYPES.keys())


def get_feature_groups() -> Dict[str, List[str]]:
    """Get feature types grouped by category.

    Returns:
        Dict mapping group name to list of feature type keys in that group.
    """
    groups: Dict[str, List[str]] = {}
    for key, meta in FEATURE_TYPES.items():
        group = meta["group"]
        if group not in groups:
            groups[group] = []
        groups[group].append(key)
    return groups


def get_operation_for_feature(feature_type: str) -> Optional[Tuple[str, str]]:
    """Get cutting condition operation for a feature type.

    Args:
        feature_type: Feature type string (e.g. "through_hole", "outer_diameter")

    Returns:
        Tuple of (operation_type, operation) for cutting conditions lookup,
        or None if feature has no machining operation (constant time or informational).
    """
    meta = FEATURE_TYPES.get(feature_type)
    if not meta:
        return None
    return meta.get("operation")
