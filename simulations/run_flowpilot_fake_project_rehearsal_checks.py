"""Run black-box fake-project rehearsal checks for the new FlowPilot entrypoint."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from flowguard import Explorer

try:  # pragma: no cover
    from . import flowpilot_fake_project_rehearsal_model as model
except ImportError:  # pragma: no cover
    import flowpilot_fake_project_rehearsal_model as model


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
ENTRYPOINT = REPO_ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_new.py"
RESULTS_PATH = ROOT / "flowpilot_fake_project_rehearsal_results.json"
DEFAULT_WORK_ROOT = REPO_ROOT / "tmp" / "flowpilot_fake_project_rehearsal"
FAKE_STARTUP_TEXT = "Build a fake calculator CLI with docs, tests, FlowGuard evidence, review, validation, and closure."
ROLE_CHAIN = (
    ("task", "pm", "fake-pm", "fake PM planned and executed the fake project route."),
    ("flowguard_check", "flowguard_operator", "fake-flowguard", "fake FlowGuard evidence passed for the PM result."),
    ("review", "reviewer", "fake-reviewer", "fake reviewer accepted the FlowGuard-backed result."),
    ("validation", "validator", "fake-validator", "fake validation evidence is current."),
    ("closure", "closure_officer", "fake-closure", "fake closure officer confirmed the backward chain."),
)
REQUIRED_PACKET_KINDS = [kind for kind, _responsibility, _agent, _body in ROLE_CHAIN]


class RehearsalFailure(AssertionError):
    """Raised when a black-box rehearsal observation violates the contract."""


def _ensure(condition: bool, message: str) -> None:
    if not condition:
        raise RehearsalFailure(message)


def _redact_args(args: tuple[str, ...]) -> list[str]:
    redacted: list[str] = []
    redact_next = False
    for arg in args:
        if redact_next:
            redacted.append("<sealed>")
            redact_next = False
            continue
        redacted.append(arg)
        if arg in {"--body", "--startup-text", "--headless-startup-text"}:
            redact_next = True
    return redacted


def _payload_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {}
    summary: dict[str, Any] = {"ok": payload.get("ok")}
    if "error" in payload:
        summary["error"] = payload["error"]
    if "mode" in payload:
        summary["mode"] = payload["mode"]
    if "lease_id" in payload:
        summary["lease_id"] = payload["lease_id"]
    if "result_id" in payload:
        summary["result_id"] = payload["result_id"]
    action = payload.get("next_action")
    if isinstance(action, dict):
        summary["next_action"] = {
            "action_type": action.get("action_type", ""),
            "responsibility": action.get("responsibility", ""),
            "subject_id": action.get("subject_id", ""),
        }
    return summary


def _parse_json(stdout: str) -> dict[str, Any] | None:
    text = stdout.strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _run_cli(root: Path, command_log: list[dict[str, Any]], *args: str, expect_ok: bool = True) -> dict[str, Any]:
    command = [sys.executable, "-B", str(ENTRYPOINT), "--root", str(root), "--json", *args]
    completed = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    payload = _parse_json(completed.stdout)
    command_log.append(
        {
            "args": _redact_args(args),
            "returncode": completed.returncode,
            "payload": _payload_summary(payload),
            "stderr_excerpt": completed.stderr.strip()[:300],
        }
    )
    if expect_ok:
        _ensure(completed.returncode == 0, f"CLI command failed: {args[0]} {completed.stderr.strip()}")
        _ensure(payload is not None, f"CLI command did not return JSON: {args[0]}")
        _ensure(payload.get("ok") is True, f"CLI command returned ok=false: {args[0]} {payload}")
    return payload or {"ok": False, "error": completed.stderr.strip(), "returncode": completed.returncode}


def _run_raw_cli(root: Path, command_log: list[dict[str, Any]], *args: str) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, "-B", str(ENTRYPOINT), "--root", str(root), *args]
    completed = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    command_log.append(
        {
            "args": _redact_args(args),
            "returncode": completed.returncode,
            "stdout_excerpt": completed.stdout[:300],
            "stderr_excerpt": completed.stderr.strip()[:300],
        }
    )
    return completed


def _reset_scenario_root(work_root: Path, name: str) -> Path:
    root = (work_root / name).resolve()
    work_root_resolved = work_root.resolve()
    _ensure(str(root).startswith(str(work_root_resolved)), f"refusing to reset path outside work root: {root}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _status_projection(root: Path, command_log: list[dict[str, Any]]) -> dict[str, Any]:
    payload = _run_cli(root, command_log, "status")
    projection = payload.get("status")
    _ensure(isinstance(projection, dict), "status command did not return a projection")
    return projection


def _packet_row(projection: dict[str, Any], packet_id: str) -> dict[str, Any]:
    for packet in projection.get("packets", []):
        if packet.get("packet_id") == packet_id:
            return packet
    raise RehearsalFailure(f"missing packet row in public status: {packet_id}")


def _assert_public_projection_is_sealed(projection: dict[str, Any]) -> None:
    serialized = json.dumps(projection, sort_keys=True)
    _ensure(projection.get("sealed_bodies_visible") is False, "public status claims sealed bodies are visible")
    _ensure(FAKE_STARTUP_TEXT not in serialized, "public status leaked fake startup text")
    _ensure("SEALED_RESULT_BODY" not in serialized, "public status leaked sealed fake AI result body")
    for packet in projection.get("packets", []):
        _ensure(packet.get("sealed_body_hidden") is True, f"packet body is not marked hidden: {packet}")


def _complete_full_packet_chain(
    root: Path,
    command_log: list[dict[str, Any]],
    current_payload: dict[str, Any],
) -> dict[str, Any]:
    completed_packets: list[dict[str, str]] = []
    for expected_kind, responsibility, agent_id, body in ROLE_CHAIN:
        action = current_payload.get("next_action")
        _ensure(isinstance(action, dict), f"missing next action before {expected_kind}")
        _ensure(action.get("action_type") == "lease_agent", f"expected lease action before {expected_kind}: {action}")
        _ensure(action.get("responsibility") == responsibility, f"wrong responsibility before {expected_kind}: {action}")
        packet_id = str(action.get("subject_id", ""))
        _ensure(packet_id, f"missing packet id before {expected_kind}")

        projection = _status_projection(root, command_log)
        packet = _packet_row(projection, packet_id)
        _ensure(packet.get("packet_kind") == expected_kind, f"wrong packet kind for {packet_id}: {packet}")

        lease_payload = _run_cli(
            root,
            command_log,
            "lease-agent",
            "--packet-id",
            packet_id,
            "--responsibility",
            responsibility,
            "--agent-id",
            agent_id,
            "--host-kind",
            "fake",
        )
        lease_id = str(lease_payload.get("lease_id", ""))
        _ensure(lease_id, f"missing lease id for {expected_kind}")
        _ensure(lease_payload["next_action"]["action_type"] == "wait_for_ack", f"expected wait_for_ack: {lease_payload}")

        ack_payload = _run_cli(root, command_log, "ack", "--lease-id", lease_id, "--packet-id", packet_id)
        _ensure(ack_payload["next_action"]["action_type"] == "wait_for_result", f"expected wait_for_result: {ack_payload}")

        current_payload = _run_cli(
            root,
            command_log,
            "submit-result",
            "--lease-id",
            lease_id,
            "--packet-id",
            packet_id,
            "--body",
            f"SEALED_RESULT_BODY: {body}",
        )
        completed_packets.append({"packet_id": packet_id, "packet_kind": expected_kind, "lease_id": lease_id})

    final_action = current_payload.get("next_action", {})
    _ensure(final_action.get("action_type") == "terminal_complete", f"final action was not terminal_complete: {final_action}")
    projection = _status_projection(root, command_log)
    _assert_public_projection_is_sealed(projection)
    _ensure(projection.get("next_action", {}).get("action_type") == "terminal_complete", "public status is not terminal")
    _ensure(projection.get("closure", {}).get("decision") == "complete", "closure did not complete")

    packet_kinds = [packet.get("packet_kind") for packet in projection.get("packets", [])]
    _ensure(packet_kinds == REQUIRED_PACKET_KINDS, f"unexpected packet kind chain: {packet_kinds}")
    _ensure(all(packet.get("status") == "accepted" for packet in projection.get("packets", [])), "not all packets are accepted")
    _ensure(not [lease for lease in projection.get("leases", []) if lease.get("status") == "active"], "terminal status has active leases")
    _ensure(all(lease.get("ack_received") for lease in projection.get("leases", [])), "a terminal lease is missing ACK")
    _ensure(all(lease.get("packet_id") for lease in projection.get("leases", [])), "a terminal lease is missing packet id")
    _ensure(projection.get("flowguard") and projection["flowguard"][0].get("decision") == "pass", "FlowGuard pass evidence missing")
    _ensure(
        projection.get("validation_evidence") and projection["validation_evidence"][0].get("status") == "passed",
        "validation evidence missing",
    )
    _ensure(not projection.get("blockers"), f"terminal public status has blockers: {projection.get('blockers')}")
    return {
        "terminal_action": final_action,
        "packet_kinds": packet_kinds,
        "completed_packets": completed_packets,
        "lease_count": len(projection.get("leases", [])),
        "sealed_bodies_visible": projection.get("sealed_bodies_visible"),
    }


def _start_rehearsal(root: Path, command_log: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    payload = _run_cli(
        root,
        command_log,
        "start",
        "--run-id",
        run_id,
        "--headless-startup-text",
        FAKE_STARTUP_TEXT,
    )
    _ensure(payload.get("mode") == "rehearsal", "headless startup should be recorded as rehearsal mode")
    _ensure(payload.get("next_action", {}).get("action_type") == "lease_agent", "startup did not request first lease")
    _ensure(payload.get("next_action", {}).get("responsibility") == "pm", "startup did not request PM first")
    projection = payload.get("status", {})
    _ensure(isinstance(projection, dict), "startup did not include public status")
    _assert_public_projection_is_sealed(projection)
    return payload


def _scenario_normal(work_root: Path) -> dict[str, Any]:
    command_log: list[dict[str, Any]] = []
    root = _reset_scenario_root(work_root, "normal_full_path")
    start_payload = _start_rehearsal(root, command_log, "run-fake-normal")
    chain = _complete_full_packet_chain(root, command_log, start_payload)
    return {
        "name": "normal_full_path",
        "ok": True,
        "root": str(root),
        "observations": chain,
        "commands": command_log,
    }


def _scenario_wrong_role_recovery(work_root: Path) -> dict[str, Any]:
    command_log: list[dict[str, Any]] = []
    root = _reset_scenario_root(work_root, "wrong_role_recovery")
    start_payload = _start_rehearsal(root, command_log, "run-fake-wrong-role")
    pm_packet = str(start_payload["next_action"]["subject_id"])

    rejected = _run_cli(
        root,
        command_log,
        "lease-agent",
        "--packet-id",
        pm_packet,
        "--responsibility",
        "flowguard_operator",
        "--agent-id",
        "fake-wrong-role",
        "--host-kind",
        "fake",
        expect_ok=False,
    )
    _ensure(rejected.get("ok") is False, f"wrong-role lease was not rejected: {rejected}")
    _ensure("lease responsibility does not match packet" in str(rejected.get("error", "")), f"wrong rejection error: {rejected}")

    chain = _complete_full_packet_chain(root, command_log, start_payload)
    return {
        "name": "wrong_role_recovery",
        "ok": True,
        "root": str(root),
        "observations": {
            "wrong_role_rejected": True,
            "recovered_to_terminal": chain["terminal_action"]["action_type"] == "terminal_complete",
            "packet_kinds": chain["packet_kinds"],
        },
        "commands": command_log,
    }


def _scenario_missing_ack_block(work_root: Path) -> dict[str, Any]:
    command_log: list[dict[str, Any]] = []
    root = _reset_scenario_root(work_root, "missing_ack_block")
    start_payload = _start_rehearsal(root, command_log, "run-fake-missing-ack")
    pm_packet = str(start_payload["next_action"]["subject_id"])

    lease_payload = _run_cli(
        root,
        command_log,
        "lease-agent",
        "--packet-id",
        pm_packet,
        "--responsibility",
        "pm",
        "--agent-id",
        "fake-pm-no-ack",
        "--host-kind",
        "fake",
    )
    lease_id = str(lease_payload["lease_id"])
    result_payload = _run_cli(
        root,
        command_log,
        "submit-result",
        "--lease-id",
        lease_id,
        "--packet-id",
        pm_packet,
        "--body",
        "SEALED_RESULT_BODY: fake PM tried to submit without ACK.",
    )
    _ensure(result_payload.get("next_action", {}).get("action_type") == "repair_packet", "missing ACK did not expose repair boundary")
    projection = _status_projection(root, command_log)
    _assert_public_projection_is_sealed(projection)
    packet = _packet_row(projection, pm_packet)
    _ensure(packet.get("status") == "result_blocked", f"missing ACK packet not blocked: {packet}")
    _ensure(projection.get("next_action", {}).get("action_type") == "repair_packet", "status did not stay on repair boundary")
    blockers = projection.get("blockers", [])
    _ensure(any("missing_ack" in str(blocker) for blocker in blockers), f"missing ACK blocker absent: {blockers}")
    _ensure(projection.get("closure", {}).get("decision") != "complete", "missing ACK reached closure")
    return {
        "name": "missing_ack_block",
        "ok": True,
        "root": str(root),
        "observations": {
            "result_status": packet.get("status"),
            "next_action": projection.get("next_action", {}).get("action_type"),
            "blockers": blockers,
        },
        "commands": command_log,
    }


def _scenario_ack_only_wait(work_root: Path) -> dict[str, Any]:
    command_log: list[dict[str, Any]] = []
    root = _reset_scenario_root(work_root, "ack_only_wait")
    start_payload = _start_rehearsal(root, command_log, "run-fake-ack-only")
    pm_packet = str(start_payload["next_action"]["subject_id"])

    lease_payload = _run_cli(
        root,
        command_log,
        "lease-agent",
        "--packet-id",
        pm_packet,
        "--responsibility",
        "pm",
        "--agent-id",
        "fake-pm-ack-only",
        "--host-kind",
        "fake",
    )
    _run_cli(root, command_log, "ack", "--lease-id", str(lease_payload["lease_id"]), "--packet-id", pm_packet)
    projection = _status_projection(root, command_log)
    _assert_public_projection_is_sealed(projection)
    _ensure(projection.get("next_action", {}).get("action_type") == "wait_for_result", "ACK-only did not wait for result")
    _ensure(projection.get("closure", {}).get("decision") != "complete", "ACK-only reached closure")
    return {
        "name": "ack_only_wait",
        "ok": True,
        "root": str(root),
        "observations": {
            "next_action": projection.get("next_action", {}).get("action_type"),
            "closure": projection.get("closure", {}).get("decision"),
        },
        "commands": command_log,
    }


def _scenario_retired_side_command(work_root: Path) -> dict[str, Any]:
    command_log: list[dict[str, Any]] = []
    root = _reset_scenario_root(work_root, "retired_side_command")
    help_result = _run_raw_cli(root, command_log, "--help")
    _ensure(help_result.returncode == 0, f"help failed: {help_result.stderr}")
    _ensure("{start,run-fake-e2e,status,lease-agent,ack,submit-result}" in help_result.stdout, "formal command list changed")
    for retired in ("complete-flowguard", "record-validation", "close"):
        _ensure(retired not in help_result.stdout, f"retired command appears in help: {retired}")

    rejected = _run_raw_cli(root, command_log, "--json", "complete-flowguard")
    _ensure(rejected.returncode != 0, "retired complete-flowguard command was accepted")
    _ensure("invalid choice" in rejected.stderr, f"retired command did not fail as invalid choice: {rejected.stderr}")
    return {
        "name": "retired_side_command",
        "ok": True,
        "root": str(root),
        "observations": {"complete_flowguard_invalid_choice": True},
        "commands": command_log,
    }


def _flowguard_report() -> dict[str, Any]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
        success_predicate=lambda state, _trace: model.is_success(state),
        required_labels=model.REQUIRED_SAFE_LABELS,
    ).explore()
    return {
        "ok": report.ok,
        "summary": report.summary,
        "violation_count": len(report.violations),
        "dead_branch_count": len(report.dead_branches),
        "exception_branch_count": len(report.exception_branches),
        "reachability_failure_count": len(report.reachability_failures),
        "reachability_failures": [failure.message for failure in report.reachability_failures],
    }


def _target_plan_report() -> dict[str, Any]:
    state = model.target_state()
    failures = model.invariant_failures(state)
    return {
        "ok": not failures and model.is_success(state),
        "evidence_role": "blackbox_fake_project_target_plan_not_live_user_proof",
        "failures": failures,
        "state": model.state_summary(state),
        "labels": list(model.REQUIRED_SAFE_LABELS),
    }


def _hazard_report() -> dict[str, Any]:
    hazards: dict[str, list[str]] = {}
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        if failures:
            hazards[name] = failures
    return {
        "ok": set(hazards) == set(model.hazard_states()),
        "hazards": hazards,
        "expected": sorted(model.hazard_states()),
    }


def _run_scenario(name: str, fn: Callable[[Path], dict[str, Any]], work_root: Path) -> dict[str, Any]:
    try:
        return fn(work_root)
    except Exception as exc:  # pragma: no cover - exercised by failing validation.
        return {"name": name, "ok": False, "error": str(exc)}


def _run_checks_in_root(work_root: Path) -> dict[str, Any]:
    work_root.mkdir(parents=True, exist_ok=True)
    flowguard = _flowguard_report()
    target_plan = _target_plan_report()
    hazards = _hazard_report()
    scenario_fns: tuple[tuple[str, Callable[[Path], dict[str, Any]]], ...] = (
        ("normal_full_path", _scenario_normal),
        ("wrong_role_recovery", _scenario_wrong_role_recovery),
        ("missing_ack_block", _scenario_missing_ack_block),
        ("ack_only_wait", _scenario_ack_only_wait),
        ("retired_side_command", _scenario_retired_side_command),
    )
    scenarios = [_run_scenario(name, fn, work_root) for name, fn in scenario_fns]
    rows = [
        {
            "id": "fake_project_flowguard_model",
            "status": "passed" if flowguard["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/flowpilot_fake_project_rehearsal_model.py"],
        },
        {
            "id": "fake_project_blackbox_cli_normal",
            "status": "passed" if scenarios[0]["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["skills/flowpilot/assets/flowpilot_new.py"],
        },
        {
            "id": "fake_project_blackbox_cli_error_flows",
            "status": "passed" if all(scenario["ok"] for scenario in scenarios[1:]) else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["skills/flowpilot/assets/flowpilot_new.py"],
        },
        {
            "id": "fake_project_hazard_replay",
            "status": "passed" if hazards["ok"] else "failed",
            "freshness": "current",
            "scope": "routine",
            "evidence": ["simulations/flowpilot_fake_project_rehearsal_model.py"],
        },
    ]
    return {
        "result_type": "flowpilot_fake_project_rehearsal_checks",
        "model_id": model.MODEL_ID,
        "ok": flowguard["ok"] and target_plan["ok"] and hazards["ok"] and all(scenario["ok"] for scenario in scenarios),
        "entrypoint": str(ENTRYPOINT),
        "work_root": str(work_root),
        "black_box_contract": {
            "uses_public_cli_subprocesses": True,
            "uses_startup_ui_script": True,
            "uses_internal_e2e_helper": False,
            "fake_ai_result_bodies_redacted_from_report": True,
        },
        "flowguard": flowguard,
        "target_plan": target_plan,
        "hazard_detection": hazards,
        "scenarios": scenarios,
        "test_mesh": {
            "rows": rows,
            "routine_gate": {"ok": all(row["status"] == "passed" for row in rows)},
        },
    }


def run_checks(work_root: Path | None = None) -> dict[str, Any]:
    if work_root is None:
        with tempfile.TemporaryDirectory(prefix="flowpilot_fake_project_rehearsal_") as tmp:
            return _run_checks_in_root(Path(tmp))
    return _run_checks_in_root(work_root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--work-root", type=Path, default=DEFAULT_WORK_ROOT)
    parser.add_argument("--no-write-results", action="store_true")
    args = parser.parse_args()

    result = run_checks(args.work_root)
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(output, end="")
    if not args.no_write_results:
        args.json_out.write_text(output, encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
