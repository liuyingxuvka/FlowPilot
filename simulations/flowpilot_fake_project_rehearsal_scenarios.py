"""Black-box FlowPilot fake-project rehearsal scenarios."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

try:  # pragma: no cover
    from .flowpilot_fake_project_rehearsal_cli import (
        ENTRYPOINT,
        assert_public_projection_is_sealed,
        complete_full_packet_chain,
        complete_planning_chain_only,
        ensure,
        packet_row,
        reset_scenario_root,
        run_cli,
        run_raw_cli,
        start_rehearsal,
        status_projection,
    )
except ImportError:  # pragma: no cover
    from flowpilot_fake_project_rehearsal_cli import (
        ENTRYPOINT,
        assert_public_projection_is_sealed,
        complete_full_packet_chain,
        complete_planning_chain_only,
        ensure,
        packet_row,
        reset_scenario_root,
        run_cli,
        run_raw_cli,
        start_rehearsal,
        status_projection,
    )


def scenario_normal(work_root: Path) -> dict[str, Any]:
    command_log: list[dict[str, Any]] = []
    root = reset_scenario_root(work_root, "normal_full_path")
    start_payload = start_rehearsal(root, command_log, "run-fake-normal")
    chain = complete_full_packet_chain(root, command_log, start_payload)
    return {
        "name": "normal_full_path",
        "ok": True,
        "root": str(root),
        "observations": chain,
        "commands": command_log,
    }


def scenario_wrong_role_recovery(work_root: Path) -> dict[str, Any]:
    command_log: list[dict[str, Any]] = []
    root = reset_scenario_root(work_root, "wrong_role_recovery")
    start_payload = start_rehearsal(root, command_log, "run-fake-wrong-role")
    pm_packet = str(start_payload["next_action"]["subject_id"])
    rejected = run_cli(
        root,
        command_log,
        "lease-agent",
        "--packet-id",
        pm_packet,
        "--responsibility",
        "reviewer",
        "--agent-id",
        "fake-reviewer-wrong-role",
        "--host-kind",
        "fake",
        expect_ok=False,
    )
    ensure(rejected.get("ok") is False, f"wrong-role lease was not rejected: {rejected}")
    ensure("lease responsibility does not match packet" in str(rejected.get("error", "")), f"wrong rejection error: {rejected}")

    chain = complete_full_packet_chain(root, command_log, start_payload)
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


def scenario_planning_chain_does_not_terminal(work_root: Path) -> dict[str, Any]:
    command_log: list[dict[str, Any]] = []
    root = reset_scenario_root(work_root, "planning_chain_does_not_terminal")
    start_payload = start_rehearsal(root, command_log, "run-fake-planning-only")
    observation = complete_planning_chain_only(root, command_log, start_payload)
    return {
        "name": "planning_chain_does_not_terminal",
        "ok": True,
        "root": str(root),
        "observations": {
            "next_action": observation["next_action"].get("action_type"),
            "next_responsibility": observation["next_action"].get("responsibility"),
            "route_node_count": len(observation["route_nodes"]),
            "closure": observation["closure"].get("decision"),
        },
        "commands": command_log,
    }


def scenario_route_mutation_recovery(work_root: Path) -> dict[str, Any]:
    command_log: list[dict[str, Any]] = []
    root = reset_scenario_root(work_root, "route_mutation_recovery")
    start_payload = start_rehearsal(root, command_log, "run-fake-route-mutation")
    chain = complete_full_packet_chain(root, command_log, start_payload, first_pm_disposition_decision="mutate_route")
    projection = status_projection(root, command_log)
    superseded = [node for node in projection.get("route_nodes", []) if node.get("status") == "superseded"]
    accepted = [node for node in projection.get("route_nodes", []) if node.get("status") == "accepted"]
    ensure(superseded, "route mutation recovery did not supersede a node")
    ensure(len(accepted) >= 3, "route mutation recovery did not accept replacement route nodes")
    return {
        "name": "route_mutation_recovery",
        "ok": True,
        "root": str(root),
        "observations": {
            "terminal": chain["terminal_action"].get("action_type"),
            "superseded_node_ids": [node.get("node_id") for node in superseded],
            "accepted_route_nodes": [node.get("node_id") for node in accepted],
        },
        "commands": command_log,
    }


def scenario_missing_ack_block(work_root: Path) -> dict[str, Any]:
    command_log: list[dict[str, Any]] = []
    root = reset_scenario_root(work_root, "missing_ack_block")
    start_payload = start_rehearsal(root, command_log, "run-fake-missing-ack")
    pm_packet = str(start_payload["next_action"]["subject_id"])

    lease_payload = run_cli(
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
    result_payload = run_cli(
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
    ensure(result_payload.get("next_action", {}).get("action_type") == "repair_packet", "missing ACK did not expose repair boundary")
    projection = status_projection(root, command_log)
    assert_public_projection_is_sealed(projection)
    packet = packet_row(projection, pm_packet)
    ensure(packet.get("status") == "result_blocked", f"missing ACK packet not blocked: {packet}")
    ensure(projection.get("next_action", {}).get("action_type") == "repair_packet", "status did not stay on repair boundary")
    blockers = projection.get("blockers", [])
    ensure(any("missing_ack" in str(blocker) for blocker in blockers), f"missing ACK blocker absent: {blockers}")
    ensure(projection.get("closure", {}).get("decision") != "complete", "missing ACK reached closure")
    guard = projection.get("lifecycle_guard", {})
    ensure(guard.get("controller_stop_allowed") is False, f"missing ACK guard allowed stop: {guard}")
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


def scenario_ack_only_wait(work_root: Path) -> dict[str, Any]:
    command_log: list[dict[str, Any]] = []
    root = reset_scenario_root(work_root, "ack_only_wait")
    start_payload = start_rehearsal(root, command_log, "run-fake-ack-only")
    pm_packet = str(start_payload["next_action"]["subject_id"])

    lease_payload = run_cli(
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
    run_cli(root, command_log, "ack", "--lease-id", str(lease_payload["lease_id"]), "--packet-id", pm_packet)
    projection = status_projection(root, command_log)
    assert_public_projection_is_sealed(projection)
    ensure(projection.get("next_action", {}).get("action_type") == "wait_for_result", "ACK-only did not wait for result")
    ensure(projection.get("closure", {}).get("decision") != "complete", "ACK-only reached closure")
    guard = projection.get("lifecycle_guard", {})
    ensure(guard.get("decision") == "wait_for_result", f"ACK-only guard did not classify result wait: {guard}")
    ensure(guard.get("controller_stop_allowed") is False, f"ACK-only guard allowed stop: {guard}")
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


def scenario_lifecycle_guard_resume_and_patrol(work_root: Path) -> dict[str, Any]:
    command_log: list[dict[str, Any]] = []
    root = reset_scenario_root(work_root, "lifecycle_guard_resume_and_patrol")
    start_payload = start_rehearsal(root, command_log, "run-fake-lifecycle-guard")
    pm_packet = str(start_payload["next_action"]["subject_id"])

    lease_payload = run_cli(
        root,
        command_log,
        "lease-agent",
        "--packet-id",
        pm_packet,
        "--responsibility",
        "pm",
        "--agent-id",
        "fake-pm-guard",
        "--host-kind",
        "fake",
    )
    run_cli(root, command_log, "ack", "--lease-id", str(lease_payload["lease_id"]), "--packet-id", pm_packet)
    resumed = run_cli(root, command_log, "resume", "--reason", "fake_lifecycle_resume")
    ensure(resumed["next_action"]["action_type"] == "wait_for_result", f"resume did not rehydrate wait: {resumed}")
    guard = resumed.get("lifecycle_guard", {})
    ensure(guard.get("decision") == "wait_for_result", f"resume guard did not classify result wait: {guard}")
    ensure(guard.get("controller_stop_allowed") is False, f"resume guard allowed nonterminal stop: {guard}")
    ensure(guard.get("wait_subject", {}).get("packet_id") == pm_packet, f"resume guard lost packet id: {guard}")

    run_cli(root, command_log, "patrol")
    patrol = run_cli(root, command_log, "patrol")
    patrol_guard = patrol.get("lifecycle_guard", {})
    ensure(
        patrol_guard.get("decision") == "reissue_or_replace_lease",
        f"patrol did not classify repeated result wait for recovery: {patrol_guard}",
    )
    ensure(patrol_guard.get("controller_stop_allowed") is False, f"patrol guard allowed stop: {patrol_guard}")
    projection = status_projection(root, command_log)
    assert_public_projection_is_sealed(projection)
    ensure(projection.get("closure", {}).get("decision") != "complete", "guard patrol reached terminal closure")
    return {
        "name": "lifecycle_guard_resume_and_patrol",
        "ok": True,
        "root": str(root),
        "observations": {
            "resume_decision": guard.get("decision"),
            "patrol_decision": patrol_guard.get("decision"),
            "controller_stop_allowed": patrol_guard.get("controller_stop_allowed"),
        },
        "commands": command_log,
    }


def scenario_retired_side_command(work_root: Path) -> dict[str, Any]:
    command_log: list[dict[str, Any]] = []
    root = reset_scenario_root(work_root, "retired_side_command")
    help_result = run_raw_cli(root, command_log, "--help")
    ensure(help_result.returncode == 0, f"help failed: {help_result.stderr}")
    ensure(
        "{start,run-fake-e2e,status,patrol,resume,lease-agent,ack,submit-result}" in help_result.stdout,
        "formal command list changed",
    )
    for retired in ("complete-flowguard", "record-validation", "close"):
        ensure(retired not in help_result.stdout, f"retired command appears in help: {retired}")

    rejected = run_raw_cli(root, command_log, "--json", "complete-flowguard")
    ensure(rejected.returncode != 0, "retired complete-flowguard command was accepted")
    ensure("invalid choice" in rejected.stderr, f"retired command did not fail as invalid choice: {rejected.stderr}")
    return {
        "name": "retired_side_command",
        "ok": True,
        "root": str(root),
        "observations": {"complete_flowguard_invalid_choice": True},
        "commands": command_log,
    }


SCENARIOS: tuple[tuple[str, Callable[[Path], dict[str, Any]]], ...] = (
    ("normal_full_path", scenario_normal),
    ("wrong_role_recovery", scenario_wrong_role_recovery),
    ("planning_chain_does_not_terminal", scenario_planning_chain_does_not_terminal),
    ("route_mutation_recovery", scenario_route_mutation_recovery),
    ("missing_ack_block", scenario_missing_ack_block),
    ("ack_only_wait", scenario_ack_only_wait),
    ("lifecycle_guard_resume_and_patrol", scenario_lifecycle_guard_resume_and_patrol),
    ("retired_side_command", scenario_retired_side_command),
)


def run_scenario(name: str, fn: Callable[[Path], dict[str, Any]], work_root: Path) -> dict[str, Any]:
    try:
        return fn(work_root)
    except Exception as exc:  # pragma: no cover - exercised by failing validation.
        return {"name": name, "ok": False, "error": str(exc)}


def run_all_scenarios(work_root: Path) -> list[dict[str, Any]]:
    return [run_scenario(name, fn, work_root) for name, fn in SCENARIOS]
