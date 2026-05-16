"""Run the long-check observability FlowGuard review model."""

from __future__ import annotations

import argparse

from long_check_observability_model import run_long_check_observability_review


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--text",
        action="store_true",
        help="Print the legacy human-readable scenario review instead of JSON.",
    )
    args = parser.parse_args()

    report = run_long_check_observability_review()
    if args.text:
        print(report.format_text(max_counterexamples=2))
    else:
        print(report.to_json_text())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
