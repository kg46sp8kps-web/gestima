"""GESTIMA - Configuration module

Exports:
- material_database: Material MRR lookup table
- settings: App configuration from parent app/config.py

Note: This __init__.py exists because app/config/ is a subpackage containing
material_database.py. The main settings are in app/config.py (parent directory).
"""

# Material database (local to this subpackage)
from .material_database import (
    MATERIAL_DB,
    get_material_data,
    list_available_materials,
)

# Import settings from parent directory's config.py
# We need to import from the module file, not the package
import sys
from pathlib import Path

# Add parent directory to path temporarily
parent_path = str(Path(__file__).parent.parent)
if parent_path not in sys.path:
    sys.path.insert(0, parent_path)

# Import from config.py in parent directory
# This works because Python will find config.py before config/__init__.py
# when we import from parent scope
try:
    # Import Settings class and settings instance from parent config.py
    import importlib.util
    config_py_path = Path(__file__).parent.parent / "config.py"
    spec = importlib.util.spec_from_file_location("_parent_config", config_py_path)
    _parent_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_parent_config)

    settings = _parent_config.settings
    Settings = _parent_config.Settings
except Exception as e:
    # Fallback for edge cases
    import warnings
    warnings.warn(f"Could not import settings from parent config.py: {e}")
    settings = None
    Settings = None

__all__ = [
    "MATERIAL_DB",
    "get_material_data",
    "list_available_materials",
    "settings",
    "Settings",
]
