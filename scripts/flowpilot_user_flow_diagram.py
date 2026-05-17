"""Repository wrapper for the FlowPilot user-flow diagram entrypoint.

The source of truth lives in `skills/flowpilot/assets/flowpilot_user_flow_diagram.py`
so the packaged skill and repository CLI cannot drift apart.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "skills" / "flowpilot" / "assets"
ASSET_PATH = ASSET_DIR / "flowpilot_user_flow_diagram.py"


def _load_asset_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("flowpilot_asset_user_flow_diagram", ASSET_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load FlowPilot user-flow diagram asset: {ASSET_PATH}")
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    sys.path.insert(0, str(ASSET_DIR))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
    return module


_asset_module = _load_asset_module()

for _name in dir(_asset_module):
    if not _name.startswith("__"):
        globals().setdefault(_name, getattr(_asset_module, _name))

__all__ = sorted(_name for _name in globals() if not _name.startswith("_"))


if __name__ == "__main__":
    raise SystemExit(main())
