"""Repository wrapper for the FlowPilot unified runtime entrypoint."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSET_RUNTIME = ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_runtime.py"


def _load_asset_runtime():
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
