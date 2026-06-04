"""Black-box FlowPilot fake-project rehearsal scenarios."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

try:  # pragma: no cover
    from .flowpilot_fake_project_rehearsal_cli import (
        ENTRYPOINT,
        RehearsalFailure,
        assert_public_projection_is_sealed,
        complete_full_packet_chain,
        complete_planning_chain_only,
        ensure,
        packet_row,
        resolve_and_lease_packet,
        reset_scenario_root,
        run_cli,
        run_raw_cli,
        start_rehearsal,
        status_projection,
    )
except ImportError:  # pragma: no cover
    from flowpilot_fake_project_rehearsal_cli import (
        ENTRYPOINT,
        RehearsalFailure,
        assert_public_projection_is_sealed,
        complete_full_packet_chain,
        complete_planning_chain_only,
        ensure,
        packet_row,
        resolve_and_lease_packet,
        reset_scenario_root,
        run_cli,
        run_raw_cli,
        start_rehearsal,
        status_projection,
    )


ROUTE_PLAN_SCHEMA_VERSION = "flowpilot.route_plan.v1"


def _route_plan_body() -> str:
    return json.dumps(
        {
            "schema_version": ROUTE_PLAN_SCHEMA_VERSION,
            "nodes": [
                {
                    "node_id": "node-001",
                    "title": "Implement fake calculator CLI behavior",
                    "responsibility": "worker",
                    "modeled_target": "development_process",
                    "acceptance_criteria": [
                        "The fake calculator behavior is implemented in the bounded scenario.",
                        "Worker evidence names current files and command results.",
                    ],
                },
                {
                    "node_id": "node-002",
                    "title": "Validate fake project evidence",
                    "responsibility": "worker",
                    "modeled_target": "model_test_alignment",
                    "acceptance_criteria": [
                        "FlowGuard and ordinary validation evidence are current.",
                        "Evidence can be challenged by an independent reviewer.",
                    ],
                },
                {
                    "node_id": "node-003",
                    "title": "Assemble final closure package",
                    "responsibility": "worker",
                    "modeled_target": "development_process",
                    "acceptance_criteria": [
                        "The final route-wide ledger accounts for all effective nodes.",
                        "The public status remains body-free at terminal completion.",
                    ],
                },
            ],
        },
        sort_keys=True,
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
        "resolve-role-assignment",
        "--packet-id",
        pm_packet,
        "--responsibility",
        "reviewer",
        "--host-kind",
        "fake",
        expect_ok=False,
    )
    ensure(rejected.get("ok") is False, f"wrong-role assignment was not rejected: {rejected}")
    ensure(
        "assignment responsibility does not match packet" in str(rejected.get("error", "")),
        f"wrong rejection error: {rejected}",
    )

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
    final_preflight = run_cli(root, command_log, "final-preflight", expect_ok=False)
    ensure(final_preflight.get("ok") is False, f"planning final-preflight unexpectedly passed: {final_preflight}")
    ensure(
        final_preflight.get("foreground_duty", {}).get("action") == "process_next_action",
        f"planning final-preflight did not preserve continuation duty: {final_preflight}",
    )
    return {
        "name": "planning_chain_does_not_terminal",
        "ok": True,
        "root": str(root),
        "observations": {
            "next_action": observation["next_action"].get("action_type"),
            "next_responsibility": observation["next_action"].get("responsibility"),
            "route_node_count": len(observation["route_nodes"]),
            "closure": observation["closure"].get("decision"),
            "final_preflight_allowed": final_preflight.get("final_return_preflight", {}).get("allowed"),
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

    lease_payload = resolve_and_lease_packet(
        root,
        command_log,
        packet_id=pm_packet,
        responsibility="pm",
        agent_id="fake-pm-no-ack",
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

    lease_payload = resolve_and_lease_packet(
        root,
        command_log,
        packet_id=pm_packet,
        responsibility="pm",
        agent_id="fake-pm-ack-only",
    )
    run_cli(root, command_log, "ack", "--lease-id", str(lease_payload["lease_id"]), "--packet-id", pm_packet)
    projection = status_projection(root, command_log)
    assert_public_projection_is_sealed(projection)
    ensure(projection.get("next_action", {}).get("action_type") == "wait_for_result", "ACK-only did not wait for result")
    ensure(projection.get("closure", {}).get("decision") != "complete", "ACK-only reached closure")
    guard = projection.get("lifecycle_guard", {})
    ensure(guard.get("decision") == "wait_for_result", f"ACK-only guard did not classify result wait: {guard}")
    ensure(guard.get("controller_stop_allowed") is False, f"ACK-only guard allowed stop: {guard}")
    duty = projection.get("foreground_duty", {})
    ensure(duty.get("action") == "wait_patrol", f"ACK-only foreground duty was not a patrol: {duty}")
    ensure(duty.get("wait_patrol", {}).get("seconds") == 60, f"ACK-only patrol did not carry 60-second duty: {duty}")
    ensure(duty.get("final_return_preflight", {}).get("allowed") is False, f"ACK-only duty allowed final return: {duty}")
    final_preflight = run_cli(root, command_log, "final-preflight", expect_ok=False)
    ensure(final_preflight.get("ok") is False, f"ACK-only final-preflight unexpectedly passed: {final_preflight}")
    return {
        "name": "ack_only_wait",
        "ok": True,
        "root": str(root),
        "observations": {
            "next_action": projection.get("next_action", {}).get("action_type"),
            "closure": projection.get("closure", {}).get("decision"),
            "foreground_duty": duty.get("action"),
            "final_preflight_allowed": final_preflight.get("final_return_preflight", {}).get("allowed"),
        },
        "commands": command_log,
    }


def scenario_lifecycle_guard_resume_and_patrol(work_root: Path) -> dict[str, Any]:
    command_log: list[dict[str, Any]] = []
    root = reset_scenario_root(work_root, "lifecycle_guard_resume_and_patrol")
    start_payload = start_rehearsal(root, command_log, "run-fake-lifecycle-guard")
    pm_packet = str(start_payload["next_action"]["subject_id"])

    lease_payload = resolve_and_lease_packet(
        root,
        command_log,
        packet_id=pm_packet,
        responsibility="pm",
        agent_id="fake-pm-guard",
    )
    run_cli(root, command_log, "ack", "--lease-id", str(lease_payload["lease_id"]), "--packet-id", pm_packet)
    resumed = run_cli(root, command_log, "resume", "--reason", "fake_lifecycle_resume")
    ensure(resumed["next_action"]["action_type"] == "wait_for_result", f"resume did not rehydrate wait: {resumed}")
    guard = resumed.get("lifecycle_guard", {})
    ensure(guard.get("decision") == "wait_for_result", f"resume guard did not classify result wait: {guard}")
    ensure(guard.get("controller_stop_allowed") is False, f"resume guard allowed nonterminal stop: {guard}")
    ensure(guard.get("wait_subject", {}).get("packet_id") == pm_packet, f"resume guard lost packet id: {guard}")
    resume_duty = resumed.get("foreground_duty", {})
    ensure(resume_duty.get("action") == "wait_patrol", f"resume did not expose wait patrol duty: {resume_duty}")

    run_cli(root, command_log, "patrol")
    patrol = run_cli(root, command_log, "patrol")
    patrol_guard = patrol.get("lifecycle_guard", {})
    ensure(
        patrol_guard.get("decision") == "wait_for_result",
        f"patrol replaced a result wait without liveness failure evidence: {patrol_guard}",
    )
    ensure(patrol_guard.get("controller_stop_allowed") is False, f"patrol guard allowed stop: {patrol_guard}")
    ensure(patrol.get("foreground_duty", {}).get("action") == "wait_patrol", f"patrol did not preserve wait duty: {patrol}")

    failed_liveness = run_cli(
        root,
        command_log,
        "progress",
        "--lease-id",
        str(lease_payload["lease_id"]),
        "--packet-id",
        pm_packet,
        "--status",
        "no_output",
    )
    failed_guard = failed_liveness.get("lifecycle_guard", {})
    ensure(
        failed_guard.get("decision") == "reissue_or_replace_lease",
        f"liveness failure did not classify for recovery: {failed_guard}",
    )
    ensure(
        failed_liveness.get("foreground_duty", {}).get("action") == "recover_or_reissue",
        f"liveness failure did not expose recovery duty: {failed_liveness}",
    )
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
            "liveness_failure_decision": failed_guard.get("decision"),
            "controller_stop_allowed": failed_guard.get("controller_stop_allowed"),
        },
        "commands": command_log,
    }


def _planning_body_for(packet_kind: str, route_scope: str, route_node_id: str = "") -> str:
    if packet_kind == "task" and route_scope == "high_standard_contract":
        return json.dumps(
            {
                "decision": "pass",
                "requirements": [
                    {
                        "requirement_id": "hsr-001",
                        "classification": "hard_current",
                        "summary": "Complete the fake project to a high standard.",
                    }
                ]
            }
        )
    if packet_kind == "task" and route_scope == "discovery":
        return json.dumps(
            {
                "decision": "pass",
                "material_sources": ["startup"],
                "local_skill_inventory": ["flowguard-development-process-flow"],
            }
        )
    if packet_kind == "task" and route_scope == "skill_standard":
        return json.dumps(
            {
                "decision": "pass",
                "obligations": [
                    {
                        "obligation_id": "skill-std-001",
                        "skill": "flowguard-development-process-flow",
                        "classification": "required",
                    }
                ]
            }
        )
    if packet_kind == "task" and route_scope == "planning":
        return _route_plan_body()
    if packet_kind == "task" and route_scope == "node_acceptance_plan":
        return json.dumps(
            {
                "decision": "pass",
                "route_node_id": route_node_id,
                "proof_obligations": ["implementation evidence", "FlowGuard evidence", "review", "validation"],
                "repair_policy": "same_node_repair_default",
                "low_quality_success_risks": ["existence-only evidence", "missing skill evidence"],
                "node_context_package": {
                    "node_id": route_node_id,
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
                    "reviewer_starting_points": [
                        "worker result",
                        "node context package",
                        "FlowGuard reports",
                        "validation evidence",
                    ],
                },
            }
        )
    return json.dumps({"decision": "pass", "summary": f"fake planning {packet_kind}"})


def scenario_slow_reviewer_progress_preserved(work_root: Path) -> dict[str, Any]:
    command_log: list[dict[str, Any]] = []
    root = reset_scenario_root(work_root, "slow_reviewer_progress_preserved")
    current_payload = start_rehearsal(root, command_log, "run-fake-slow-reviewer")

    for step_index in range(40):
        action = current_payload.get("next_action")
        ensure(isinstance(action, dict), f"missing next action before reviewer step: {current_payload}")
        ensure(action.get("action_type") == "resolve_role_assignment", f"unexpected action before reviewer step: {action}")
        responsibility = str(action.get("responsibility", ""))
        packet_id = str(action.get("subject_id", ""))
        projection = status_projection(root, command_log)
        packet = packet_row(projection, packet_id)
        packet_kind = str(packet.get("packet_kind", ""))
        route_scope = str(packet.get("route_scope", ""))

        lease_payload = resolve_and_lease_packet(
            root,
            command_log,
            packet_id=packet_id,
            responsibility=responsibility,
            agent_id=f"fake-slow-reviewer-{step_index}",
        )
        lease_id = str(lease_payload["lease_id"])
        run_cli(root, command_log, "ack", "--lease-id", lease_id, "--packet-id", packet_id)

        if responsibility == "reviewer" or packet_kind == "review":
            progress_payload = run_cli(
                root,
                command_log,
                "progress",
                "--lease-id",
                lease_id,
                "--packet-id",
                packet_id,
                "--status",
                "still_working",
            )
            progress_guard = progress_payload.get("lifecycle_guard", {})
            ensure(progress_guard.get("decision") == "wait_for_result", f"reviewer progress did not keep wait: {progress_guard}")
            ensure(
                progress_payload.get("foreground_duty", {}).get("action") == "wait_patrol",
                f"reviewer progress did not keep patrol duty: {progress_payload}",
            )
            patrol_payload = run_cli(root, command_log, "patrol")
            patrol_guard = patrol_payload.get("lifecycle_guard", {})
            ensure(
                patrol_guard.get("decision") == "wait_for_result",
                f"slow live reviewer was reissued instead of preserved: {patrol_guard}",
            )
            ensure(
                patrol_payload.get("foreground_duty", {}).get("action") == "wait_patrol",
                f"slow live reviewer lost patrol duty: {patrol_payload}",
            )
            final_preflight = run_cli(root, command_log, "final-preflight", expect_ok=False)
            ensure(final_preflight.get("ok") is False, f"slow reviewer final-preflight unexpectedly passed: {final_preflight}")
            return {
                "name": "slow_reviewer_progress_preserved",
                "ok": True,
                "root": str(root),
                "observations": {
                    "review_packet": packet_id,
                    "progress_decision": progress_guard.get("decision"),
                    "patrol_decision": patrol_guard.get("decision"),
                    "foreground_duty": patrol_payload.get("foreground_duty", {}).get("action"),
                    "final_preflight_allowed": final_preflight.get("final_return_preflight", {}).get("allowed"),
                },
                "commands": command_log,
            }

        current_payload = run_cli(
            root,
            command_log,
            "submit-result",
            "--lease-id",
            lease_id,
            "--packet-id",
            packet_id,
            "--body",
            _planning_body_for(packet_kind, route_scope, str(packet.get("route_node_id") or "")),
        )

    raise RehearsalFailure("slow reviewer scenario never reached a reviewer packet")


def scenario_accepted_packet_reassignment_rejected(work_root: Path) -> dict[str, Any]:
    command_log: list[dict[str, Any]] = []
    root = reset_scenario_root(work_root, "accepted_packet_reassignment_rejected")
    current_payload = start_rehearsal(root, command_log, "run-fake-accepted-reassign")
    pm_packet = str(current_payload["next_action"]["subject_id"])
    projection = status_projection(root, command_log)
    packet = packet_row(projection, pm_packet)

    for step_index in range(20):
        action = current_payload.get("next_action")
        ensure(isinstance(action, dict), f"missing next action before accepted packet: {current_payload}")
        ensure(action.get("action_type") == "resolve_role_assignment", f"unexpected action before accepted packet: {action}")
        packet_id = str(action.get("subject_id", ""))
        responsibility = str(action.get("responsibility", ""))
        projection = status_projection(root, command_log)
        current_packet = packet_row(projection, packet_id)
        lease_payload = resolve_and_lease_packet(
            root,
            command_log,
            packet_id=packet_id,
            responsibility=responsibility,
            agent_id=f"fake-accepted-reassign-{step_index}",
        )
        lease_id = str(lease_payload["lease_id"])
        run_cli(root, command_log, "ack", "--lease-id", lease_id, "--packet-id", packet_id)
        current_payload = run_cli(
            root,
            command_log,
            "submit-result",
            "--lease-id",
            lease_id,
            "--packet-id",
            packet_id,
            "--body",
            _planning_body_for(
                str(current_packet.get("packet_kind", "")),
                str(current_packet.get("route_scope", "")),
                str(current_packet.get("route_node_id") or ""),
            ),
        )
        projection = status_projection(root, command_log)
        packet = packet_row(projection, pm_packet)
        if packet.get("status") == "accepted":
            break
    else:
        raise RehearsalFailure(f"first PM packet never reached accepted state: {packet}")

    reassignment = run_cli(
        root,
        command_log,
        "resolve-role-assignment",
        "--packet-id",
        pm_packet,
        "--responsibility",
        "pm",
        "--host-kind",
        "fake",
        expect_ok=False,
    )
    ensure(reassignment.get("ok") is False, f"accepted packet reassignment unexpectedly passed: {reassignment}")
    ensure("cannot assign accepted packet" in str(reassignment.get("error", "")), f"wrong reassignment error: {reassignment}")
    projection = status_projection(root, command_log)
    assert_public_projection_is_sealed(projection)
    accepted_packet = packet_row(projection, pm_packet)
    ensure(accepted_packet.get("status") == "accepted", f"accepted packet regressed after rejected reassignment: {accepted_packet}")
    return {
        "name": "accepted_packet_reassignment_rejected",
        "ok": True,
        "root": str(root),
        "observations": {
            "accepted_packet": pm_packet,
            "reassignment_rejected": True,
            "next_action": projection.get("next_action", {}).get("action_type"),
        },
        "commands": command_log,
    }


def scenario_stop_terminal_fence(work_root: Path) -> dict[str, Any]:
    command_log: list[dict[str, Any]] = []
    root = reset_scenario_root(work_root, "stop_terminal_fence")
    current_payload = start_rehearsal(root, command_log, "run-fake-stop-terminal")
    pm_packet = str(current_payload["next_action"]["subject_id"])
    lease_payload = resolve_and_lease_packet(
        root,
        command_log,
        packet_id=pm_packet,
        responsibility="pm",
        agent_id="fake-pm-stop-terminal",
    )
    stopped = run_cli(root, command_log, "stop", "--reason", "fake user stop")
    ensure(stopped.get("next_action", {}).get("action_type") == "terminal_lifecycle", f"stop did not terminalize: {stopped}")
    ensure(stopped.get("final_return_preflight", {}).get("allowed") is True, f"stop preflight did not allow exit: {stopped}")
    rejected = run_cli(
        root,
        command_log,
        "ack",
        "--lease-id",
        str(lease_payload["lease_id"]),
        "--packet-id",
        pm_packet,
        expect_ok=False,
    )
    ensure(rejected.get("ok") is False, f"stopped run accepted new work: {rejected}")
    ensure("run is terminal" in str(rejected.get("error", "")), f"wrong stopped-run error: {rejected}")
    projection = status_projection(root, command_log)
    assert_public_projection_is_sealed(projection)
    ensure(projection.get("next_action", {}).get("action_type") == "terminal_lifecycle", "stop status lost terminal action")
    return {
        "name": "stop_terminal_fence",
        "ok": True,
        "root": str(root),
        "observations": {
            "terminal_lifecycle": stopped.get("final_return_preflight", {}).get("terminal_lifecycle_status"),
            "post_stop_work_rejected": True,
        },
        "commands": command_log,
    }


def scenario_host_liveness_bridge_recovery(work_root: Path) -> dict[str, Any]:
    command_log: list[dict[str, Any]] = []
    root = reset_scenario_root(work_root, "host_liveness_bridge_recovery")
    current_payload = start_rehearsal(root, command_log, "run-fake-host-liveness")
    pm_packet = str(current_payload["next_action"]["subject_id"])
    lease_payload = resolve_and_lease_packet(
        root,
        command_log,
        packet_id=pm_packet,
        responsibility="pm",
        agent_id="fake-pm-host-liveness",
    )
    lease_id = str(lease_payload["lease_id"])
    run_cli(root, command_log, "ack", "--lease-id", lease_id, "--packet-id", pm_packet)
    run_cli(root, command_log, "progress", "--lease-id", lease_id, "--packet-id", pm_packet, "--status", "still_working")
    liveness = run_cli(
        root,
        command_log,
        "host-liveness",
        "--lease-id",
        lease_id,
        "--packet-id",
        pm_packet,
        "--status",
        "not_found",
        "--source",
        "fake_host_probe",
    )
    guard = liveness.get("lifecycle_guard", {})
    ensure(guard.get("decision") == "reissue_or_replace_lease", f"host not_found did not force recovery: {guard}")
    ensure(
        guard.get("wait_recovery", {}).get("last_liveness_status") == "not_found",
        f"host liveness status not visible in guard: {guard}",
    )
    ensure(liveness.get("foreground_duty", {}).get("action") == "recover_or_reissue", f"host liveness lost duty: {liveness}")
    return {
        "name": "host_liveness_bridge_recovery",
        "ok": True,
        "root": str(root),
        "observations": {
            "decision": guard.get("decision"),
            "liveness_status": guard.get("wait_recovery", {}).get("last_liveness_status"),
        },
        "commands": command_log,
    }


def scenario_orphan_runner_summary_recovery(work_root: Path) -> dict[str, Any]:
    command_log: list[dict[str, Any]] = []
    root = reset_scenario_root(work_root, "orphan_runner_summary_recovery")
    current_payload = start_rehearsal(root, command_log, "run-fake-orphan-summary")
    pm_packet = str(current_payload["next_action"]["subject_id"])
    lease_payload = resolve_and_lease_packet(
        root,
        command_log,
        packet_id=pm_packet,
        responsibility="pm",
        agent_id="fake-pm-orphan-summary",
    )
    run_cli(root, command_log, "ack", "--lease-id", str(lease_payload["lease_id"]), "--packet-id", pm_packet)
    current = json.loads((root / ".flowpilot" / "current.json").read_text(encoding="utf-8"))
    runner_summary = Path(str(current["run_root"])) / "evidence" / "flowguard" / pm_packet / "runner_summary.json"
    runner_summary.parent.mkdir(parents=True, exist_ok=True)
    runner_summary.write_text(
        json.dumps({"status": "completed", "runners": [{"name": "fake-runner", "exit_code": 0}]}, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    patrol = run_cli(root, command_log, "patrol")
    guard = patrol.get("lifecycle_guard", {})
    ensure(guard.get("decision") == "reissue_or_replace_lease", f"orphan evidence did not route reissue recovery: {guard}")
    ensure(patrol.get("foreground_duty", {}).get("action") == "recover_or_reissue", f"orphan evidence lost duty: {patrol}")
    projection = status_projection(root, command_log)
    packet = packet_row(projection, pm_packet)
    ensure(packet.get("status") == "acknowledged", f"orphan evidence auto-mutated packet: {packet}")
    ensure(not packet.get("accepted_result_id"), f"orphan evidence auto-accepted packet: {packet}")
    ensure(projection.get("orphan_evidence"), f"orphan evidence not projected: {projection}")
    return {
        "name": "orphan_runner_summary_recovery",
        "ok": True,
        "root": str(root),
        "observations": {
            "decision": guard.get("decision"),
            "packet_status": packet.get("status"),
            "orphan_count": len(projection.get("orphan_evidence", [])),
        },
        "commands": command_log,
    }


def scenario_unsupported_side_command(work_root: Path) -> dict[str, Any]:
    command_log: list[dict[str, Any]] = []
    root = reset_scenario_root(work_root, "unsupported_side_command")
    help_result = run_raw_cli(root, command_log, "--help")
    ensure(help_result.returncode == 0, f"help failed: {help_result.stderr}")
    for expected in ("start", "run-until-wait", "status", "patrol", "submit-result"):
        ensure(expected in help_result.stdout, f"formal command missing from help: {expected}")
    for retired in ("run-fake-e2e", "headless-startup-text"):
        ensure(retired not in help_result.stdout, f"retired command appears in help: {retired}")
    for unsupported in ("complete-flowguard", "record-validation", "close"):
        ensure(unsupported not in help_result.stdout, f"unsupported command appears in help: {unsupported}")

    rejected = run_raw_cli(root, command_log, "--json", "complete-flowguard")
    ensure(rejected.returncode != 0, "unsupported complete-flowguard command was accepted")
    ensure("invalid choice" in rejected.stderr, f"unsupported command did not fail as invalid choice: {rejected.stderr}")
    return {
        "name": "unsupported_side_command",
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
    ("slow_reviewer_progress_preserved", scenario_slow_reviewer_progress_preserved),
    ("accepted_packet_reassignment_rejected", scenario_accepted_packet_reassignment_rejected),
    ("stop_terminal_fence", scenario_stop_terminal_fence),
    ("host_liveness_bridge_recovery", scenario_host_liveness_bridge_recovery),
    ("orphan_runner_summary_recovery", scenario_orphan_runner_summary_recovery),
    ("unsupported_side_command", scenario_unsupported_side_command),
)


def run_scenario(name: str, fn: Callable[[Path], dict[str, Any]], work_root: Path) -> dict[str, Any]:
    try:
        return fn(work_root)
    except Exception as exc:  # pragma: no cover - exercised by failing validation.
        return {"name": name, "ok": False, "error": str(exc)}


def run_all_scenarios(work_root: Path) -> list[dict[str, Any]]:
    return [run_scenario(name, fn, work_root) for name, fn in SCENARIOS]
