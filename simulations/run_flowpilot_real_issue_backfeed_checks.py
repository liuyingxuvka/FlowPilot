"""Run FlowPilot real-issue backfeed registry checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:  # pragma: no cover
    from . import flowpilot_real_issue_backfeed as model
except ImportError:  # pragma: no cover
    import flowpilot_real_issue_backfeed as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "flowpilot_real_issue_backfeed_results.json"


def run_checks() -> dict[str, object]:
    return model.build_report()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args()

    report = run_checks()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else f"FlowPilot real-issue backfeed ok={report['ok']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
