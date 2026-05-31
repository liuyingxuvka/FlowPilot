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
    duty = payload.get("foreground_duty")
    if isinstance(duty, dict):
        summary["foreground_duty"] = {
            "action": duty.get("action", ""),
            "final_return_allowed": (duty.get("final_return_preflight") or {}).get("allowed", False),
        }
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


def _node_acceptance_plan_body(packet: dict[str, Any]) -> str:
    node_id = str(packet.get("route_node_id") or "")
    return json.dumps(
        {
            "route_node_id": node_id,
            "proof_obligations": ["implementation evidence", "FlowGuard evidence", "review", "validation"],
            "repair_policy": "same_node_repair_default",
            "low_quality_success_risks": ["existence-only evidence", "missing skill evidence"],
            "node_context_package": {
                "node_id": node_id,
                "purpose": "Complete the current route node with bounded worker execution, FlowGuard checks, review, and validation.",
                "acceptance_criteria": [
                    "worker result satisfies the node packet",
                    "pre-work and post-result FlowGuard evidence are current",
                    "reviewer independently challenges the node outcome",
                ],
                "relevant_references": ["route node contract", "high standard contract", "runtime ledger"],
                "evidence_targets": ["worker result body", "FlowGuard report", "reviewer report", "validation output"],
                "inspection_targets": ["changed files", "command output", "model artifacts", "runtime ledger"],
                "known_risks": ["existence-only evidence", "stale generation", "review without active inspection"],
                "flowguard_targets": ["development-process route", "model-test alignment where applicable"],
                "reviewer_starting_points": ["worker result", "node context package", "FlowGuard reports", "validation evidence"],
            },
        }
    )


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
        elif packet_kind == "task" and packet.get("route_scope") == "node_acceptance_plan":
            body = _node_acceptance_plan_body(packet)
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
    guard = projection.get("lifecycle_guard", {})
    ensure(guard.get("decision") == "terminal_return", f"terminal guard did not allow terminal return: {guard}")
    ensure(guard.get("controller_stop_allowed") is True, f"terminal guard did not allow Controller stop: {guard}")
    duty = projection.get("foreground_duty", {})
    ensure(duty.get("action") == "terminal_return", f"terminal foreground duty did not allow return: {duty}")
    ensure(duty.get("final_return_preflight", {}).get("allowed") is True, f"terminal final preflight failed: {duty}")

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
    ensure(projection.get("system_closures"), "system closure evidence missing")
    ensure("validation" not in packet_kinds, f"ordinary path still issued validator packets: {packet_kinds}")
    ensure("closure" not in packet_kinds, f"ordinary path still issued closure packets: {packet_kinds}")
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
    for step_index in range(40):
        action = current_payload.get("next_action")
        ensure(isinstance(action, dict), "missing planning next action")
        ensure(action.get("action_type") == "lease_agent", f"expected planning lease action: {action}")
        responsibility = str(action.get("responsibility", ""))
        packet_id = str(action.get("subject_id", ""))
        projection = status_projection(root, command_log)
        packet = packet_row(projection, packet_id)
        packet_kind = str(packet.get("packet_kind", ""))
        route_scope = str(packet.get("route_scope", ""))
        ensure(packet_kind in {"task", "flowguard_check", "review"}, f"wrong planning packet kind: {packet}")
        ensure(responsibility == packet.get("responsibility"), f"wrong planning responsibility: {action}")
        lease_payload = run_cli(
            root,
            command_log,
            "lease-agent",
            "--packet-id",
            packet_id,
            "--responsibility",
            responsibility,
            "--agent-id",
            f"fake-planning-{packet_kind}-{step_index}",
            "--host-kind",
            "fake",
        )
        lease_id = str(lease_payload["lease_id"])
        run_cli(root, command_log, "ack", "--lease-id", lease_id, "--packet-id", packet_id)
        if packet_kind == "task" and route_scope == "high_standard_contract":
            body = json.dumps(
                {
                    "requirements": [
                        {
                            "requirement_id": "hsr-001",
                            "classification": "hard_current",
                            "summary": "Complete the fake project to a high standard.",
                        }
                    ]
                }
            )
        elif packet_kind == "task" and route_scope == "discovery":
            body = json.dumps(
                {
                    "material_sources": ["startup"],
                    "local_skill_inventory": ["flowguard-development-process-flow"],
                }
            )
        elif packet_kind == "task" and route_scope == "skill_standard":
            body = json.dumps(
                {
                    "obligations": [
                        {
                            "obligation_id": "skill-std-001",
                            "skill": "flowguard-development-process-flow",
                            "classification": "required",
                        }
                    ]
                }
            )
        elif packet_kind == "task" and route_scope == "planning":
            body = "\n".join(
                [
                    "1. Plan architecture and acceptance contracts",
                    "2. Implement the fake calculator CLI behavior",
                    "3. Validate tests, evidence, and route-wide closure",
                ]
            )
        elif packet_kind == "task" and route_scope == "node_acceptance_plan":
            body = _node_acceptance_plan_body(packet)
        else:
            body = f"SEALED_RESULT_BODY: fake planning {packet_kind}"
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
        if packet_kind == "review" and route_scope == "planning":
            break
    else:
        raise RehearsalFailure("planning chain exceeded high-standard gate budget")
    projection = status_projection(root, command_log)
    assert_public_projection_is_sealed(projection)
    next_action = projection.get("next_action", {})
    ensure(next_action.get("action_type") == "lease_agent", "planning chain did not continue to node planning")
    next_packet = packet_row(projection, str(next_action.get("subject_id", "")))
    ensure(
        next_packet.get("route_scope") == "node_acceptance_plan",
        f"planning chain did not stop at node acceptance planning: {next_packet}",
    )
    ensure(next_action.get("responsibility") == "pm", f"node acceptance plan is not PM-owned: {next_action}")
    ensure(projection.get("closure", {}).get("decision") != "complete", "planning chain reached terminal closure")
    guard = projection.get("lifecycle_guard", {})
    ensure(guard.get("controller_stop_allowed") is False, f"planning guard allowed Controller stop: {guard}")
    duty = projection.get("foreground_duty", {})
    ensure(duty.get("action") == "process_next_action", f"planning duty did not continue: {duty}")
    ensure(duty.get("subject_id") == str(next_action.get("subject_id", "")), f"planning duty lost next packet: {duty}")
    ensure(duty.get("final_return_preflight", {}).get("allowed") is False, f"planning duty allowed final return: {duty}")
    ensure(len(projection.get("route_nodes", [])) >= MIN_ACCEPTED_ROUTE_NODES, "planning chain did not materialize route nodes")
    return {
        "next_action": next_action,
        "next_route_scope": next_packet.get("route_scope"),
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
    duty = projection.get("foreground_duty", {})
    ensure(duty.get("action") == "process_next_action", f"startup foreground duty did not process next action: {duty}")
    ensure(duty.get("final_return_preflight", {}).get("allowed") is False, f"startup allowed final return: {duty}")
    return payload
