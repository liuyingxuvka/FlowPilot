"""Run FlowGuard model-maturation closure checks for FlowPilot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import flowpilot_model_maturation_model as model


def build_report() -> dict[str, object]:
    return model.build_report()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=Path(model.RESULT_PATH),
        help="Path for writing the JSON result payload.",
    )
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
