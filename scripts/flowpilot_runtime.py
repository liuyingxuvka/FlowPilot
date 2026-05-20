"""Repository wrapper for the FlowPilot unified runtime entrypoint."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "skills" / "flowpilot" / "assets"
ASSET_RUNTIME = ASSET_DIR / "flowpilot_runtime.py"


def _load_asset_runtime():
    asset_dir_text = str(ASSET_DIR)
    if asset_dir_text not in sys.path:
        sys.path.insert(0, asset_dir_text)
    spec = importlib.util.spec_from_file_location("flowpilot_asset_runtime", ASSET_RUNTIME)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load FlowPilot runtime from {ASSET_RUNTIME}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    return int(_load_asset_runtime().main(argv))


def parse_args(argv: list[str]):
    return _load_asset_runtime().parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
