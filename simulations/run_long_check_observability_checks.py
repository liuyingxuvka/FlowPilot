"""Run the long-check observability FlowGuard review model."""

from __future__ import annotations

from long_check_observability_model import run_long_check_observability_review


def main() -> int:
    report = run_long_check_observability_review()
    print(report.format_text(max_counterexamples=2))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
