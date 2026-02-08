"""GESTIMA - Configuration module

Exports:
- material_database: Material MRR lookup table
- settings: App configuration from parent app/config.py
"""

# Material database (local to this subpackage)
from .material_database import (
    MATERIAL_DB,
    get_material_data,
    list_available_materials,
)

# Settings from parent app/config.py (lazy import to avoid circular dependency)
def get_settings():
    """Lazy import of settings to avoid circular dependency."""
    import sys
    from pathlib import Path
    import importlib.util

    parent_dir = Path(__file__).parent.parent
    config_file = parent_dir / "config.py"

    spec = importlib.util.spec_from_file_location("_config", config_file)
    _config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_config)

    return _config.settings

__all__ = [
    "MATERIAL_DB",
    "get_material_data",
    "list_available_materials",
    "get_settings",
]
