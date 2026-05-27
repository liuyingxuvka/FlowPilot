"""Run the FlowPilot final confidence hard gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from flowpilot_final_confidence_gate import (
    DEFAULT_RESULT_PATHS,
    evaluate_final_confidence,
    result_paths_for_dir,
    run_required_subchecks,
    write_json,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("tmp") / "final_confidence_gate",
        help="Directory for subcheck outputs when --run-checks is used.",
    )
    parser.add_argument(
        "--run-checks",
        action="store_true",
        help="Run required evidence producers before aggregating their JSON outputs.",
    )
    args = parser.parse_args(argv)

    if args.run_checks:
        subcheck_runs = run_required_subchecks(args.results_dir)
        result_paths = result_paths_for_dir(args.results_dir)
    else:
        subcheck_runs = []
        result_paths = DEFAULT_RESULT_PATHS

    report = evaluate_final_confidence(result_paths)
    report["result_type"] = "flowpilot_final_confidence_gate"
    report["subcheck_runs"] = subcheck_runs
    report["result_paths"] = {name: str(path) for name, path in result_paths.items()}

    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        write_json(args.json_out, report)
    print(output, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
