"""Deterministic fake-host end-to-end rehearsal for ``flowpilot_new.py``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from . import cockpit, host, router, run_shell, runtime


StartRun = Callable[..., dict[str, Any]]

CURRENT_REPORT_FAKE_SUCCESS_FIELD_MARKERS = (
    "modeled_boundary",
    "independent_challenge",
    "missing_test_kinds",
    "evidence_consistency",
)


def _route_plan_body() -> str:
    return json.dumps(
        {
            "schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION,
            "decision": "pass",
            "nodes": [
                {
                    "node_id": "node-001",
                    "title": "Implement target behavior",
                    "responsibility": "worker",
                    "modeled_target": "development_process",
                    "acceptance_criteria": [
                        "Target behavior is implemented in the bounded project scope.",
                        "Worker result references current changed files and evidence.",
                    ],
                },
                {
                    "node_id": "node-002",
                    "title": "Validate implementation evidence",
                    "responsibility": "worker",
                    "modeled_target": "model_test_alignment",
                    "acceptance_criteria": [
                        "FlowGuard and ordinary checks are current for the node.",
                        "Evidence is sufficient for independent review.",
                    ],
                },
                {
                    "node_id": "node-003",
                    "title": "Prepare final closure package",
                    "responsibility": "worker",
                    "modeled_target": "development_process",
                    "acceptance_criteria": [
                        "Final route-wide ledger can account for every effective node.",
                        "Closure evidence is body-free and reviewable from public status.",
                    ],
                },
            ],
        },
        sort_keys=True,
    )


def _body_for_packet(packet: dict[str, Any]) -> str:
    envelope = packet["envelope"]
    kind = envelope.get("packet_kind", "task")
    scope = envelope.get("route_scope", "")
    if kind == "task" and scope == "high_standard_contract":
        payload = runtime._packet_result_minimal_valid_shape(packet)
        payload["requirements"][0]["summary"] = "Deliver the requested FlowPilot work to a high standard."
        payload["requirements"][0]["source_user_intent"] = "sealed_startup_intake"
        payload["requirements"].append(
            {
                "requirement_id": "hsr-002",
                "classification": "high_standard_current",
                "summary": "Every node must have current evidence and review.",
                "source_user_intent": "sealed_startup_intake",
                "evidence_rule": "Direct current node evidence, FlowGuard evidence, Reviewer challenge, and PM absorption required.",
                "closure_blocking": True,
                "report_only_closure_allowed": False,
            }
        )
        return json.dumps(payload)
    if kind == "task" and scope == "discovery":
        return json.dumps(
            {
                "decision": "pass",
                "material_sources": ["sealed_startup_intake", "current_repository"],
                "material_sufficiency": "sufficient_for_route_planning",
                "local_skill_inventory": ["flowguard-development-process-flow"],
                "candidate_only_skill_policy": True,
            }
        )
    if kind == "task" and scope == "skill_standard":
        return json.dumps(
            {
                "decision": "pass",
                "obligations": [
                    {
                        "obligation_id": "skill-std-001",
                        "skill": "flowguard-development-process-flow",
                        "classification": "required",
                        "role_use": "flowguard_operator",
                        "use_context": "node_validation",
                        "evidence_required": "current-run FlowGuard work order",
                        "closure_blocking": True,
                    }
                ]
            }
        )
    if kind == "task" and scope == "planning":
        return _route_plan_body()
    if kind == "task" and scope == "node_acceptance_plan":
        node_id = envelope.get("route_node_id", "")
        return json.dumps(
            {
                "decision": "pass",
                "route_node_id": node_id,
                "proof_obligations": ["implementation evidence", "FlowGuard evidence", "review", "validation"],
                "repair_policy": "repair_scope_replacement_default",
                "low_quality_success_risks": ["existence-only evidence", "missing skill evidence"],
                "node_context_package": {
                    "node_id": node_id,
                    "purpose": "Complete the current route node with bounded worker execution, FlowGuard checks, review, and validation.",
                    "acceptance_criteria": [
                        "worker result satisfies the node packet",
                        "node-plan Reviewer, post-result FlowGuard, and final Reviewer evidence are current",
                        "reviewer independently challenges the node outcome",
                    ],
                    "relevant_references": ["route node contract", "high standard contract", "runtime ledger"],
                    "evidence_targets": ["worker result body", "FlowGuard report", "reviewer report", "validation output"],
                    "inspection_targets": ["changed files", "command output", "model artifacts", "runtime ledger"],
                    "known_risks": ["existence-only evidence", "stale generation", "review without active inspection"],
                    "flowguard_targets": ["development-process route", "model-test alignment where applicable"],
                    "reviewer_starting_points": ["worker result", "node context package", "FlowGuard reports", "validation evidence"],
                    "high_standard_requirement_ids": ["hsr-001", "hsr-002"],
                    "low_quality_success_risks": ["existence-only evidence", "generic pass without hard-part proof"],
                    "semantic_downgrade_risks": ["accepted node does not prove user-visible completion"],
                    "work_packet_projection": ["copy hard requirements, risk probes, and test obligations into Worker, FlowGuard, Reviewer, and PM disposition packets"],
                    "final_user_intent_checks": ["node evidence advances the sealed startup request"],
                    "structure_hygiene_expectation": ["no compatibility branch, fallback parser, or stale artifact may be introduced"],
                    "direct_evidence_closure_rules": ["report-only closure is not sufficient for covered hard requirements"],
                    "test_obligation_matrix": {
                        "pre_worker": [
                            {
                                "obligation_id": f"test-{node_id or 'active'}-001",
                                "source": "node_acceptance_plan",
                                "required_test_kind": "targeted_current_validation",
                                "owner_role": "worker",
                                "expected_evidence": "current validation evidence",
                                "freshness_rule": "after worker result for the current node",
                                "pm_disposition": "pending",
                            }
                        ]
                    },
                },
            }
        )
    if kind == "task" and scope == "parent_backward_replay":
        return json.dumps(
            {
                "route_node_id": envelope.get("route_node_id", ""),
                "decision": "pass",
                "pm_visible_summary": ["Reviewer accepted the parent backward replay."],
                "composition_checked": True,
            }
        )
    family_id = runtime._packet_result_family_id(packet)
    if family_id == "review.terminal_backward_replay":
        payload = runtime._packet_result_minimal_valid_shape(packet)
        try:
            packet_body = json.loads(packet.get("body") or "{}")
        except json.JSONDecodeError:
            packet_body = {}
        segment_targets = packet_body.get("segment_targets") if isinstance(packet_body, dict) else []
        if isinstance(segment_targets, list) and segment_targets:
            payload["segment_reviews"] = [
                {
                    "segment_id": str(target.get("segment_id") or f"segment-{index}"),
                    "segment_kind": str(target.get("segment_kind") or "route_segment"),
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "pm_segment_decision": "continue",
                    "direct_evidence_paths_checked": [str(target.get("summary") or target.get("segment_id") or "current segment")],
                }
                for index, target in enumerate(segment_targets, start=1)
                if isinstance(target, dict)
            ]
        return json.dumps(payload, sort_keys=True)
    if family_id.startswith("flowguard_check.") or family_id == "review.any_current_subject":
        return json.dumps(runtime._packet_result_minimal_valid_shape(packet), sort_keys=True)
    if family_id == "pm_flowguard_acceptance.pm_flowguard_acceptance":
        payload = runtime._packet_result_minimal_valid_shape(packet)
        try:
            packet_body = json.loads(packet.get("body") or "{}")
        except json.JSONDecodeError:
            packet_body = {}
        if isinstance(packet_body, dict) and packet_body.get("flowguard_result_id"):
            payload["accepted_flowguard_result_id"] = str(packet_body["flowguard_result_id"])
        payload["flowguard_absorption"] = "fake PM absorbed the current FlowGuard report before Reviewer review"
        return json.dumps(payload, sort_keys=True)
    if kind == "pm_disposition":
        payload = runtime._packet_result_minimal_valid_shape(packet)
        try:
            packet_body = json.loads(packet.get("body") or "{}")
        except json.JSONDecodeError:
            packet_body = {}
        if isinstance(packet_body, dict) and isinstance(packet_body.get("minimal_valid_shape"), dict):
            payload = dict(packet_body["minimal_valid_shape"])
        payload["reason"] = "fake PM accepts current node after absorbing current evidence"
        return json.dumps(payload, sort_keys=True)
    return json.dumps(
        {
            "decision": "pass",
            "pm_visible_summary": [f"fake {kind} result for packet {packet['packet_id']}"],
        },
        sort_keys=True,
    )


def _fault_body_for_packet(packet: dict[str, Any]) -> str:
    family_id = runtime._packet_result_family_id(packet)
    if family_id == "task.high_standard_contract":
        return json.dumps(
            {
                "overall_contract": "old contract wrapper must be rejected",
                "contract_rows": [],
            },
            sort_keys=True,
        )
    if family_id == "task.skill_standard":
        return json.dumps(
            {
                "decision": "pass",
                "selected_skills": ["flowguard-development-process-flow"],
            },
            sort_keys=True,
        )
    if family_id == "task.node_acceptance_plan":
        return json.dumps(
            {
                "decision": "pass",
                "repair_policy": "repair_scope_replacement_default",
            },
            sort_keys=True,
        )
    if family_id == "pm_disposition.node_pm_disposition":
        return json.dumps(
            {
                "decision": "accept",
                "summary": "old PM disposition summary must be rejected as a reason alias",
            },
            sort_keys=True,
        )
    if family_id.startswith("flowguard_check.") or family_id in {
        "review.any_current_subject",
        "review.terminal_backward_replay",
    }:
        return json.dumps(
            {
                "decision": "pass",
                "pm_visible_summary": ["old generic result body must be rejected for this packet family"],
            },
            sort_keys=True,
        )
    return _body_for_packet(packet)


def _consistency_fault_body_for_packet(packet: dict[str, Any]) -> str:
    family_id = runtime._packet_result_family_id(packet)
    if family_id.startswith("flowguard_check."):
        payload = runtime._packet_result_minimal_valid_shape(packet)
        payload["pm_visible_summary"] = [
            "current-shaped FlowGuard result must be rejected because hard child evidence blocks."
        ]
        payload["passed"] = True
        payload["evidence_consistency"] = {
            "self_check_passed": True,
            "child_reports_all_passed": False,
            "blocking_child_reports": [
                {
                    "report_path": "evidence/flowguard/current/model_test_alignment_report.json",
                    "decision": "missing_code_contract",
                }
            ],
            "hard_evidence_decision": "missing_code_contract",
        }
        return json.dumps(payload, sort_keys=True)
    return _fault_body_for_packet(packet)


def run_fake_e2e(
    root: Path,
    *,
    run_id: str | None,
    startup_text: str,
    start_run: StartRun,
    inject_contract_faults: bool = False,
    inject_consistency_faults: bool = False,
) -> dict[str, Any]:
    start_result = start_run(
        root,
        run_id=run_id,
        headless_startup_text=startup_text,
        require_formal_ui=False,
    )
    shell = run_shell.load_run_shell(root, run_id=start_result["run"]["run_id"])
    ledger = run_shell.load_run_ledger(shell)

    def complete_leased_packet(packet_id: str, *, agent_id: str, body: str) -> tuple[str, str]:
        packet = ledger["packets"][packet_id]
        responsibility = packet["envelope"]["responsibility"]
        lease_id = host.lease_responsibility(
            ledger,
            responsibility,
            host_kind="fake",
            agent_id=agent_id,
            packet_id=packet_id,
            scope="e2e",
        )
        runtime.assign_packet(ledger, packet_id, lease_id)
        runtime.ack_lease(ledger, lease_id, packet_id)
        runtime.open_authorized_input_materials_for_role(ledger, packet_id, lease_id)
        result_id = host.submit_host_result(ledger, lease_id, packet_id, body)
        return lease_id, result_id

    completed_packets: list[dict[str, str]] = []
    folded_boundaries: list[dict[str, Any]] = []
    injected_fault_families: set[str] = set()
    injected_consistency_fault_families: set[str] = set()
    mechanical_contract_blocks: list[dict[str, Any]] = []
    for index in range(80):
        boundary = runtime.run_until_wait(ledger)
        folded_boundaries.append(boundary)
        action_json = boundary["next_action"]
        action_type = str(action_json.get("action_type") or "")
        if action_type == "terminal_complete":
            break
        if action_type != "dispatch_current_role":
            raise runtime.BlackBoxRuntimeError(f"fake e2e cannot satisfy next action: {action_json}")
        packet_id = str(action_json.get("subject_id") or "")
        packet = ledger["packets"][packet_id]
        kind = packet["envelope"].get("packet_kind", "task")
        family_id = runtime._packet_result_family_id(packet)
        should_fault = inject_contract_faults and family_id in {
            "task.high_standard_contract",
            "task.skill_standard",
            "task.node_acceptance_plan",
            "flowguard_check.post_result",
            "review.any_current_subject",
            "review.terminal_backward_replay",
            "pm_flowguard_acceptance.pm_flowguard_acceptance",
            "pm_disposition.node_pm_disposition",
        } and family_id not in injected_fault_families
        should_consistency_fault = (
            inject_consistency_faults
            and family_id == "flowguard_check.post_result"
            and family_id not in injected_consistency_fault_families
        )
        if should_consistency_fault:
            body = _consistency_fault_body_for_packet(packet)
            injected_consistency_fault_families.add(family_id)
        elif should_fault:
            body = _fault_body_for_packet(packet)
            injected_fault_families.add(family_id)
        else:
            body = _body_for_packet(packet)
        lease_id, result_id = complete_leased_packet(
            packet_id,
            agent_id=f"fake-{kind}-{index}",
            body=body,
        )
        result = ledger["results"][result_id]
        if result.get("status") == "mechanical_contract_blocked":
            mechanical_contract_blocks.append(
                {
                    "packet_id": packet_id,
                    "result_id": result_id,
                    "contract_family_id": str(result.get("contract_family_id") or ""),
                    "missing_required_fields": list(result.get("missing_required_fields") or []),
                    "forbidden_fields_seen": list(result.get("forbidden_fields_seen") or []),
                    "quarantine_reason": str(result.get("quarantine_reason") or ""),
                }
            )
        completed_packets.append({"packet_id": packet_id, "packet_kind": kind, "lease_id": lease_id, "result_id": result_id})
    else:
        raise runtime.BlackBoxRuntimeError("fake e2e exceeded packet completion budget")

    closure = ledger.get("closure") or {"decision": "not_attempted"}
    run_shell.save_run_ledger(shell, ledger)
    return {
        "ok": closure["decision"] == "complete",
        "mode": "rehearsal",
        "run": shell.to_json(),
        "completed_packets": completed_packets,
        "mechanical_contract_blocks": mechanical_contract_blocks,
        "injected_fault_families": sorted(injected_fault_families),
        "injected_consistency_fault_families": sorted(injected_consistency_fault_families),
        "folded_boundaries": folded_boundaries,
        "accepted_node_ids": [
            node_id for node_id, node in ledger.get("route_nodes", {}).items() if node.get("status") == "accepted"
        ],
        "final_route_wide_gate_ledger": ledger.get("final_route_wide_gate_ledger"),
        "closure": closure,
        "next_action": router.router_next_action(ledger).to_json(),
        "lifecycle_guard": ledger.get("lifecycle_guard", {}),
        "foreground_duty": ledger.get("foreground_duty", {}),
        "final_return_preflight": runtime.final_return_preflight(
            ledger,
            guard=ledger.get("lifecycle_guard") if isinstance(ledger.get("lifecycle_guard"), dict) else None,
        ),
        "status": cockpit.render_status(ledger),
    }
