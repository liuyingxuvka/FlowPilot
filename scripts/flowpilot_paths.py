"""Compatibility wrapper for FlowPilot path helpers.

The source of truth lives in `skills/flowpilot/assets/flowpilot_paths.py` so
the packaged skill and repository helper imports cannot drift apart.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
ASSET_PATH = ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_paths.py"


def _load_asset_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("flowpilot_asset_paths", ASSET_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load FlowPilot path helper asset: {ASSET_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_asset_module = _load_asset_module()

for _name in dir(_asset_module):
    if not _name.startswith("__"):
        globals().setdefault(_name, getattr(_asset_module, _name))

__all__ = sorted(_name for _name in globals() if not _name.startswith("_"))
