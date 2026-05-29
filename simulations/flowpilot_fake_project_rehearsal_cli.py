"""CLI helpers for the black-box FlowPilot fake-project rehearsal."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
ENTRYPOINT = REPO_ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_new.py"
FAKE_STARTUP_TEXT = "Build a fake calculator CLI with docs, tests, FlowGuard evidence, review, validation, and closure."
MIN_ACCEPTED_ROUTE_NODES = 3
PLANNING_CHAIN = (
    ("task", "pm"),
    ("flowguard_check", "flowguard_operator"),
    ("review", "reviewer"),
    ("validation", "validator"),
    ("closure", "closure_officer"),
)


class RehearsalFailure(AssertionError):
    """Raised when a black-box rehearsal observation violates the contract."""


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise RehearsalFailure(message)


def redact_args(args: tuple[str, ...]) -> list[str]:
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


def payload_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
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


def parse_json(stdout: str) -> dict[str, Any] | None:
    text = stdout.strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def run_cli(root: Path, command_log: list[dict[str, Any]], *args: str, expect_ok: bool = True) -> dict[str, Any]:
    command = [sys.executable, "-B", str(ENTRYPOINT), "--root", str(root), "--json", *args]
    completed = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    payload = parse_json(completed.stdout)
    command_log.append(
        {
            "args": redact_args(args),
            "returncode": completed.returncode,
            "payload": payload_summary(payload),
            "stderr_excerpt": completed.stderr.strip()[:300],
        }
    )
    if expect_ok:
        ensure(completed.returncode == 0, f"CLI command failed: {args[0]} {completed.stderr.strip()}")
        ensure(payload is not None, f"CLI command did not return JSON: {args[0]}")
        ensure(payload.get("ok") is True, f"CLI command returned ok=false: {args[0]} {payload}")
    return payload or {"ok": False, "error": completed.stderr.strip(), "returncode": completed.returncode}


def run_raw_cli(root: Path, command_log: list[dict[str, Any]], *args: str) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, "-B", str(ENTRYPOINT), "--root", str(root), *args]
    completed = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    command_log.append(
        {
            "args": redact_args(args),
            "returncode": completed.returncode,
            "stdout_excerpt": completed.stdout[:300],
            "stderr_excerpt": completed.stderr.strip()[:300],
        }
    )
    return completed


def reset_scenario_root(work_root: Path, name: str) -> Path:
    root = (work_root / name).resolve()
    work_root_resolved = work_root.resolve()
    ensure(str(root).startswith(str(work_root_resolved)), f"refusing to reset path outside work root: {root}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def status_projection(root: Path, command_log: list[dict[str, Any]]) -> dict[str, Any]:
    payload = run_cli(root, command_log, "status")
    projection = payload.get("status")
    ensure(isinstance(projection, dict), "status command did not return a projection")
    return projection


def packet_row(projection: dict[str, Any], packet_id: str) -> dict[str, Any]:
    for packet in projection.get("packets", []):
        if packet.get("packet_id") == packet_id:
            return packet
    raise RehearsalFailure(f"missing packet row in public status: {packet_id}")


def assert_public_projection_is_sealed(projection: dict[str, Any]) -> None:
    serialized = json.dumps(projection, sort_keys=True)
    ensure(projection.get("sealed_bodies_visible") is False, "public status claims sealed bodies are visible")
    ensure(FAKE_STARTUP_TEXT not in serialized, "public status leaked fake startup text")
    ensure("SEALED_RESULT_BODY" not in serialized, "public status leaked sealed fake AI result body")
    for packet in projection.get("packets", []):
        ensure(packet.get("sealed_body_hidden") is True, f"packet body is not marked hidden: {packet}")


def complete_full_packet_chain(
    root: Path,
    command_log: list[dict[str, Any]],
    current_payload: dict[str, Any],
    *,
    first_pm_disposition_decision: str = "accept",
) -> dict[str, Any]:
    completed_packets: list[dict[str, str]] = []
    pm_disposition_count = 0
    for step_index in range(80):
        action = current_payload.get("next_action")
        ensure(isinstance(action, dict), f"missing next action at step {step_index}")
        if action.get("action_type") == "terminal_complete":
            break
        ensure(action.get("action_type") == "lease_agent", f"expected lease action at step {step_index}: {action}")
        responsibility = str(action.get("responsibility", ""))
        packet_id = str(action.get("subject_id", ""))
        ensure(packet_id, f"missing packet id at step {step_index}")

        projection = status_projection(root, command_log)
        packet = packet_row(projection, packet_id)
        packet_kind = str(packet.get("packet_kind", ""))
        ensure(packet_kind, f"missing packet kind for {packet_id}: {packet}")
        ensure(
            packet_kind != "task" or packet.get("route_scope") != "planning" or responsibility == "pm",
            f"planning task packet must be PM-owned: {packet}",
        )

        lease_payload = run_cli(
            root,
            command_log,
            "lease-agent",
            "--packet-id",
            packet_id,
            "--responsibility",
            responsibility,
            "--agent-id",
            f"fake-{packet_kind}-{step_index}",
            "--host-kind",
            "fake",
        )
        lease_id = str(lease_payload.get("lease_id", ""))
        ensure(lease_id, f"missing lease id for {packet_kind}")
        ensure(lease_payload["next_action"]["action_type"] == "wait_for_ack", f"expected wait_for_ack: {lease_payload}")

        ack_payload = run_cli(root, command_log, "ack", "--lease-id", lease_id, "--packet-id", packet_id)
        ensure(ack_payload["next_action"]["action_type"] == "wait_for_result", f"expected wait_for_result: {ack_payload}")
        if packet_kind == "task" and packet.get("route_scope") == "planning":
            body = "\n".join(
                [
                    "1. Plan architecture and acceptance contracts",
                    "2. Implement the fake calculator CLI behavior",
                    "3. Validate tests, evidence, and route-wide closure",
                ]
            )
        elif packet_kind == "pm_disposition":
            pm_disposition_count += 1
            decision = first_pm_disposition_decision if pm_disposition_count == 1 else "accept"
            body = json.dumps({"decision": decision, "reason": f"fake PM disposition {decision}"})
        else:
            body = f"SEALED_RESULT_BODY: fake {packet_kind} result for {packet_id}"

        current_payload = run_cli(
            root,
            command_log,
            "submit-result",
            "--lease-id",
            lease_id,
            "--packet-id",
            packet_id,
            "--body",
            body,
        )
        completed_packets.append({"packet_id": packet_id, "packet_kind": packet_kind, "lease_id": lease_id})
    else:
        raise RehearsalFailure("packet chain exceeded recursive route budget")

    final_action = current_payload.get("next_action", {})
    ensure(final_action.get("action_type") == "terminal_complete", f"final action was not terminal_complete: {final_action}")
    projection = status_projection(root, command_log)
    assert_public_projection_is_sealed(projection)
    ensure(projection.get("next_action", {}).get("action_type") == "terminal_complete", "public status is not terminal")
    ensure(projection.get("closure", {}).get("decision") == "complete", "closure did not complete")

    packet_kinds = [packet.get("packet_kind") for packet in projection.get("packets", [])]
    route_nodes = projection.get("route_nodes", [])
    accepted_nodes = [node for node in route_nodes if node.get("status") == "accepted"]
    ensure(len(accepted_nodes) >= MIN_ACCEPTED_ROUTE_NODES, f"recursive route did not accept enough nodes: {route_nodes}")
    ensure(packet_kinds.count("pm_disposition") >= MIN_ACCEPTED_ROUTE_NODES, f"PM dispositions missing from chain: {packet_kinds}")
    ensure(all(packet.get("status") == "accepted" for packet in projection.get("packets", [])), "not all packets are accepted")
    ensure(not [lease for lease in projection.get("leases", []) if lease.get("status") == "active"], "terminal status has active leases")
    ensure(all(lease.get("ack_received") for lease in projection.get("leases", [])), "a terminal lease is missing ACK")
    ensure(all(lease.get("packet_id") for lease in projection.get("leases", [])), "a terminal lease is missing packet id")
    ensure(projection.get("flowguard") and projection["flowguard"][0].get("decision") == "pass", "FlowGuard pass evidence missing")
    ensure(
        projection.get("validation_evidence") and projection["validation_evidence"][0].get("status") == "passed",
        "validation evidence missing",
    )
    ensure(not projection.get("blockers"), f"terminal public status has blockers: {projection.get('blockers')}")
    return {
        "terminal_action": final_action,
        "packet_kinds": packet_kinds,
        "accepted_route_nodes": [node.get("node_id") for node in accepted_nodes],
        "completed_packets": completed_packets,
        "lease_count": len(projection.get("leases", [])),
        "sealed_bodies_visible": projection.get("sealed_bodies_visible"),
    }


def complete_planning_chain_only(
    root: Path,
    command_log: list[dict[str, Any]],
    current_payload: dict[str, Any],
) -> dict[str, Any]:
    for step_index, (expected_kind, responsibility) in enumerate(PLANNING_CHAIN):
        action = current_payload.get("next_action")
        ensure(isinstance(action, dict), f"missing planning next action before {expected_kind}")
        ensure(action.get("action_type") == "lease_agent", f"expected planning lease action: {action}")
        ensure(action.get("responsibility") == responsibility, f"wrong planning responsibility: {action}")
        packet_id = str(action.get("subject_id", ""))
        projection = status_projection(root, command_log)
        packet = packet_row(projection, packet_id)
        ensure(packet.get("packet_kind") == expected_kind, f"wrong planning packet kind: {packet}")
        lease_payload = run_cli(
            root,
            command_log,
            "lease-agent",
            "--packet-id",
            packet_id,
            "--responsibility",
            responsibility,
            "--agent-id",
            f"fake-planning-{expected_kind}-{step_index}",
            "--host-kind",
            "fake",
        )
        lease_id = str(lease_payload["lease_id"])
        run_cli(root, command_log, "ack", "--lease-id", lease_id, "--packet-id", packet_id)
        if expected_kind == "task":
            body = "\n".join(
                [
                    "1. Plan architecture and acceptance contracts",
                    "2. Implement the fake calculator CLI behavior",
                    "3. Validate tests, evidence, and route-wide closure",
                ]
            )
        else:
            body = f"SEALED_RESULT_BODY: fake planning {expected_kind}"
        current_payload = run_cli(
            root,
            command_log,
            "submit-result",
            "--lease-id",
            lease_id,
            "--packet-id",
            packet_id,
            "--body",
            body,
        )
    projection = status_projection(root, command_log)
    assert_public_projection_is_sealed(projection)
    ensure(projection.get("next_action", {}).get("action_type") == "lease_agent", "planning chain did not continue to node work")
    ensure(
        projection.get("next_action", {}).get("responsibility") in {"worker", "ui_qa", "research_worker", "reviewer"},
        "planning chain did not lease a node role",
    )
    ensure(projection.get("closure", {}).get("decision") != "complete", "planning chain reached terminal closure")
    ensure(len(projection.get("route_nodes", [])) >= MIN_ACCEPTED_ROUTE_NODES, "planning chain did not materialize route nodes")
    return {
        "next_action": projection.get("next_action", {}),
        "route_nodes": projection.get("route_nodes", []),
        "closure": projection.get("closure", {}),
    }


def start_rehearsal(root: Path, command_log: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    payload = run_cli(
        root,
        command_log,
        "start",
        "--run-id",
        run_id,
        "--headless-startup-text",
        FAKE_STARTUP_TEXT,
    )
    ensure(payload.get("mode") == "rehearsal", "headless startup should be recorded as rehearsal mode")
    ensure(payload.get("next_action", {}).get("action_type") == "lease_agent", "startup did not request first lease")
    ensure(payload.get("next_action", {}).get("responsibility") == "pm", "startup did not request PM first")
    projection = payload.get("status", {})
    ensure(isinstance(projection, dict), "startup did not include public status")
    assert_public_projection_is_sealed(projection)
    return payload
