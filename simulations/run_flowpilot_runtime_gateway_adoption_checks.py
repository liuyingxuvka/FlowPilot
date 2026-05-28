"""Run FlowPilot runtime gateway adoption checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import flowpilot_runtime_gateway_adoption


RESULTS_PATH = Path(__file__).with_name("flowpilot_runtime_gateway_adoption_results.json")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args(argv)
    report = flowpilot_runtime_gateway_adoption.build_report()
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
