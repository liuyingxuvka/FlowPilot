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
    control_plane_friction_check = [
        sys.executable,
        "simulations/run_flowpilot_control_plane_friction_checks.py",
        "--skip-live-audit",
        "--json-out",
        "simulations/flowpilot_control_plane_friction_results.json",
    ]
    cross_plane_friction_check = [
        sys.executable,
        "simulations/run_flowpilot_cross_plane_friction_checks.py",
        "--skip-live-audit",
        "--json-out",
        "simulations/flowpilot_cross_plane_friction_results.json",
    ]
    prompt_isolation_check = [sys.executable, "simulations/run_prompt_isolation_checks.py"]
    persistent_router_daemon_check = [
        sys.executable,
        "simulations/run_flowpilot_persistent_router_daemon_checks.py",
        "--json-out",
        "simulations/flowpilot_persistent_router_daemon_results.json",
    ]
    daemon_startup_lock_check = [
        sys.executable,
        "simulations/run_flowpilot_daemon_startup_lock_checks.py",
        "--json-out",
        "simulations/flowpilot_daemon_startup_lock_results.json",
    ]
    daemon_controller_actions_check = [
        sys.executable,
        "simulations/run_flowpilot_daemon_controller_actions_checks.py",
        "--json-out",
        "simulations/flowpilot_daemon_controller_actions_results.json",
    ]
    daemon_wait_liveness_check = [
        sys.executable,
        "simulations/run_flowpilot_daemon_wait_liveness_checks.py",
        "--json-out",
        "simulations/flowpilot_daemon_wait_liveness_results.json",
    ]
    daemon_terminal_projection_check = [
        sys.executable,
        "simulations/run_flowpilot_daemon_terminal_projection_checks.py",
        "--json-out",
        "simulations/flowpilot_daemon_terminal_projection_results.json",
    ]
    model_mesh_check = [
        sys.executable,
        "simulations/run_flowpilot_model_mesh_checks.py",
        "--json-out",
        "simulations/flowpilot_model_mesh_results.json",
    ]
    model_hierarchy_check = [
        sys.executable,
        "simulations/run_flowpilot_model_hierarchy_checks.py",
        "--json-out",
        "simulations/flowpilot_model_hierarchy_results.json",
    ]
    structure_maintenance_check = [
        sys.executable,
        "simulations/run_flowpilot_structure_maintenance_checks.py",
        "--json-out",
        "simulations/flowpilot_structure_maintenance_results.json",
    ]
    router_facade_split_check = [
        sys.executable,
        "simulations/run_flowpilot_router_facade_split_checks.py",
        "--json-out",
        "simulations/flowpilot_router_facade_split_results.json",
    ]
    model_test_alignment_check = [
        sys.executable,
        "simulations/run_flowpilot_model_test_alignment_checks.py",
        "--json-out",
        "simulations/flowpilot_model_test_alignment_results.json",
    ]
    control_transaction_registry_check = [
        sys.executable,
        "simulations/run_flowpilot_control_transaction_registry_checks.py",
        "--json-out",
        "simulations/flowpilot_control_transaction_registry_results.json",
    ]
    if args.fast:
        meta_check.append("--fast")
        capability_check.append("--fast")

    checks = [
        [sys.executable, "simulations/run_card_instruction_coverage_checks.py"],
        [sys.executable, "simulations/run_release_tooling_checks.py"],
        [sys.executable, "simulations/run_startup_pm_review_checks.py"],
        [sys.executable, "simulations/run_command_refinement_checks.py"],
        [sys.executable, "simulations/run_flowpilot_reviewer_active_challenge_checks.py"],
        prompt_isolation_check,
        control_plane_friction_check,
        cross_plane_friction_check,
        persistent_router_daemon_check,
        daemon_startup_lock_check,
        daemon_controller_actions_check,
        daemon_wait_liveness_check,
        daemon_terminal_projection_check,
        control_transaction_registry_check,
        model_mesh_check,
        # Hierarchy consumes the current thin-parent proof files written by the
        # meta/capability checks, so refresh those proofs first.
        meta_check,
        capability_check,
        model_hierarchy_check,
        structure_maintenance_check,
        router_facade_split_check,
        model_test_alignment_check,
    ]
    ok = True
    for command in checks:
        if not run(command):
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
