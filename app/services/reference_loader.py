"""GESTIMA - Referenční data (stroje, materiály, typy kroků)"""

from typing import List, Dict, Any
from pathlib import Path
import pandas as pd
from functools import lru_cache

from app.config import settings
from app.services.feature_definitions import FEATURE_FIELDS


@lru_cache(maxsize=1)
def get_machines() -> List[Dict[str, Any]]:
    excel_path = settings.DATA_DIR / "machines.xlsx"
    
    if excel_path.exists():
        df = pd.read_excel(excel_path)
        return df.to_dict(orient="records")
    
    return [
        {"id": 1, "name": "NLX 2000", "type": "lathe_mill", "hourly_rate": 1200, "max_rpm": 4000, "has_bar_feeder": True},
        {"id": 2, "name": "NZX 2000", "type": "lathe_mill", "hourly_rate": 1500, "max_rpm": 5000, "has_bar_feeder": True},
        {"id": 3, "name": "PUMA 2600", "type": "lathe", "hourly_rate": 900, "max_rpm": 3500, "has_bar_feeder": True},
        {"id": 4, "name": "Bruska", "type": "grinding", "hourly_rate": 800, "max_rpm": 2000, "has_bar_feeder": False},
    ]


@lru_cache(maxsize=1)
def get_material_groups() -> List[Dict[str, Any]]:
    return [
        {"code": "automatova_ocel", "name": "Automatová ocel", "density": 7.85, "price_per_kg": 35, "color": "#42A5F5"},
        {"code": "konstrukcni_ocel", "name": "Konstrukční ocel", "density": 7.85, "price_per_kg": 28, "color": "#2196F3"},
        {"code": "legovana_ocel", "name": "Legovaná ocel", "density": 7.85, "price_per_kg": 45, "color": "#1976D2"},
        {"code": "nastrojova_ocel", "name": "Nástrojová ocel", "density": 7.85, "price_per_kg": 85, "color": "#1565C0"},
        {"code": "nerez_feriticka", "name": "Nerez feritická", "density": 7.75, "price_per_kg": 95, "color": "#FFD54F"},
        {"code": "nerez_austeniticka", "name": "Nerez austenitická", "density": 7.90, "price_per_kg": 120, "color": "#FFC107"},
        {"code": "hlinik", "name": "Hliník", "density": 2.70, "price_per_kg": 75, "color": "#4CAF50"},
        {"code": "mosaz_bronz", "name": "Mosaz / Bronz", "density": 8.50, "price_per_kg": 180, "color": "#388E3C"},
        {"code": "med", "name": "Měď", "density": 8.96, "price_per_kg": 220, "color": "#2E7D32"},
        {"code": "plasty", "name": "Plasty", "density": 1.40, "price_per_kg": 45, "color": "#81C784"},
    ]


def get_material_properties(material_group: str) -> Dict[str, float]:
    for mat in get_material_groups():
        if mat["code"] == material_group:
            return {"density": mat["density"], "price_per_kg": mat["price_per_kg"]}
    return {"density": 7.85, "price_per_kg": 30}


def get_feature_types() -> List[Dict[str, Any]]:
    result = []
    for code, config in FEATURE_FIELDS.items():
        result.append({
            "code": code,
            "name": config.get("name", code),
            "icon": config.get("icon", "🔧"),
            "category": config.get("category", "other"),
            "fields": config.get("fields", []),
            "cutting": config.get("cutting", []),
        })
    return result


def clear_cache():
    get_machines.cache_clear()
    get_material_groups.cache_clear()
