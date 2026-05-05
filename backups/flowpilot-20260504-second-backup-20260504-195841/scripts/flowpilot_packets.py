"""Repo CLI wrapper for the installed FlowPilot packet runtime."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

from packet_runtime import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
