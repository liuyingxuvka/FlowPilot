"""Run FlowGuard checks for the flowpilot capability-routing model."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import capability_model as model
from flowpilot_thin_parent_checks import (
    LAYERED_FULL_PROOF_PATHS,
    LAYERED_FULL_RESULT_PATHS,
    THIN_PROOF_PATHS,
    THIN_RESULT_PATHS,
    layered_full_input_fingerprint,
    legacy_input_fingerprint,
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
LEGACY_RESULTS_PATH = ROOT / "capability_results.json"
LEGACY_PROOF_PATH = ROOT / "capability_results.proof.json"
RESULTS_PATH = THIN_RESULT_PATHS["capability"]
PROOF_PATH = THIN_PROOF_PATHS["capability"]
LAYERED_RESULTS_PATH = LAYERED_FULL_RESULT_PATHS["capability"]
LAYERED_PROOF_PATH = LAYERED_FULL_PROOF_PATHS["capability"]
PROOF_SCHEMA = 1


def _emit_proof_reuse(check_name: str, path: Path) -> None:
    if _progress_enabled():
        print(
            f"[flowpilot-flowguard] proof_reused check={check_name} path={path}",
            file=sys.stderr,
            flush=True,
        )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _current_input_fingerprint() -> str:
    return thin_input_fingerprint("capability", RUNNER_PATH)


def _legacy_input_fingerprint() -> str:
    return legacy_input_fingerprint("capability")


def _layered_input_fingerprint() -> str:
    return layered_full_input_fingerprint("capability", RUNNER_PATH)


def _legacy_file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _valid_legacy_proof(input_fingerprint: str) -> tuple[bool, str]:
    if not LEGACY_PROOF_PATH.exists():
        return False, "proof missing"
    if not LEGACY_RESULTS_PATH.exists():
        return False, "results missing"
    try:
        proof = json.loads(LEGACY_PROOF_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False, "proof is not valid JSON"

    if proof.get("schema") != PROOF_SCHEMA:
        return False, "proof schema changed"
    if proof.get("check") != "capability":
        return False, "proof check changed"
    if proof.get("ok") is not True:
        return False, "previous proof was not successful"
    if proof.get("input_fingerprint") != input_fingerprint:
        return False, "input fingerprint changed"
    if proof.get("result_fingerprint") != _legacy_file_sha256(LEGACY_RESULTS_PATH):
        return False, "result fingerprint changed"
    return True, "valid proof"


def _write_legacy_proof(*, ok: bool, input_fingerprint: str) -> None:
    payload = {
        "schema": PROOF_SCHEMA,
        "check": "capability",
        "ok": ok,
        "input_fingerprint": input_fingerprint,
        "result_fingerprint": _legacy_file_sha256(LEGACY_RESULTS_PATH),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    LEGACY_PROOF_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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
        "--legacy-full",
        action="store_true",
        help="run the legacy monolithic Capability graph regression explicitly",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="force the legacy full Capability graph regression and ignore existing full proof",
    )
    args = parser.parse_args(argv)

    input_fingerprint = _current_input_fingerprint()
    if args.fast and not args.force and not args.full and not args.legacy_full:
        valid, reason = _valid_proof(input_fingerprint)
        if valid:
            _emit_proof_reuse("capability", PROOF_PATH)
            print(f"FlowGuard capability proof reused: {PROOF_PATH}")
            return 0
        print(f"FlowGuard capability proof not reused: {reason}")

    if not args.force and not args.full and not args.legacy_full:
        payload = run_thin_parent(
            "capability",
            runner_path=RUNNER_PATH,
            result_path=RESULTS_PATH,
            proof_path=PROOF_PATH,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload.get("ok") else 1

    if args.full and not args.legacy_full:
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

    legacy_input_fingerprint = _legacy_input_fingerprint()
    if args.legacy_full and args.fast and not args.force:
        valid, reason = _valid_legacy_proof(legacy_input_fingerprint)
        if valid:
            _emit_proof_reuse("capability", LEGACY_PROOF_PATH)
            print(f"FlowGuard capability full proof reused: {LEGACY_PROOF_PATH}")
            return 0
        print(f"FlowGuard capability full proof not reused: {reason}")

    (
        graph_report,
        progress_report,
        loop_report,
        default_success_state,
        ui_success_state,
    ) = _run_sharded_graph_checks()
    hazard_report = _check_hazard_cases(
        default_success_state=default_success_state,
        ui_success_state=ui_success_state,
    )
    ok = (
        graph_report["ok"]
        and progress_report["ok"]
        and loop_report["ok"]
        and hazard_report["ok"]
    )

    payload = {
        "graph": graph_report,
        "hazard": hazard_report,
        "result_type": "legacy_full_parent",
        "progress": progress_report,
        "loop": loop_report,
    }
    LEGACY_RESULTS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    _write_legacy_proof(ok=ok, input_fingerprint=legacy_input_fingerprint)

    print("=== Capability State Graph ===")
    print(json.dumps(graph_report, indent=2, sort_keys=True))
    print()
    print("=== Progress Review ===")
    print(json.dumps(progress_report, indent=2, sort_keys=True))
    print()
    print("=== Loop/Stuck Review ===")
    print(json.dumps(loop_report, indent=2, sort_keys=True))
    print()
    print("=== Hazard Regression Review ===")
    print(json.dumps(hazard_report, indent=2, sort_keys=True))

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
