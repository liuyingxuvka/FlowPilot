"""Write current execution receipts for complete-workstream fake-AI profiles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from flowpilot_complete_workstream_fake_ai_execution import run_all_profiles


RESULTS_PATH = Path(__file__).resolve().with_name(
    "flowpilot_complete_workstream_fake_ai_results.json"
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args(argv)
    result = run_all_profiles()
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
