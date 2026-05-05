"""Run FlowPilot smoke checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> bool:
    completed = subprocess.run(command, cwd=ROOT, text=True)
    return completed.returncode == 0


def main() -> int:
    checks = [
        [sys.executable, "simulations/run_card_instruction_coverage_checks.py"],
        [sys.executable, "simulations/run_release_tooling_checks.py"],
        [sys.executable, "simulations/run_startup_pm_review_checks.py"],
        [sys.executable, "simulations/run_barrier_equivalence_checks.py"],
        [sys.executable, "simulations/run_meta_checks.py"],
        [sys.executable, "simulations/run_capability_checks.py"],
    ]
    ok = True
    for command in checks:
        if not run(command):
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
