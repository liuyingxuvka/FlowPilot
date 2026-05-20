"""Run thin child checks for persistent daemon waits and liveness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from flowpilot_persistent_router_daemon_child_models import build_report


ROOT = Path(__file__).resolve().parent
FAMILY = "wait_liveness"
RESULTS_PATH = ROOT / "flowpilot_daemon_wait_liveness_results.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args()

    report = build_report(FAMILY)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.json_out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
