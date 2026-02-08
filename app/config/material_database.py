"""GESTIMA - Material Database for Machining Time Estimation

Physics-based material removal rate (MRR) database for CNC machining.
Based on industrial cutting data (Sandvik, Iscar, Kennametal).

ADR-040: Machining Time Estimation System
Reference: ISO 3685 (tool life), DIN 6580 (metal cutting)

Units:
- MRR: cm³/min (material removal rate)
- Cutting speeds: m/min
- Hardness: HB (Brinell)
- Penalties: dimensionless multiplier (1.0 = no penalty)

Material categories aligned with MATERIAL_GROUP_MAP in cutting_conditions_catalog.py
"""

from typing import Dict, Any

# === MATERIAL DATABASE ===
MATERIAL_DB: Dict[str, Dict[str, Any]] = {
    # === ALUMINUM (ISO N) ===
    "20910000": {  # Hliník
        "category": "aluminum",
        "iso_group": "N",
        "hardness_hb": 60,
        "density": 2.70,  # kg/dm³
        "mrr_aggressive_cm3_min": 800.00,  # roughing - very high MRR
        "mrr_finishing_cm3_min": 400.00,
        "cutting_speed_roughing_m_min": 350.00,
        "cutting_speed_finishing_m_min": 500.00,
        "deep_pocket_penalty": 1.30,  # less penalty than steel (better chip evacuation)
        "thin_wall_penalty": 1.80,  # moderate penalty (ductile)
    },

    # === COPPER & BRASS (ISO N) ===
    "20910001": {  # Měď
        "category": "copper",
        "iso_group": "N",
        "hardness_hb": 70,
        "density": 8.90,
        "mrr_aggressive_cm3_min": 500.00,
        "mrr_finishing_cm3_min": 250.00,
        "cutting_speed_roughing_m_min": 200.00,
        "cutting_speed_finishing_m_min": 300.00,
        "deep_pocket_penalty": 1.40,
        "thin_wall_penalty": 2.00,  # ductile, work hardening
    },
    "20910002": {  # Mosaz
        "category": "brass",
        "iso_group": "N",
        "hardness_hb": 90,
        "density": 8.50,
        "mrr_aggressive_cm3_min": 650.00,
        "mrr_finishing_cm3_min": 350.00,
        "cutting_speed_roughing_m_min": 250.00,
        "cutting_speed_finishing_m_min": 350.00,
        "deep_pocket_penalty": 1.30,
        "thin_wall_penalty": 1.70,
    },

    # === FREE-CUTTING STEEL (ISO P) ===
    "20910003": {  # Ocel automatová (11SMn30, 11SMnPb30)
        "category": "free_cutting_steel",
        "iso_group": "P",
        "hardness_hb": 180,
        "density": 7.85,
        "mrr_aggressive_cm3_min": 300.00,  # best machinability in steels
        "mrr_finishing_cm3_min": 180.00,
        "cutting_speed_roughing_m_min": 220.00,
        "cutting_speed_finishing_m_min": 280.00,
        "deep_pocket_penalty": 1.50,
        "thin_wall_penalty": 2.20,
    },

    # === STRUCTURAL STEEL (ISO P) ===
    "20910004": {  # Ocel konstrukční (C45, S355, E295)
        "category": "structural_steel",
        "iso_group": "P",
        "hardness_hb": 200,
        "density": 7.85,
        "mrr_aggressive_cm3_min": 250.00,
        "mrr_finishing_cm3_min": 150.00,
        "cutting_speed_roughing_m_min": 180.00,
        "cutting_speed_finishing_m_min": 220.00,
        "deep_pocket_penalty": 1.60,
        "thin_wall_penalty": 2.30,
    },

    # === ALLOY STEEL / CASE HARDENING (ISO P) ===
    "20910005": {  # Ocel legovaná (42CrMo4, 34CrNiMo6, 16MnCr5)
        "category": "alloy_steel",
        "iso_group": "P",
        "hardness_hb": 230,
        "density": 7.85,
        "mrr_aggressive_cm3_min": 180.00,  # lower MRR (higher strength)
        "mrr_finishing_cm3_min": 100.00,
        "cutting_speed_roughing_m_min": 160.00,
        "cutting_speed_finishing_m_min": 200.00,
        "deep_pocket_penalty": 1.80,  # higher penalty (tougher material)
        "thin_wall_penalty": 2.50,
    },

    # === TOOL STEEL (ISO H) ===
    "20910006": {  # Ocel nástrojová (X210Cr12, 90MnCrV8)
        "category": "tool_steel",
        "iso_group": "H",
        "hardness_hb": 250,
        "density": 7.85,
        "mrr_aggressive_cm3_min": 120.00,  # very low MRR (hard material)
        "mrr_finishing_cm3_min": 70.00,
        "cutting_speed_roughing_m_min": 120.00,
        "cutting_speed_finishing_m_min": 150.00,
        "deep_pocket_penalty": 2.20,  # severe penalty (hardness + abrasiveness)
        "thin_wall_penalty": 3.00,
    },

    # === STAINLESS STEEL (ISO M) ===
    "20910007": {  # Nerez (X5CrNi18-10, 1.4301/AISI 304)
        "category": "stainless_steel",
        "iso_group": "M",
        "hardness_hb": 180,
        "density": 7.90,
        "mrr_aggressive_cm3_min": 150.00,  # low MRR (work hardening, heat buildup)
        "mrr_finishing_cm3_min": 90.00,
        "cutting_speed_roughing_m_min": 140.00,
        "cutting_speed_finishing_m_min": 180.00,
        "deep_pocket_penalty": 2.00,  # severe (heat dissipation issues)
        "thin_wall_penalty": 2.80,
    },

    # === PLASTICS (ISO N) ===
    "20910008": {  # Plasty (POM, PA, PTFE, PEEK)
        "category": "plastics",
        "iso_group": "N",
        "hardness_hb": 30,
        "density": 1.20,
        "mrr_aggressive_cm3_min": 1200.00,  # very high MRR (low cutting forces)
        "mrr_finishing_cm3_min": 600.00,
        "cutting_speed_roughing_m_min": 400.00,
        "cutting_speed_finishing_m_min": 600.00,
        "deep_pocket_penalty": 1.20,  # minimal penalty (soft material)
        "thin_wall_penalty": 1.50,
    },
}


def get_material_data(material_code: str) -> Dict[str, Any]:
    """
    Get material data by 8-digit code.

    Args:
        material_code: 8-digit material group code (e.g., "20910005")

    Returns:
        Material data dict or empty dict if not found

    Example:
        >>> data = get_material_data("20910005")
        >>> data["mrr_aggressive_cm3_min"]
        180.0
    """
    return MATERIAL_DB.get(material_code, {})


def list_available_materials() -> list[str]:
    """
    List all available material codes.

    Returns:
        List of 8-digit material codes
    """
    return list(MATERIAL_DB.keys())
