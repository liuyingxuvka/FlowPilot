"""Run FlowGuard checks for the flowpilot meta-process simulation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import meta_model as model
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

from meta_checks_runner_contract import REQUIRED_LABELS, _state_id
from meta_checks_runner_graph import (
    CHECK_STATE_LIMIT,
    GRAPH_SHARD_DEPTH,
    GRAPH_STATE_LIMIT,
    MAX_INVARIANT_FAILURE_SAMPLES,
    PROGRESS_STEPS,
    _GraphBuildProgress,
    _build_reachable_graph,
    _check_loops,
    _check_progress,
    _graph_report_from_graph,
    _prefix_shards,
    _progress_enabled,
    _reverse_reachable,
    _run_sharded_graph_checks,
    _tarjan_scc,
    explore_state_graph,
)


ROOT = Path(__file__).resolve().parent
RUNNER_PATH = ROOT / "run_meta_checks.py"
RESULTS_PATH = THIN_RESULT_PATHS["meta"]
PROOF_PATH = THIN_PROOF_PATHS["meta"]
LAYERED_RESULTS_PATH = LAYERED_FULL_RESULT_PATHS["meta"]
LAYERED_PROOF_PATH = LAYERED_FULL_PROOF_PATHS["meta"]
PARENT_ID = "meta"


def _emit_proof_reuse(check_name: str, path: Path) -> None:
    if _progress_enabled():
        print(
            f"[flowpilot-flowguard] proof_reused check={check_name} path={path}",
            file=sys.stderr,
            flush=True,
        )


def _current_input_fingerprint() -> str:
    return thin_input_fingerprint("meta", RUNNER_PATH)


def _layered_input_fingerprint() -> str:
    return layered_full_input_fingerprint("meta", RUNNER_PATH)


def _valid_proof(
    input_fingerprint: str,
    *,
    result_path: Path | None = None,
    proof_path: Path | None = None,
) -> tuple[bool, str]:
    return valid_thin_proof(
        parent=PARENT_ID,
        runner_path=RUNNER_PATH,
        result_path=result_path or RESULTS_PATH,
        proof_path=proof_path or PROOF_PATH,
        input_fingerprint=input_fingerprint,
    )


def _write_proof(
    *,
    ok: bool,
    input_fingerprint: str,
    result_path: Path | None = None,
    proof_path: Path | None = None,
) -> None:
    write_thin_proof(
        parent=PARENT_ID,
        result_path=result_path or RESULTS_PATH,
        proof_path=proof_path or PROOF_PATH,
        ok=ok,
        input_fingerprint=input_fingerprint,
    )


def _valid_layered_proof(
    input_fingerprint: str,
    *,
    result_path: Path | None = None,
    proof_path: Path | None = None,
) -> tuple[bool, str]:
    return valid_layered_full_proof(
        parent=PARENT_ID,
        runner_path=RUNNER_PATH,
        result_path=result_path or LAYERED_RESULTS_PATH,
        proof_path=proof_path or LAYERED_PROOF_PATH,
        input_fingerprint=input_fingerprint,
    )


def _proof_path_for(result_path: Path) -> Path:
    return result_path.with_suffix(".proof.json")


def _prepare_output_paths(*paths: Path) -> None:
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)


def _thin_result_path_for(layered_result_path: Path) -> Path:
    name = layered_result_path.name
    if name.endswith("_layered_full_results.json"):
        return layered_result_path.with_name(name.replace("_layered_full_results.json", "_thin_parent_results.json"))
    return layered_result_path.with_name(f"{PARENT_ID}_thin_parent_results.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fast", action="store_true", help="reuse a valid thin-parent proof when possible")
    parser.add_argument(
        "--full",
        action="store_true",
        help="run the layered full Meta parent regression instead of the routine thin parent check",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="force the selected Meta regression and ignore reusable proof files",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="write the selected result JSON to this path instead of the tracked default baseline",
    )
    parser.add_argument(
        "--proof-out",
        type=Path,
        default=None,
        help="write the selected proof JSON to this path; defaults beside --json-out when provided",
    )
    parser.add_argument(
        "--thin-json-out",
        type=Path,
        default=None,
        help="with --full, write the refreshed thin-parent result to this path",
    )
    parser.add_argument(
        "--thin-proof-out",
        type=Path,
        default=None,
        help="with --full, write the refreshed thin-parent proof to this path",
    )
    args = parser.parse_args(argv)

    result_path = args.json_out or (LAYERED_RESULTS_PATH if args.full else RESULTS_PATH)
    proof_path = args.proof_out or (_proof_path_for(result_path) if args.json_out else (LAYERED_PROOF_PATH if args.full else PROOF_PATH))
    thin_result_path = args.thin_json_out or (_thin_result_path_for(result_path) if args.full and args.json_out else RESULTS_PATH)
    thin_proof_path = args.thin_proof_out or (
        _proof_path_for(thin_result_path) if args.full and (args.json_out or args.thin_json_out) else PROOF_PATH
    )

    input_fingerprint = _current_input_fingerprint()
    if args.fast and not args.force and not args.full:
        valid, reason = _valid_proof(input_fingerprint, result_path=result_path, proof_path=proof_path)
        if valid:
            _emit_proof_reuse("meta", proof_path)
            print(f"FlowGuard meta proof reused: {proof_path}")
            return 0
        print(f"FlowGuard meta proof not reused: {reason}")

    if not args.full:
        _prepare_output_paths(result_path, proof_path)
        payload = run_thin_parent(
            PARENT_ID,
            runner_path=RUNNER_PATH,
            result_path=result_path,
            proof_path=proof_path,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload.get("ok") else 1

    if args.full:
        layered_input_fingerprint = _layered_input_fingerprint()
        if args.fast and not args.force:
            valid, reason = _valid_layered_proof(layered_input_fingerprint, result_path=result_path, proof_path=proof_path)
            if valid:
                _emit_proof_reuse("meta-layered-full", proof_path)
                print(f"FlowGuard meta layered full proof reused: {proof_path}")
                return 0
            print(f"FlowGuard meta layered full proof not reused: {reason}")
        _prepare_output_paths(result_path, proof_path, thin_result_path, thin_proof_path)
        payload = run_layered_full_parent(
            PARENT_ID,
            runner_path=RUNNER_PATH,
            result_path=result_path,
            proof_path=proof_path,
            thin_result_path=thin_result_path,
            thin_proof_path=thin_proof_path,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
