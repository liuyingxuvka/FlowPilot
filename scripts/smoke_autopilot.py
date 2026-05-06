"""Run FlowPilot smoke checks."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> bool:
    completed = subprocess.run(command, cwd=ROOT, text=True)
    return completed.returncode == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fast", action="store_true", help="reuse valid slow-model proofs when possible")
    args = parser.parse_args(argv)

    meta_check = [sys.executable, "simulations/run_meta_checks.py"]
    capability_check = [sys.executable, "simulations/run_capability_checks.py"]
    if args.fast:
        meta_check.append("--fast")
        capability_check.append("--fast")

    checks = [
        [sys.executable, "simulations/run_card_instruction_coverage_checks.py"],
        [sys.executable, "simulations/run_release_tooling_checks.py"],
        [sys.executable, "simulations/run_startup_pm_review_checks.py"],
        [sys.executable, "simulations/run_barrier_equivalence_checks.py"],
        meta_check,
        capability_check,
    ]
    ok = True
    for command in checks:
        if not run(command):
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
