"""GESTIMA - Řezné podmínky"""

from typing import Dict, Any, Optional

MATERIAL_COEFFICIENTS = {
    "automatova_ocel":     {"K_Vc": 1.30, "K_f": 1.20, "threading_category": "easy"},
    "konstrukcni_ocel":    {"K_Vc": 1.00, "K_f": 1.00, "threading_category": "medium"},
    "legovana_ocel":       {"K_Vc": 0.75, "K_f": 0.85, "threading_category": "medium"},
    "nastrojova_ocel":     {"K_Vc": 0.50, "K_f": 0.70, "threading_category": "hard"},
    "nerez_feriticka":     {"K_Vc": 0.55, "K_f": 0.80, "threading_category": "medium"},
    "nerez_austeniticka":  {"K_Vc": 0.45, "K_f": 0.70, "threading_category": "hard"},
    "hlinik":              {"K_Vc": 1.80, "K_f": 1.50, "threading_category": "easy"},
    "mosaz_bronz":         {"K_Vc": 1.50, "K_f": 1.30, "threading_category": "easy"},
    "med":                 {"K_Vc": 1.20, "K_f": 1.10, "threading_category": "easy"},
    "plasty":              {"K_Vc": 2.00, "K_f": 1.50, "threading_category": "easy"},
}

BASE_CONDITIONS = {
    ("turning", "od_rough", "low"):  {"Vc": 120, "f": 0.25, "Ap": 2.5},
    ("turning", "od_rough", "mid"):  {"Vc": 180, "f": 0.30, "Ap": 3.0},
    ("turning", "od_rough", "high"): {"Vc": 250, "f": 0.35, "Ap": 3.5},
    ("turning", "od_finish", "low"):  {"Vc": 150, "f": 0.10, "Ap": 0.3},
    ("turning", "od_finish", "mid"):  {"Vc": 200, "f": 0.12, "Ap": 0.4},
    ("turning", "od_finish", "high"): {"Vc": 280, "f": 0.15, "Ap": 0.5},
    ("turning", "id_rough", "low"):  {"Vc": 100, "f": 0.20, "Ap": 2.0},
    ("turning", "id_rough", "mid"):  {"Vc": 150, "f": 0.25, "Ap": 2.5},
    ("turning", "id_rough", "high"): {"Vc": 200, "f": 0.30, "Ap": 3.0},
    ("turning", "id_finish", "low"):  {"Vc": 120, "f": 0.08, "Ap": 0.25},
    ("turning", "id_finish", "mid"):  {"Vc": 170, "f": 0.10, "Ap": 0.35},
    ("turning", "id_finish", "high"): {"Vc": 220, "f": 0.12, "Ap": 0.45},
    ("drilling", "drill", "low"):  {"Vc": 60, "f": 0.12},
    ("drilling", "drill", "mid"):  {"Vc": 90, "f": 0.18},
    ("drilling", "drill", "high"): {"Vc": 120, "f": 0.25},
    ("milling", "face", "low"):  {"Vc": 100, "fz": 0.08, "Ap": 1.5},
    ("milling", "face", "mid"):  {"Vc": 150, "fz": 0.12, "Ap": 2.0},
    ("milling", "face", "high"): {"Vc": 200, "fz": 0.15, "Ap": 2.5},
    ("grooving", "groove", "low"):  {"Vc": 60, "f": 0.05},
    ("grooving", "groove", "mid"):  {"Vc": 90, "f": 0.08},
    ("grooving", "groove", "high"): {"Vc": 120, "f": 0.10},
    ("parting", "parting", "low"):  {"Vc": 50, "f": 0.04},
    ("parting", "parting", "mid"):  {"Vc": 80, "f": 0.06},
    ("parting", "parting", "high"): {"Vc": 100, "f": 0.08},
    ("threading", "thread", "low"):  {"Vc": 40},
    ("threading", "thread", "mid"):  {"Vc": 60},
    ("threading", "thread", "high"): {"Vc": 80},
    ("grinding", "od", "low"):  {"Vc": 25, "f": 0.008, "Ap": 0.015},
    ("grinding", "od", "mid"):  {"Vc": 30, "f": 0.010, "Ap": 0.020},
    ("grinding", "od", "high"): {"Vc": 35, "f": 0.012, "Ap": 0.025},
}

FEATURE_TO_OPERATION = {
    "face": ("turning", "od_finish"),
    "od_rough": ("turning", "od_rough"),
    "od_finish": ("turning", "od_finish"),
    "od_profile": ("turning", "od_finish"),
    "id_rough": ("turning", "id_rough"),
    "id_finish": ("turning", "id_finish"),
    "id_profile": ("turning", "id_finish"),
    "bore": ("turning", "id_rough"),
    "thread_od": ("threading", "thread"),
    "thread_id": ("threading", "thread"),
    "groove_od": ("grooving", "groove"),
    "groove_id": ("grooving", "groove"),
    "groove_face": ("grooving", "groove"),
    "parting": ("parting", "parting"),
    "drill": ("drilling", "drill"),
    "drill_deep": ("drilling", "drill"),
    "center_drill": ("drilling", "drill"),
    "ream": ("drilling", "drill"),
    "tap": ("threading", "thread"),
    "mill_face": ("milling", "face"),
    "mill_pocket": ("milling", "face"),
    "mill_slot": ("milling", "face"),
    "grind_od": ("grinding", "od"),
    "grind_id": ("grinding", "od"),
    "grind_face": ("grinding", "od"),
}


def get_conditions(
    feature_type: str,
    material_group: str,
    mode: str = "mid",
    diameter: Optional[float] = None,
    pitch: Optional[float] = None,
) -> Dict[str, Any]:
    result = {"Vc": None, "f": None, "Ap": None, "fz": None}
    
    mapping = FEATURE_TO_OPERATION.get(feature_type, ("turning", "od_finish"))
    category, operation = mapping
    
    base_key = (category, operation, mode)
    base = BASE_CONDITIONS.get(base_key, {})
    
    if not base:
        return result
    
    mat = MATERIAL_COEFFICIENTS.get(material_group, MATERIAL_COEFFICIENTS["konstrukcni_ocel"])
    
    if "Vc" in base:
        result["Vc"] = round(base["Vc"] * mat["K_Vc"], 0)
    if "f" in base:
        result["f"] = round(base["f"] * mat["K_f"], 3)
    if "fz" in base:
        result["fz"] = round(base["fz"] * mat["K_f"], 3)
    if "Ap" in base:
        result["Ap"] = base["Ap"]
    
    if category == "drilling" and diameter:
        result = _apply_drilling_coefficients(result, diameter)
    
    return result


def _apply_drilling_coefficients(conditions: Dict, diameter: float) -> Dict:
    coefficients = [
        (3,   0.60, 0.25),
        (6,   0.70, 0.40),
        (10,  0.85, 0.60),
        (16,  1.00, 0.80),
        (25,  1.00, 1.00),
        (40,  0.95, 1.15),
        (999, 0.85, 1.25),
    ]
    
    k_vc, k_f = 1.0, 1.0
    for max_dia, kvc, kf in coefficients:
        if diameter <= max_dia:
            k_vc, k_f = kvc, kf
            break
    
    if conditions.get("Vc"):
        conditions["Vc"] = round(conditions["Vc"] * k_vc, 0)
    if conditions.get("f"):
        conditions["f"] = round(conditions["f"] * k_f, 3)
    
    return conditions


def get_threading_passes(material_group: str, pitch: float) -> int:
    mat = MATERIAL_COEFFICIENTS.get(material_group, MATERIAL_COEFFICIENTS["konstrukcni_ocel"])
    category = mat.get("threading_category", "medium")
    
    passes_table = {
        "easy":   {1.0: 4, 1.5: 5, 2.0: 6, 3.0: 7, 999: 9},
        "medium": {1.0: 5, 1.5: 6, 2.0: 7, 3.0: 9, 999: 11},
        "hard":   {1.0: 6, 1.5: 7, 2.0: 9, 3.0: 11, 999: 14},
    }
    
    table = passes_table.get(category, passes_table["medium"])
    for max_pitch, num_passes in sorted(table.items()):
        if pitch <= max_pitch:
            return num_passes
    return 6
