"""Compatibility entrypoint for the FlowPilot install self-check."""

from __future__ import annotations

from install_checks import main


if __name__ == "__main__":
    raise SystemExit(main())
