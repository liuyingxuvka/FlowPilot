"""Run FlowGuard similarity-convergence checks for FlowPilot maintenance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from flowpilot_similarity_convergence_model import RESULTS_PATH, build_report


DEFAULT_RESULTS_PATH = Path(__file__).resolve().parent / Path(RESULTS_PATH).name


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_RESULTS_PATH)
    args = parser.parse_args(argv)

    report = build_report()
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
