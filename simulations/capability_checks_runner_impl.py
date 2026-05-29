"""Run FlowGuard checks for the flowpilot capability-routing model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import capability_model as model
from flowpilot_thin_parent_checks import (
    LAYERED_FULL_PROOF_PATHS,
    LAYERED_FULL_RESULT_PATHS,
    THIN_PROOF_PATHS,
    THIN_RESULT_PATHS,
    layered_full_input_fingerprint,
    run_layered_full_parent,
    run_thin_parent,
    valid_layered_full_proof,
    thin_input_fingerprint,
    valid_thin_proof,
    write_thin_proof,
)

from capability_checks_runner_contract import REQUIRED_LABELS, _state_id
from capability_checks_runner_graph import (
    CHECK_STATE_LIMIT,
    GRAPH_SHARD_DEPTH,
    GRAPH_STATE_LIMIT,
    MAX_INVARIANT_FAILURE_SAMPLES,
    PROGRESS_STEPS,
    _GraphBuildProgress,
    _build_reachable_graph,
    _check_loops,
    _check_progress,
    _check_hazard_cases,
    _graph_report_from_graph,
    _prefix_shards,
    _progress_enabled,
    _reverse_reachable,
    _run_sharded_graph_checks,
    _tarjan_scc,
    explore_state_graph,
)


ROOT = Path(__file__).resolve().parent
RUNNER_PATH = ROOT / "run_capability_checks.py"
RESULTS_PATH = THIN_RESULT_PATHS["capability"]
PROOF_PATH = THIN_PROOF_PATHS["capability"]
LAYERED_RESULTS_PATH = LAYERED_FULL_RESULT_PATHS["capability"]
LAYERED_PROOF_PATH = LAYERED_FULL_PROOF_PATHS["capability"]


def _emit_proof_reuse(check_name: str, path: Path) -> None:
    if _progress_enabled():
        print(
            f"[flowpilot-flowguard] proof_reused check={check_name} path={path}",
            file=sys.stderr,
            flush=True,
        )


def _current_input_fingerprint() -> str:
    return thin_input_fingerprint("capability", RUNNER_PATH)


def _layered_input_fingerprint() -> str:
    return layered_full_input_fingerprint("capability", RUNNER_PATH)


def _valid_proof(input_fingerprint: str) -> tuple[bool, str]:
    return valid_thin_proof(
        parent="capability",
        runner_path=RUNNER_PATH,
        result_path=RESULTS_PATH,
        proof_path=PROOF_PATH,
        input_fingerprint=input_fingerprint,
    )


def _write_proof(*, ok: bool, input_fingerprint: str) -> None:
    write_thin_proof(
        parent="capability",
        result_path=RESULTS_PATH,
        proof_path=PROOF_PATH,
        ok=ok,
        input_fingerprint=input_fingerprint,
    )


def _valid_layered_proof(input_fingerprint: str) -> tuple[bool, str]:
    return valid_layered_full_proof(
        parent="capability",
        runner_path=RUNNER_PATH,
        result_path=LAYERED_RESULTS_PATH,
        proof_path=LAYERED_PROOF_PATH,
        input_fingerprint=input_fingerprint,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fast", action="store_true", help="reuse a valid thin-parent proof when possible")
    parser.add_argument(
        "--full",
        action="store_true",
        help="run the layered full Capability parent regression instead of the routine thin parent check",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="force the selected Capability regression and ignore reusable proof files",
    )
    args = parser.parse_args(argv)

    input_fingerprint = _current_input_fingerprint()
    if args.fast and not args.force and not args.full:
        valid, reason = _valid_proof(input_fingerprint)
        if valid:
            _emit_proof_reuse("capability", PROOF_PATH)
            print(f"FlowGuard capability proof reused: {PROOF_PATH}")
            return 0
        print(f"FlowGuard capability proof not reused: {reason}")

    if not args.force and not args.full:
        payload = run_thin_parent(
            "capability",
            runner_path=RUNNER_PATH,
            result_path=RESULTS_PATH,
            proof_path=PROOF_PATH,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload.get("ok") else 1

    if args.full:
        layered_input_fingerprint = _layered_input_fingerprint()
        if args.fast and not args.force:
            valid, reason = _valid_layered_proof(layered_input_fingerprint)
            if valid:
                _emit_proof_reuse("capability-layered-full", LAYERED_PROOF_PATH)
                print(f"FlowGuard capability layered full proof reused: {LAYERED_PROOF_PATH}")
                return 0
            print(f"FlowGuard capability layered full proof not reused: {reason}")
        payload = run_layered_full_parent(
            "capability",
            runner_path=RUNNER_PATH,
            result_path=LAYERED_RESULTS_PATH,
            proof_path=LAYERED_PROOF_PATH,
            thin_result_path=RESULTS_PATH,
            thin_proof_path=PROOF_PATH,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
