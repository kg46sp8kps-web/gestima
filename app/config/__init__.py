"""GESTIMA - Configuration module

Re-exports settings from parent app/config.py.
"""

import importlib.util
from pathlib import Path

try:
    config_py_path = Path(__file__).parent.parent / "config.py"
    spec = importlib.util.spec_from_file_location("_parent_config", config_py_path)
    _parent_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_parent_config)

    settings = _parent_config.settings
    Settings = _parent_config.Settings
except Exception as e:
    import warnings
    warnings.warn(f"Could not import settings from parent config.py: {e}")
    settings = None
    Settings = None

__all__ = ["settings", "Settings"]
