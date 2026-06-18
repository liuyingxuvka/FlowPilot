from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))

runtime = importlib.import_module("flowpilot_core_runtime.runtime")
host = importlib.import_module("flowpilot_core_runtime.host")
packet_result_contracts = importlib.import_module("flowpilot_core_runtime.packet_result_contracts")
packet_stage_evidence_matrix = importlib.import_module("flowpilot_core_runtime.packet_stage_evidence_matrix")
review_window_contracts = importlib.import_module("flowpilot_core_runtime.review_window_contracts")


def _contract_child_fields(family_id: str) -> list[str]:
    return list(packet_result_contracts.PACKET_RESULT_CONTRACTS_BY_FAMILY[family_id].get("required_child_fields") or [])


def _pass_body(summary: str = "Current packet evidence passed.", **fields: object) -> str:
    payload: dict[str, object] = {
        "decision": "pass",
        "pm_visible_summary": [summary],
        "current_evidence_refs": ["current-high-standard-evidence"],
    }
    payload.update(fields)
    return json.dumps(payload)


def _flowguard_pass_body(summary: str = "FlowGuard accepted the current packet evidence.", **fields: object) -> str:
    payload = packet_result_contracts.minimal_valid_shape_for_family("flowguard_check.post_result")
    payload["pm_visible_summary"] = [summary]
    payload.update(fields)
    return json.dumps(payload)


def _flowguard_semantic_recheck_body_from_packet(
    ledger: dict,
    packet_id: str,
    summary: str = "FlowGuard accepted the blocker-bound semantic recheck.",
    **fields: object,
) -> str:
    payload = json.loads(_flowguard_pass_body(summary))
    packet = ledger["packets"][packet_id]
    profile_bindings = packet["envelope"].get("result_contract_profile_bindings", {})
    semantic_binding = (
        profile_bindings.get("flowguard.semantic_recheck_required", {})
        if isinstance(profile_bindings, dict)
        else {}
    )
    if isinstance(semantic_binding, dict) and semantic_binding:
        authorized_read_ids = [
            str(item)
            for item in semantic_binding.get("authorized_result_read_ids", [])
            if str(item)
        ]
        payload["semantic_recheck"] = {
            "blocker_id": str(semantic_binding.get("blocker_id") or ""),
            "subject_result_consumed": True,
            "subject_bound_semantic_coverage": True,
            "coverage_boundary": str(semantic_binding.get("coverage_boundary") or "subject_bound_semantic"),
            "consumed_authorized_result_read_ids": authorized_read_ids,
            "consumed_repair_obligation_ids": list(semantic_binding.get("repair_obligation_ids") or []),
        }
    payload.update(fields)
    return json.dumps(payload)


def _semantic_recheck_payload(blocker_id: str, authorized_read_ids: list[str] | None = None) -> dict[str, object]:
    return {
        "blocker_id": blocker_id,
        "subject_result_consumed": True,
        "subject_bound_semantic_coverage": True,
        "coverage_boundary": "subject_bound_semantic",
        "consumed_authorized_result_read_ids": authorized_read_ids or [],
    }


def _flowguard_block_body(summary: str, *, blocker_class: str, recommended_resolution: str, **fields: object) -> str:
    payload = packet_result_contracts.minimal_valid_shape_for_family("flowguard_check.post_result")
    payload.update(
        {
            "pm_visible_summary": [summary],
            "passed": False,
            "blockers": [
                {
                    "blocker_id": "flowguard-block-current",
                    "blocker_class": blocker_class,
                    "next_action": "pm_flowguard_acceptance",
                    "recommended_resolution": recommended_resolution,
                }
            ],
        }
    )
    payload.update(fields)
    return json.dumps(payload)


def _review_pass_body(summary: str = "Reviewer accepted the current packet evidence.", **fields: object) -> str:
    payload = packet_result_contracts.minimal_valid_shape_for_family("review.any_current_subject")
    payload["pm_visible_summary"] = [summary]
    payload.update(fields)
    return json.dumps(payload)


def _terminal_backward_replay_body(packet: dict) -> str:
    payload = packet_result_contracts.minimal_valid_shape_for_family("review.terminal_backward_replay")
    try:
        body = json.loads(packet.get("body") or "{}")
    except json.JSONDecodeError:
        body = {}
    targets = body.get("segment_targets") if isinstance(body, dict) else []
    if isinstance(targets, list) and targets:
        payload["route_segment_replay"] = [
            {
                "segment_id": str(target.get("segment_id") or f"segment-{index}"),
                "segment_kind": str(target.get("segment_kind") or "route_segment"),
                "status": "closed",
                "basis": str(target.get("summary") or target.get("segment_id") or "current segment"),
            }
            for index, target in enumerate(targets, start=1)
            if isinstance(target, dict)
        ]
    return json.dumps(payload)


def _parent_backward_replay_body(parent_node_id: str, child_node_ids: list[str], child_evidence_refs: list[str]) -> str:
    payload = packet_result_contracts.minimal_valid_shape_for_family("task.parent_backward_replay")
    payload.update(
        {
            "parent_node_id": parent_node_id,
            "child_node_ids": child_node_ids,
            "child_evidence_refs": child_evidence_refs,
            "composition_decision": "pass",
            "blockers": [],
        }
    )
    return json.dumps(payload)


def _review_block_body(summary: str, *, blocker_class: str, recommended_resolution: str, **fields: object) -> str:
    payload = packet_result_contracts.minimal_valid_shape_for_family("review.any_current_subject")
    payload.update(
        {
            "pm_visible_summary": [summary],
            "passed": False,
            "findings": [summary],
            "blockers": [
                {
                    "blocker_id": "review-block-current",
                    "blocker_class": blocker_class,
                    "next_action": "repair_current_scope",
                    "recommended_resolution": recommended_resolution,
                }
            ],
        }
    )
    payload.update(fields)
    return json.dumps(payload)


def _block_body(summary: str, *, blocker_class: str, recommended_resolution: str, **fields: object) -> str:
    payload: dict[str, object] = {
        "decision": "block",
        "blocking": True,
        "blocker_class": blocker_class,
        "recommended_resolution": recommended_resolution,
        "pm_visible_summary": [summary],
        "current_evidence_refs": ["current-high-standard-blocker-evidence"],
    }
    payload.update(fields)
    return json.dumps(payload)


_PM_REPAIR_OBLIGATION_DISPOSITION_BY_DECISION = {
    "repair_current_scope": "fresh_repair_packet_required",
    "repair_parent_scope": "parent_scope_repair_required",
    "redesign_route": "route_redesign_required",
    "waive_with_authority": "waived_with_authority",
    "stop_for_user": "stop_for_user",
}

_PM_REPAIR_OBLIGATION_RETURN_GATE_BY_DECISION = {
    "repair_current_scope": "flowguard_then_reviewer",
    "repair_parent_scope": "flowguard_then_reviewer",
    "redesign_route": "route_redesign_gate",
    "waive_with_authority": "authority_waiver_gate",
    "stop_for_user": "terminal_user_stop",
}


def _pm_repair_body_from_packet(
    ledger: dict,
    packet_id: str,
    summary: str,
    *,
    decision: str,
    reason: str,
    **fields: object,
) -> str:
    packet_body = json.loads(ledger["packets"][packet_id]["body"])
    payload = dict(packet_body.get("minimal_valid_shape") or {})
    payload.update(
        {
            "decision": decision,
            "next_action": decision,
            "reason": reason,
            "pm_visible_summary": [summary],
        }
    )
    obligations = packet_body.get("repair_evidence_obligations")
    if isinstance(obligations, list) and obligations:
        payload["repair_obligation_disposition"] = [
            {
                "obligation_id": str(row.get("obligation_id") or ""),
                "disposition": _PM_REPAIR_OBLIGATION_DISPOSITION_BY_DECISION[decision],
                "return_gate": _PM_REPAIR_OBLIGATION_RETURN_GATE_BY_DECISION[decision],
                "evidence_kind": "fresh_current_evidence",
            }
            for row in obligations
            if isinstance(row, dict)
        ]
    payload.update(fields)
    return json.dumps(payload)


def _pm_disposition_body(
    summary: str = "PM accepted the current node after absorbing role evidence.",
    **fields: object,
) -> str:
    payload = packet_result_contracts.minimal_valid_shape_for_family("pm_disposition.node_pm_disposition")
    payload["reason"] = summary
    payload.update(fields)
    return json.dumps(payload)


def _pm_disposition_body_from_packet(
    ledger: dict,
    packet_id: str,
    summary: str = "PM accepted the current node after absorbing role evidence.",
    **fields: object,
) -> str:
    packet_body = json.loads(ledger["packets"][packet_id].get("body") or "{}")
    if isinstance(packet_body.get("minimal_valid_shape"), dict):
        payload = json.loads(json.dumps(packet_body["minimal_valid_shape"]))
    else:
        payload = json.loads(_pm_disposition_body(summary))
    payload["reason"] = summary
    payload.update(fields)
    return json.dumps(payload)


def _high_standard_contract_body() -> str:
    return json.dumps(
        {
            "requirements": [
                {
                    "requirement_id": "hsr-001",
                    "classification": "hard_current",
                    "summary": "Complete the requested outcome.",
                    "source_user_intent": "sealed_startup_intake",
                    "closure_rule": "Future owner nodes and terminal replay must close this item with current evidence.",
                }
            ],
            "acceptance_item_registry": {
                "schema_version": runtime.ACCEPTANCE_ITEM_REGISTRY_SCHEMA_VERSION,
                "items": [
                    {
                        "acceptance_item_id": "acc-001",
                        "source_type": "user_explicit",
                        "source_requirement_ids": ["hsr-001"],
                        "summary": "Complete the requested outcome.",
                        "quality_floor": "high_quality_required",
                        "future_evidence_rule": "Future owner nodes and terminal replay must close this item.",
                        "status": "active",
                    },
                    {
                        "acceptance_item_id": "acc-002",
                        "source_type": "pm_high_standard",
                        "source_requirement_ids": ["hsr-001"],
                        "summary": "Hold the result to the highest reasonable current-run quality bar.",
                        "quality_floor": "high_quality_required",
                        "future_evidence_rule": "Future owner nodes and terminal replay must close this item.",
                        "status": "active",
                    },
                ],
            },
        }
    )


def _discovery_body() -> str:
    return json.dumps(
        {
            "decision": "pass",
            "material_sources": ["startup"],
            "material_sufficiency": "sufficient_for_route_planning",
            "candidate_skill_inventory": ["flowguard-development-process-flow"],
        }
    )


def _skill_standard_body() -> str:
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
                    "evidence_rule": "FlowGuard operator produces current model/report evidence in its own packet.",
                }
            ],
        }
    )


def _ledger() -> dict:
    ledger = runtime.new_ledger("Build target", "Finish only with high-standard evidence.")
    ledger["startup_intake"] = {
        "sealed": True,
        "startup_answers": {
            runtime.BACKGROUND_COLLABORATION_ACK_FIELD: True,
        },
    }
    ledger["recursive_route_execution_required"] = True
    ledger["high_standard_control_flow_required"] = True
    runtime.create_route(ledger, "High-standard route", ["planning", "implementation", "validation"])
    runtime.ensure_preplanning_gate_packet(ledger)
    return ledger


def _open_packets(ledger: dict, *, kind: str | None = None, scope: str | None = None) -> list[str]:
    rows: list[str] = []
    for packet_id, packet in ledger["packets"].items():
        envelope = packet["envelope"]
        if packet["status"] != "open":
            continue
        if kind and envelope.get("packet_kind", "task") != kind:
            continue
        if scope and envelope.get("route_scope") != scope:
            continue
        rows.append(packet_id)
    return rows


def _complete_open_packet(ledger: dict, packet_id: str, body: str | None = None) -> str:
    if body is None:
        body = _pass_body()
    packet = ledger["packets"][packet_id]
    if packet["envelope"].get("packet_kind") == "pm_disposition":
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {}
        packet_body = json.loads(packet.get("body") or "{}")
        if isinstance(payload, dict) and isinstance(packet_body.get("minimal_valid_shape"), dict):
            if payload.get("acceptance_item_disposition") == packet_result_contracts.minimal_valid_shape_for_family(
                "pm_disposition.node_pm_disposition"
            ).get("acceptance_item_disposition"):
                payload["acceptance_item_disposition"] = packet_body["minimal_valid_shape"].get(
                    "acceptance_item_disposition",
                    payload.get("acceptance_item_disposition"),
                )
                body = json.dumps(payload)
    blocker_id = str(packet.get("repair_blocker_id") or packet["envelope"].get("repair_blocker_id") or "")
    if packet["envelope"].get("packet_kind") == "flowguard_check" and blocker_id:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload, dict) and "semantic_recheck" not in payload:
            authorized_read_ids = [
                str(row.get("result_id") or "")
                for row in packet["envelope"].get("authorized_result_reads", [])
                if row.get("required_before_submit") is True and str(row.get("result_id") or "")
            ]
            payload["semantic_recheck"] = _semantic_recheck_payload(blocker_id, authorized_read_ids)
            body = json.dumps(payload)
    responsibility = packet["envelope"]["responsibility"]
    lease_id = host.lease_responsibility(
        ledger,
        responsibility,
        host_kind="fake",
        agent_id=f"{responsibility}-{packet_id}",
        packet_id=packet_id,
        scope="high-standard-test",
    )
    runtime.assign_packet(ledger, packet_id, lease_id)
    runtime.ack_lease(ledger, lease_id, packet_id)
    runtime.open_authorized_input_materials_for_role(ledger, packet_id, lease_id)
    if packet["envelope"].get("packet_kind") == "flowguard_check":
        _write_flowguard_evidence_artifact(ledger, packet, body or "")
    return host.submit_host_result(ledger, lease_id, packet_id, body)


def _write_flowguard_evidence_artifact(ledger: dict, packet: dict, body: str) -> None:
    path = runtime._flowguard_packet_evidence_artifact_path(ledger, packet)
    if path is None:
        return
    decision = "pass"
    try:
        payload = json.loads(body or "{}")
    except json.JSONDecodeError:
        payload = {}
    if isinstance(payload, dict) and payload.get("passed") is False:
        decision = "blocked"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "flowpilot.flowguard_evidence.v1",
                "model_test_alignment_report": {
                    "decision": decision,
                    "failed_predicates": [] if decision == "pass" else ["high_standard_test_block"],
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _complete_task_chain(ledger: dict, packet_id: str | None = None, body: str | None = None) -> None:
    if packet_id is None:
        raise AssertionError("packet_id is required for the current FlowPilot task chain")
    _complete_open_packet(ledger, packet_id, body)
    flowguard_packets = _open_packets(ledger, kind="flowguard_check")
    if flowguard_packets:
        _complete_open_packet(
            ledger,
            flowguard_packets[0],
            _flowguard_pass_body("FlowGuard checked the current packet evidence."),
        )
    review_packets = _open_packets(ledger, kind="review")
    if review_packets:
        _complete_open_packet(
            ledger,
            review_packets[0],
            _review_pass_body("Reviewer accepted the current packet evidence."),
        )


def _complete_preplanning(ledger: dict) -> None:
    _complete_task_chain(
        ledger,
        _open_packets(ledger, scope="high_standard_contract")[0],
        _high_standard_contract_body(),
    )
    _complete_task_chain(
        ledger,
        _open_packets(ledger, scope="discovery")[0],
        _discovery_body(),
    )
    _complete_task_chain(
        ledger,
        _open_packets(ledger, scope="skill_standard")[0],
        _skill_standard_body(),
    )


def _route_plan_body(nodes: list[dict] | None = None) -> str:
    route_nodes = nodes or [
        {
            "node_id": "node-001",
            "title": "Plan architecture",
            "modeled_target": "development_process",
            "acceptance_criteria": ["Architecture plan is accepted with high-standard evidence."],
            "high_standard_requirement_ids": ["hsr-001"],
            "skill_standard_obligation_ids": ["skill-std-001"],
        },
        {
            "node_id": "node-002",
            "title": "Implement behavior",
            "modeled_target": "development_process",
            "acceptance_criteria": ["Behavior implementation is accepted with high-standard evidence."],
            "high_standard_requirement_ids": ["hsr-001"],
            "skill_standard_obligation_ids": ["skill-std-001"],
        },
        {
            "node_id": "node-003",
            "title": "Validate evidence",
            "modeled_target": "development_process",
            "acceptance_criteria": ["Validation evidence is accepted with high-standard evidence."],
            "high_standard_requirement_ids": ["hsr-001"],
            "skill_standard_obligation_ids": ["skill-std-001"],
        },
    ]
    normalized_nodes: list[dict] = []
    for node in route_nodes:
        normalized = dict(node)
        normalized.setdefault("acceptance_item_ids", ["acc-001", "acc-002"])
        normalized_nodes.append(normalized)
    return json.dumps(
        {
            "schema_version": runtime.ROUTE_PLAN_SCHEMA_VERSION,
            "decision": "pass",
            "pm_visible_summary": ["PM accepted the route plan."],
            "nodes": normalized_nodes,
        }
    )


def _route_plan_obj(nodes: list[dict]) -> dict:
    if nodes and str(nodes[0].get("node_kind") or "") in {"parent", "module"} and nodes[0].get("child_node_ids"):
        return json.loads(_route_plan_body(nodes))
    child_nodes: list[dict] = []
    child_ids: list[str] = []
    for index, node in enumerate(nodes, start=1):
        child = dict(node)
        child.setdefault("node_id", f"redesign-leaf-{index:03d}")
        child.setdefault("node_kind", "leaf")
        child["parent_node_id"] = "redesign-module-001"
        child["child_node_ids"] = []
        child_ids.append(str(child["node_id"]))
        child_nodes.append(child)
    parent = {
        "node_id": "redesign-module-001",
        "title": "Redesign current route scope",
        "node_kind": "module",
        "parent_node_id": "",
        "child_node_ids": child_ids,
        "responsibility": "pm",
        "modeled_target": "development_process",
        "acceptance_criteria": ["Redesign scope is decomposed into executable child work."],
        "acceptance_item_ids": [],
    }
    return json.loads(_route_plan_body([parent, *child_nodes]))


def _complete_planning(ledger: dict) -> None:
    _complete_task_chain(
        ledger,
        _open_packets(ledger, scope="planning")[0],
        _route_plan_body(),
    )


def _node_context_body(ledger: dict) -> str:
    node_id = ledger["execution_frontier"]["active_node_id"]
    node = ledger["route_nodes"][node_id]
    acceptance_item_ids = list(node.get("acceptance_item_ids") or [])
    return json.dumps(
        {
            "decision": "pass",
            "pm_visible_summary": ["PM accepted the node context package."],
            "repair_policy": "repair_scope_replacement_default",
            "node_context_package": {
                "purpose": f"Execute and verify {node['title']}",
                "acceptance_criteria": list(node.get("acceptance_criteria") or []),
                "relevant_references": [
                    {"kind": "route_node", "id": node_id},
                    {"kind": "node_acceptance_plan_packet", "id": _open_packets(ledger, scope="node_acceptance_plan")[0]},
                ],
                "known_risks": ["thin evidence", "wrong FlowGuard target", "stale repair-generation evidence"],
                "acceptance_item_projection": [
                    {
                        "acceptance_item_id": str(item_id),
                        "status_for_this_node": "complete_here",
                        "future_evidence_rule": "Direct current evidence, FlowGuard, Reviewer, PM disposition, and terminal replay.",
                    }
                    for item_id in acceptance_item_ids
                ],
            },
        }
    )


def _parent_repair_contract(parent_node_id: str, child_node_id: str = "node-parent-repair-child-001") -> dict:
    return {
        "schema_version": runtime.PARENT_REPAIR_SCOPE_CONTRACT_SCHEMA_VERSION,
        "source_parent_node_id": parent_node_id,
        "inherit_existing_children": True,
        "repair_child_specs": [
            {
                "node_id": child_node_id,
                "title": "Repair parent composition",
                "purpose": "Repair the parent composition blocker with current evidence.",
                "required_evidence": ["current repair child result", "parent replay authorization proof"],
                "acceptance_criteria": ["Current repair child closes the parent composition blocker."],
            }
        ],
    }


def _complete_node_acceptance_plan(ledger: dict) -> None:
    _complete_task_chain(
        ledger,
        _open_packets(ledger, scope="node_acceptance_plan")[0],
        _node_context_body(ledger),
    )


def _latest_pm_decision_gate(ledger: dict) -> dict:
    return list(ledger["pm_decision_gates"].values())[-1]


def _pm_flowguard_acceptance_body(ledger: dict, *, decision: str = "accept", route_plan: dict | None = None) -> str:
    gate = _latest_pm_decision_gate(ledger)
    order = ledger["flowguard_work_orders"][gate["flowguard_order_id"]]
    payload = packet_result_contracts.minimal_valid_shape_for_family("pm_flowguard_acceptance.pm_flowguard_acceptance")
    payload.update(
        {
            "decision": decision,
            "reason": "PM absorbed FlowGuard and chose the next structural path.",
            "flowguard_absorption": "PM accepted the current FlowGuard report, including missing-test and route-depth findings.",
            "accepted_flowguard_result_id": order["proof_result_id"],
        }
    )
    if decision == "redesign_route":
        payload["route_plan"] = route_plan or _route_plan_obj(
            [
                {
                    "node_id": "node-pm-rewrite-001",
                    "title": "PM rewritten node",
                    "responsibility": "worker",
                    "modeled_target": "development_process",
                    "acceptance_criteria": ["PM rewrite opens a fresh executable node."],
                }
            ]
        )
    return json.dumps(payload)


def _complete_pm_flowguard_acceptance(ledger: dict, *, decision: str = "accept", route_plan: dict | None = None) -> str:
    return _complete_open_packet(
        ledger,
        _open_packets(ledger, kind="pm_flowguard_acceptance")[0],
        _pm_flowguard_acceptance_body(ledger, decision=decision, route_plan=route_plan),
    )


def _complete_active_node_packet_loop(ledger: dict) -> str:
    node_id = ledger["execution_frontier"]["active_node_id"]
    _complete_task_chain(
        ledger,
        _open_packets(ledger, scope="node")[0],
        _pass_body("Worker completed the current node task.", node_id=node_id),
    )
    return node_id


class FlowPilotHighStandardControlFlowTests(unittest.TestCase):
    def assertReviewWindowComplete(self, ledger: dict, review_packet_id: str) -> None:
        packet = ledger["packets"][review_packet_id]
        envelope = packet["envelope"]
        body = json.loads(packet["body"])
        review_window = envelope["review_window"]
        self.assertEqual(review_window, body["current_handoff_contract"]["review_window"])
        self.assertEqual(
            review_window_contracts.review_window_pair_failures(
                review_window,
                body["current_handoff_contract"]["review_window"],
            ),
            (),
        )
        self.assertEqual(review_window["schema_version"], review_window_contracts.REVIEW_WINDOW_SCHEMA_VERSION)
        self.assertEqual(review_window["review_window_coverage_status"], "declared")

        row = review_window_contracts.review_flow_row(review_window["review_flow_id"])
        self.assertEqual(review_window["review_result_family_id"], row["review_result_family_id"])
        self.assertEqual(review_window["subject_result_family_id"], row["subject_family_id"])
        self.assertEqual(review_window["subject_lifecycle_stage"], row["subject_lifecycle_stage"])
        self.assertLessEqual(
            set(review_window_contracts.required_window_paths_for_row(row)),
            set(review_window["required_window_paths"]),
        )
        for path in review_window["required_window_paths"]:
            self.assertIn(path, review_window)
        self.assertEqual(review_window["required_material_classes"], list(row["required_material_classes"]))
        self.assertEqual(
            review_window["required_authorized_read_purposes_before_submit"],
            list(row["required_read_purposes"]),
        )
        self.assertLessEqual(
            set(row["required_read_purposes"]),
            set(review_window["authorized_result_read_purposes"]),
        )
        self.assertIn("Reviewer hard blockers return to PM repair work", review_window["pm_repair_return_rule"])

    def test_review_window_validator_rejects_orphan_missing_mismatch_and_prose_only_windows(self) -> None:
        row = review_window_contracts.review_flow_row("node_acceptance_plan_review")
        valid = {
            "schema_version": review_window_contracts.REVIEW_WINDOW_SCHEMA_VERSION,
            "review_flow_id": "node_acceptance_plan_review",
            "review_window_coverage_status": "declared",
            "review_result_family_id": row["review_result_family_id"],
            "subject_packet_id": "packet-node-plan",
            "target_result_id": "result-node-plan",
            "subject_result_family_id": row["subject_family_id"],
            "subject_lifecycle_stage": row["subject_lifecycle_stage"],
            "required_window_paths": list(review_window_contracts.required_window_paths_for_row(row)),
            "required_material_classes": list(row["required_material_classes"]),
            "required_authorized_read_purposes_before_submit": list(row["required_read_purposes"]),
            "authorized_result_read_purposes": list(row["required_read_purposes"]),
            "forbidden_future_stage_classes": list(row["forbidden_future_stage_classes"]),
            "required_current_fields": [],
            "allowed_blocker_classes": [],
            "blocker_next_actions": {},
            "authorized_result_read_ids": [],
            "required_authorized_result_read_ids_before_submit": [],
            "sealed_body_access": "authorized_result_reads_only",
            "review_depth_rule": "Reviewer challenges current-stage material.",
            "forbidden_future_stage_demands": [
                "Do not require future-stage evidence for current-stage review."
            ],
            "pm_repair_return_rule": (
                "Reviewer hard blockers return to PM repair work and then to Reviewer recheck."
            ),
        }

        self.assertEqual(review_window_contracts.review_window_completeness_failures(valid), ())

        orphan = dict(valid)
        orphan["review_flow_id"] = "orphan:review.any_current_subject:task.missing:stage"
        orphan["review_window_coverage_status"] = "orphan_review_flow"
        failures = review_window_contracts.review_window_completeness_failures(orphan)
        self.assertIn("orphan_review_flow", failures)

        missing = dict(valid)
        missing.pop("pm_repair_return_rule")
        self.assertIn(
            "required_window_path_missing:pm_repair_return_rule",
            review_window_contracts.review_window_completeness_failures(missing),
        )

        body_window = dict(valid)
        body_window["subject_lifecycle_stage"] = "wrong_stage"
        self.assertIn(
            "envelope_body_window_mismatch",
            review_window_contracts.review_window_pair_failures(valid, body_window),
        )

        self.assertEqual(
            review_window_contracts.review_window_completeness_failures(None),
            ("review_window_not_structured",),
        )

    def test_runtime_issued_review_packets_have_complete_declared_windows(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        node_plan_packet = _open_packets(ledger, scope="node_acceptance_plan")[0]
        _complete_open_packet(ledger, node_plan_packet, _node_context_body(ledger))
        _complete_open_packet(ledger, _open_packets(ledger, kind="review")[0], _review_pass_body())

        node_packet = _open_packets(ledger, scope="node")[0]
        node_id = ledger["execution_frontier"]["active_node_id"]
        _complete_open_packet(ledger, node_packet, _pass_body("Worker completed node.", node_id=node_id))
        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], _flowguard_pass_body())
        _complete_open_packet(ledger, _open_packets(ledger, kind="review")[0], _review_pass_body())

        review_flow_ids = {
            ledger["packets"][packet_id]["envelope"]["review_window"]["review_flow_id"]
            for packet_id, packet in ledger["packets"].items()
            if packet["envelope"].get("packet_kind") == "review"
        }
        self.assertLessEqual(
            {
                "preplanning_high_standard_contract_review",
                "preplanning_discovery_review",
                "preplanning_skill_standard_review",
                "route_planning_review",
                "node_acceptance_plan_review",
                "worker_node_result_review",
            },
            review_flow_ids,
        )
        for packet_id, packet in ledger["packets"].items():
            if packet["envelope"].get("packet_kind") == "review":
                with self.subTest(packet_id=packet_id):
                    self.assertReviewWindowComplete(ledger, packet_id)

    def test_terminal_review_window_uses_terminal_flow_when_subject_is_not_packet(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_task_chain(
            ledger,
            _open_packets(ledger, scope="planning")[0],
            _route_plan_body(
                [
                    {
                        "node_id": "node-001",
                        "title": "Implement behavior",
                        "acceptance_criteria": ["Behavior implementation accepted."],
                        "high_standard_requirement_ids": ["hsr-001"],
                        "skill_standard_obligation_ids": ["skill-std-001"],
                    }
                ]
            ),
        )
        runtime.ensure_node_acceptance_plan_packet(ledger, "node-001")
        _complete_node_acceptance_plan(ledger)
        _complete_active_node_packet_loop(ledger)
        _complete_open_packet(
            ledger,
            _open_packets(ledger, kind="pm_disposition")[0],
            _pm_disposition_body("PM accepted node after role evidence absorption."),
        )
        boundary = runtime.run_until_wait(ledger)
        packet_id = boundary["next_action"]["subject_id"]

        self.assertReviewWindowComplete(ledger, packet_id)
        review_window = ledger["packets"][packet_id]["envelope"]["review_window"]
        self.assertEqual(review_window["review_flow_id"], "terminal_backward_replay_review")

    def test_stage_evidence_matrix_covers_every_packet_result_family(self) -> None:
        matrix_families = set(packet_stage_evidence_matrix.PACKET_STAGE_EVIDENCE_MATRIX_BY_FAMILY)
        contract_families = {
            str(row["family_id"])
            for row in packet_result_contracts.PACKET_RESULT_CONTRACTS
        }

        self.assertEqual(contract_families, matrix_families)
        required_keys = {
            "family_id",
            "lifecycle_stage",
            "required_evidence_owner",
            "current_required_fields",
            "moved_fields",
            "deleted_fields",
            "allowed_blocker_classes",
            "blocker_next_actions",
            "blocker_repair_packet_contracts",
            "repeat_repair_required_fields",
        }
        for family_id in sorted(contract_families):
            with self.subTest(family_id=family_id):
                row = packet_stage_evidence_matrix.stage_evidence_row_json(family_id)
                self.assertTrue(required_keys.issubset(row))
                self.assertEqual(family_id, row["family_id"])
                self.assertTrue(row["lifecycle_stage"])
                self.assertTrue(row["required_evidence_owner"])
                self.assertIsInstance(row["current_required_fields"], list)
                self.assertIsInstance(row["moved_fields"], list)
                self.assertIsInstance(row["deleted_fields"], list)
                self.assertIsInstance(row["allowed_blocker_classes"], list)
                self.assertIsInstance(row["blocker_next_actions"], dict)
                self.assertIsInstance(row["blocker_repair_packet_contracts"], dict)
                self.assertEqual(set(row["allowed_blocker_classes"]), set(row["blocker_next_actions"]))
                self.assertNotIn(
                    "simulations/run_flowpilot_model_test_alignment_checks.py",
                    json.dumps(row, sort_keys=True),
                )

    def test_generated_packet_handoffs_include_stage_matrix_for_each_package_class(self) -> None:
        ledger = _ledger()

        def assert_handoff(packet_id: str, family_id: str, expected_lifecycle_stage: str) -> None:
            packet = ledger["packets"][packet_id]
            envelope_contract = packet["envelope"]["current_handoff_contract"]
            body_contract = json.loads(packet["body"])["current_handoff_contract"]
            for source in (envelope_contract, body_contract):
                with self.subTest(packet_id=packet_id, family_id=family_id, source=source["contract_id"]):
                    self.assertEqual(family_id, source["contract_family_id"])
                    self.assertEqual(expected_lifecycle_stage, source["stage_evidence_matrix"]["lifecycle_stage"])
                    self.assertNotIn("moved_fields", source["stage_evidence_matrix"])
                    self.assertNotIn("deleted_fields", source["stage_evidence_matrix"])
                    self.assertEqual(
                        expected_lifecycle_stage,
                        source["required_report_contract"]["stage_evidence_matrix"]["lifecycle_stage"],
                    )
                    self.assertNotIn("moved_fields", source["required_report_contract"]["stage_evidence_matrix"])
                    self.assertNotIn("deleted_fields", source["required_report_contract"]["stage_evidence_matrix"])
                    self.assertTrue(source["required_report_contract"]["stage_evidence_matrix"]["current_required_fields"])

        hs_packet = _open_packets(ledger, scope="high_standard_contract")[0]
        assert_handoff(hs_packet, "task.high_standard_contract", "preplanning_contract_definition")
        _complete_open_packet(ledger, hs_packet, _high_standard_contract_body())
        fg_packet = _open_packets(ledger, kind="flowguard_check")[0]
        assert_handoff(fg_packet, "flowguard_check.post_result", "post_result_flowguard_check")
        fg_body = json.loads(ledger["packets"][fg_packet]["body"])
        self.assertEqual("preplanning_contract_definition", fg_body["subject_stage_evidence_matrix"]["lifecycle_stage"])
        _complete_open_packet(ledger, fg_packet, _flowguard_pass_body())
        review_packet = _open_packets(ledger, kind="review")[0]
        assert_handoff(review_packet, "review.any_current_subject", "independent_current_subject_review")
        review_body = json.loads(ledger["packets"][review_packet]["body"])
        self.assertEqual("preplanning_contract_definition", review_body["subject_stage_evidence_matrix"]["lifecycle_stage"])
        _complete_open_packet(ledger, review_packet, _review_pass_body())

        for scope, family_id, stage, body in (
            ("discovery", "task.discovery", "preplanning_material_discovery", _discovery_body()),
            ("skill_standard", "task.skill_standard", "preplanning_skill_standard_contract", _skill_standard_body()),
            (
                "planning",
                "task.planning",
                "route_planning",
                _route_plan_body(
                    [
                        {
                            "node_id": "node-001",
                            "title": "Implement behavior",
                            "acceptance_criteria": ["Behavior implementation accepted."],
                            "high_standard_requirement_ids": ["hsr-001"],
                            "skill_standard_obligation_ids": ["skill-std-001"],
                        }
                    ]
                ),
            ),
        ):
            packet_id = _open_packets(ledger, scope=scope)[0]
            assert_handoff(packet_id, family_id, stage)
            _complete_open_packet(ledger, packet_id, body)
            fg_packet = _open_packets(ledger, kind="flowguard_check")[0]
            assert_handoff(fg_packet, "flowguard_check.post_result", "post_result_flowguard_check")
            fg_body = json.loads(ledger["packets"][fg_packet]["body"])
            self.assertEqual(stage, fg_body["subject_stage_evidence_matrix"]["lifecycle_stage"])
            _complete_open_packet(ledger, fg_packet, _flowguard_pass_body())
            review_packet = _open_packets(ledger, kind="review")[0]
            assert_handoff(review_packet, "review.any_current_subject", "independent_current_subject_review")
            review_body = json.loads(ledger["packets"][review_packet]["body"])
            self.assertEqual(stage, review_body["subject_stage_evidence_matrix"]["lifecycle_stage"])
            _complete_open_packet(ledger, review_packet, _review_pass_body())

        node_plan_packet = _open_packets(ledger, scope="node_acceptance_plan")[0]
        assert_handoff(node_plan_packet, "task.node_acceptance_plan", "node_plan_definition")
        _complete_open_packet(ledger, node_plan_packet, _node_context_body(ledger))
        review_packet = _open_packets(ledger, kind="review")[0]
        assert_handoff(review_packet, "review.any_current_subject", "independent_current_subject_review")
        review_body = json.loads(ledger["packets"][review_packet]["body"])
        self.assertEqual("node_plan_definition", review_body["subject_stage_evidence_matrix"]["lifecycle_stage"])
        self.assertEqual("commit_node_acceptance_plan", review_body["staged_effect"]["effect_kind"])
        _complete_open_packet(ledger, review_packet, _review_pass_body())

        node_packet = _open_packets(ledger, scope="node")[0]
        assert_handoff(node_packet, "task.node", "node_result_execution")
        node_id = ledger["execution_frontier"]["active_node_id"]
        _complete_open_packet(ledger, node_packet, _pass_body("Worker completed the current node task.", node_id=node_id))
        fg_packet = _open_packets(ledger, kind="flowguard_check")[0]
        fg_body = json.loads(ledger["packets"][fg_packet]["body"])
        self.assertEqual("node_result_execution", fg_body["subject_stage_evidence_matrix"]["lifecycle_stage"])
        self.assertIn("current_evidence_refs", fg_body["subject_stage_evidence_matrix"]["current_required_fields"])
        _complete_open_packet(ledger, fg_packet, _flowguard_pass_body())
        review_packet = _open_packets(ledger, kind="review")[0]
        review_body = json.loads(ledger["packets"][review_packet]["body"])
        self.assertEqual("node_result_execution", review_body["subject_stage_evidence_matrix"]["lifecycle_stage"])
        _complete_open_packet(ledger, review_packet, _review_pass_body())
        pm_packet = _open_packets(ledger, kind="pm_disposition")[0]
        assert_handoff(pm_packet, "pm_disposition.node_pm_disposition", "pm_node_result_disposition")
        _complete_open_packet(ledger, pm_packet, _pm_disposition_body("PM accepted node after evidence absorption."))

        self.assertEqual(ledger["route_nodes"][node_id]["status"], "accepted")
        boundary = runtime.run_until_wait(ledger)
        terminal_packet_id = boundary["next_action"]["subject_id"]
        assert_handoff(terminal_packet_id, "review.terminal_backward_replay", "terminal_final_backward_replay")

    def test_high_standard_flowguard_packet_uses_preplanning_stage_matrix(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]

        _complete_open_packet(ledger, packet_id, _high_standard_contract_body())

        flowguard_packet_id = _open_packets(ledger, kind="flowguard_check")[0]
        flowguard_body = json.loads(ledger["packets"][flowguard_packet_id]["body"])
        matrix = flowguard_body["subject_stage_evidence_matrix"]
        policy = flowguard_body["modeled_subject_policy"]
        serialized = json.dumps(flowguard_body, sort_keys=True)

        self.assertEqual("task.high_standard_contract", flowguard_body["subject_result_family_id"])
        self.assertEqual("preplanning_contract_definition", matrix["lifecycle_stage"])
        self.assertEqual(["requirements", "acceptance_item_registry"], matrix["current_required_fields"])
        self.assertNotIn("moved_fields", matrix)
        self.assertNotIn("deleted_fields", matrix)
        self.assertIn("local_artifact", matrix["allowed_blocker_classes"])
        self.assertEqual("pm_repair_decision", matrix["blocker_next_actions"]["local_artifact"])
        self.assertIn("requirements list defines current", json.dumps(policy, sort_keys=True))
        self.assertIn("acceptance_item_registry.items records active acceptance items", json.dumps(policy, sort_keys=True))
        self.assertNotIn("worker_result_artifacts", json.dumps(policy, sort_keys=True))
        self.assertNotIn("simulations/run_flowpilot_model_test_alignment_checks.py", serialized)

    def test_flowguard_minimal_shape_uses_installed_self_check_receipt_not_dev_script(self) -> None:
        payload = packet_result_contracts.minimal_valid_shape_for_family("flowguard_check.post_result")
        serialized = json.dumps(payload, sort_keys=True)

        self.assertIn("FlowPilot installed runtime self-check receipt", serialized)
        self.assertIn("development-repository simulation script", serialized)
        self.assertNotIn("simulations/run_flowpilot_model_test_alignment_checks.py", serialized)

    def test_result_and_terminal_stages_keep_current_evidence_fields(self) -> None:
        node_row = packet_stage_evidence_matrix.stage_evidence_row_json("task.node")
        terminal_row = packet_stage_evidence_matrix.stage_evidence_row_json("review.terminal_backward_replay")

        self.assertIn("current_evidence_refs", node_row["current_required_fields"])
        self.assertEqual(
            [
                "pm_visible_summary",
                "reviewed_by_role",
                "passed",
                "findings",
                "blockers",
                "pm_suggestion_items",
                "final_artifact_refs",
                "acceptance_item_closure",
                "route_segment_replay",
                "waiver_records",
                "final_blockers",
                "contract_self_check",
            ],
            terminal_row["current_required_fields"],
        )
        self.assertIn("terminal_closure", terminal_row["allowed_blocker_classes"])
        self.assertEqual(
            "pm_repair_decision",
            terminal_row["blocker_next_actions"]["terminal_closure"],
        )

    def test_node_acceptance_plan_review_packet_keeps_worker_evidence_future_stage(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        packet_id = _open_packets(ledger, scope="node_acceptance_plan")[0]

        _complete_open_packet(ledger, packet_id, _node_context_body(ledger))

        review_packet_id = _open_packets(ledger, kind="review")[0]
        review_body = json.loads(ledger["packets"][review_packet_id]["body"])
        matrix = review_body["subject_stage_evidence_matrix"]

        self.assertEqual("task.node_acceptance_plan", review_body["subject_result_family_id"])
        self.assertEqual("node_plan_definition", matrix["lifecycle_stage"])
        self.assertNotIn("moved_fields", matrix)
        self.assertNotIn("deleted_fields", matrix)
        self.assertIn("route_decomposition", matrix["allowed_blocker_classes"])
        self.assertEqual("commit_node_acceptance_plan", review_body["staged_effect"]["effect_kind"])

        review_envelope = ledger["packets"][review_packet_id]["envelope"]
        review_window = review_envelope["review_window"]
        body_window = review_body["current_handoff_contract"]["review_window"]
        self.assertEqual(review_window, body_window)
        self.assertEqual(review_window["schema_version"], "black_box_flowpilot.review_window.v1")
        self.assertEqual(review_window["subject_packet_id"], packet_id)
        self.assertEqual(review_window["subject_result_family_id"], "task.node_acceptance_plan")
        self.assertEqual(review_window["subject_lifecycle_stage"], "node_plan_definition")
        self.assertIn("authorized_result_reads_only", review_window["sealed_body_access"])
        self.assertIn("Reviewer hard blockers return to PM repair work", review_window["pm_repair_return_rule"])
        self.assertIn(
            "Do not require Worker/result-stage artifacts for a plan-stage subject unless the subject claims they already exist.",
            review_window["forbidden_future_stage_demands"],
        )

    def test_pm_planning_packet_carries_route_decomposition_quality_gate(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)

        packet_id = _open_packets(ledger, scope="planning")[0]
        packet = ledger["packets"][packet_id]
        body = json.loads(packet["body"])
        criteria = " ".join(packet["envelope"]["acceptance_criteria"]).lower()

        self.assertIn("route_decomposition_review_criteria", body)
        self.assertIn("worker-ready without worker replanning", body["instruction"].lower())
        self.assertIn("small worker-ready leaves", criteria)
        self.assertIn("reviewer may block planning before materialization", criteria)
        self.assertNotIn("why_this_node_exists", body["instruction"])

    def test_pm_planning_packet_surfaces_active_acceptance_owner_coverage_contract(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)

        packet_id = _open_packets(ledger, scope="planning")[0]
        packet = ledger["packets"][packet_id]
        contract = json.loads(packet["body"])["current_handoff_contract"]["required_report_contract"]
        active_ids = ["acc-001", "acc-002"]

        self.assertEqual(contract["required_acceptance_item_ids"], active_ids)
        self.assertEqual(contract["ownership_coverage_rule"]["field_path"], "nodes[].acceptance_item_ids")
        self.assertEqual(contract["ownership_coverage_rule"]["required_ids"], active_ids)
        self.assertEqual(
            contract["allowed_value_options"]["nodes[].acceptance_item_ids[]"],
            active_ids,
        )
        self.assertEqual(contract["field_type_requirements"]["nodes[].acceptance_item_ids"], "array:string")
        self.assertEqual(contract["minimal_valid_shape"]["nodes"][0]["acceptance_item_ids"], active_ids)

    def test_node_acceptance_plan_packet_surfaces_projection_rows_and_allowed_ids(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)

        packet_id = _open_packets(ledger, scope="node_acceptance_plan")[0]
        contract = json.loads(ledger["packets"][packet_id]["body"])["current_handoff_contract"]["required_report_contract"]
        active_ids = ["acc-001", "acc-002"]

        self.assertEqual(contract["required_node_acceptance_item_ids"], active_ids)
        self.assertEqual(
            contract["node_acceptance_projection_rule"]["field_path"],
            "node_context_package.acceptance_item_projection",
        )
        self.assertEqual(contract["node_acceptance_projection_rule"]["required_ids"], active_ids)
        self.assertIn(
            "node_context_package.acceptance_item_projection[].acceptance_item_id",
            contract["required_child_fields"],
        )
        self.assertEqual(
            contract["allowed_value_options"]["node_context_package.acceptance_item_projection[].acceptance_item_id"],
            active_ids,
        )
        projected_ids = [
            row["acceptance_item_id"]
            for row in contract["minimal_valid_shape"]["node_context_package"]["acceptance_item_projection"]
        ]
        self.assertEqual(projected_ids, active_ids)

    def test_reviewer_under_decomposition_block_keeps_planning_unmaterialized_and_replans(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        planning_packet = _open_packets(ledger, scope="planning")[0]

        _complete_open_packet(
            ledger,
            planning_packet,
            _route_plan_body(
                [
                    {
                        "node_id": "node-plan",
                        "title": "Research, implement, and validate the feature",
                        "acceptance_criteria": ["The feature is researched, implemented, and validated."],
                    }
                ]
            ),
        )
        flowguard_packet = _open_packets(ledger, kind="flowguard_check")[0]
        flowguard_body = json.loads(ledger["packets"][flowguard_packet]["body"])
        self.assertTrue(flowguard_body["route_process_focus"]["worker_decision_leakage_check_required"])
        _complete_open_packet(
            ledger,
            flowguard_packet,
            _flowguard_pass_body("FlowGuard reported that Reviewer still must judge route depth."),
        )

        review_packet = _open_packets(ledger, kind="review")[0]
        review_body = json.loads(ledger["packets"][review_packet]["body"])
        self.assertTrue(review_body["route_decomposition_quality_gate"]["reviewer_is_semantic_gate"])
        _complete_open_packet(
            ledger,
            review_packet,
            _review_block_body(
                "Reviewer blocked the broad planning leaf.",
                blocker_class="route_decomposition",
                recommended_resolution=(
                    "PM must split node-plan into a parent module with separate research, implementation, "
                    "and validation leaves before materialization."
                ),
            ),
        )

        self.assertFalse(ledger["route_nodes"])
        self.assertEqual(ledger["packets"][planning_packet]["status"], "review_blocked")
        active = [row for row in ledger["active_blockers"].values() if row["status"] == "active"]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["required_recheck_role"], "reviewer")

        pm_repair_packet = _open_packets(ledger, kind="pm_repair_decision")[0]
        _complete_open_packet(
            ledger,
            pm_repair_packet,
            _pm_repair_body_from_packet(
                ledger,
                pm_repair_packet,
                "PM chose current-scope route replanning.",
                decision="repair_current_scope",
                reason="Reviewer found the planning leaf too broad for one worker packet.",
            ),
        )
        gate = _latest_pm_decision_gate(ledger)
        self.assertEqual(gate["decision"], "repair_current_scope")
        self.assertEqual(gate["status"], "awaiting_flowguard")
        flowguard_packet = _open_packets(ledger, kind="flowguard_check")[0]
        _complete_open_packet(ledger, flowguard_packet, _flowguard_semantic_recheck_body_from_packet(ledger, flowguard_packet))
        _complete_pm_flowguard_acceptance(ledger)
        _complete_open_packet(ledger, _open_packets(ledger, kind="review")[0], _review_pass_body())
        self.assertEqual(gate["status"], "applied")
        repair_packets = [
            packet_id
            for packet_id, packet in ledger["packets"].items()
            if packet.get("repair_blocker_id") == active[0]["blocker_id"]
            and packet["status"] == "open"
            and packet["envelope"].get("route_scope") == "planning"
        ]
        self.assertEqual(len(repair_packets), 1)

        _complete_open_packet(
            ledger,
            repair_packets[0],
            _route_plan_body(
                [
                    {
                        "node_id": "node-parent",
                        "title": "Feature delivery module",
                        "node_kind": "parent",
                        "acceptance_criteria": ["Child leaves close research, implementation, and validation."],
                        "child_node_ids": ["node-research", "node-implement", "node-validate"],
                    },
                    {
                        "node_id": "node-research",
                        "title": "Confirm requirements and constraints",
                        "parent_node_id": "node-parent",
                        "acceptance_criteria": ["Current requirements and constraints are recorded."],
                    },
                    {
                        "node_id": "node-implement",
                        "title": "Apply the scoped implementation change",
                        "parent_node_id": "node-parent",
                        "acceptance_criteria": ["Scoped implementation is complete."],
                    },
                    {
                        "node_id": "node-validate",
                        "title": "Run targeted validation and report evidence",
                        "parent_node_id": "node-parent",
                        "acceptance_criteria": ["Validation evidence is current and accepted."],
                    },
                ]
            ),
        )
        flowguard_packet = _open_packets(ledger, kind="flowguard_check")[0]
        _complete_open_packet(ledger, flowguard_packet, _flowguard_semantic_recheck_body_from_packet(ledger, flowguard_packet))
        _complete_open_packet(ledger, _open_packets(ledger, kind="review")[0], _review_pass_body())

        self.assertNotIn("node-plan", ledger["route_nodes"])
        self.assertEqual(set(ledger["route_nodes"]), {"node-parent", "node-research", "node-implement", "node-validate"})
        self.assertEqual(ledger["route_nodes"]["node-parent"]["child_node_ids"], ["node-research", "node-implement", "node-validate"])

    def test_reviewer_pass_auto_closes_without_closure_flowguard_operator_packet(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]
        _complete_open_packet(ledger, packet_id, _high_standard_contract_body())
        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], _flowguard_pass_body())
        _complete_open_packet(ledger, _open_packets(ledger, kind="review")[0], _review_pass_body())

        self.assertFalse(_open_packets(ledger, kind="validation"))
        self.assertFalse(_open_packets(ledger, kind="closure"))
        evidence = list(ledger["validation_evidence"].values())
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["status"], "passed")
        self.assertEqual(evidence[0]["owner_role"], "system")
        self.assertEqual(evidence[0]["evidence_kind"], "system_review_validation")
        self.assertEqual(evidence[0]["subject_packet_id"], packet_id)
        self.assertTrue(evidence[0]["flowguard_order_ids"])
        closures = list(ledger["system_closures"].values())
        self.assertEqual(len(closures), 1)
        self.assertEqual(closures[0]["subject_packet_id"], packet_id)
        self.assertEqual(closures[0]["validation_evidence_id"], evidence[0]["evidence_id"])
        self.assertEqual((ledger.get("high_standard_contract") or {}).get("status"), "accepted")

    def test_missing_flowguard_report_blocks_before_review_packet(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]
        _complete_open_packet(ledger, packet_id, _high_standard_contract_body())

        review_packet = runtime._ensure_review_packet_for_task_result(ledger, packet_id)

        self.assertEqual(review_packet, "")
        self.assertFalse(_open_packets(ledger, kind="review"))
        self.assertFalse(_open_packets(ledger, kind="closure"))
        self.assertFalse(ledger["system_closures"])
        self.assertFalse([row for row in ledger["validation_evidence"].values() if row["status"] == "failed"])
        active = [row for row in ledger["active_blockers"].values() if row["status"] == "active"]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["gate_kind"], "flowguard_review_handoff")
        self.assertEqual(active[0]["blocker_class"], "missing_matching_flowguard_report")
        self.assertEqual(active[0]["required_recheck_role"], "flowguard_operator")
        self.assertIn("flowguard_missing_matching_report", active[0]["root_cause_loop_key"])
        self.assertTrue(_open_packets(ledger, kind="pm_repair_decision"))

    def test_system_validation_failure_routes_to_pm_repair(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]
        _complete_open_packet(ledger, packet_id, _high_standard_contract_body())
        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], _flowguard_pass_body())
        review_packet = _open_packets(ledger, kind="review")[0]
        review_id = _complete_open_packet(ledger, review_packet, _review_pass_body())

        evidence_id = runtime._record_system_validation_for_packet(
            ledger,
            packet_id,
            source_packet_id=review_packet,
            source_result_id=review_id,
            review_id="different-review-id",
        )
        blocker_id = runtime._record_system_validation_blocker(
            ledger,
            packet_id,
            validation_evidence_id=evidence_id,
            source_packet_id=review_packet,
            source_result_id=review_id,
        )

        evidence = ledger["validation_evidence"][evidence_id]
        blocker = ledger["active_blockers"][blocker_id]
        self.assertEqual(evidence["status"], "failed")
        self.assertEqual(blocker["gate_kind"], "system_validation")
        self.assertEqual(blocker["blocker_class"], "system_validation_failure")
        self.assertEqual(blocker["required_recheck_role"], "system")
        self.assertEqual(ledger["packets"][packet_id]["status"], "system_validation_blocked")
        self.assertTrue(_open_packets(ledger, kind="pm_repair_decision"))

    def test_high_standard_contract_accepts_requirements_without_decision(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]

        _complete_open_packet(ledger, packet_id, _high_standard_contract_body())

        self.assertEqual(ledger["packets"][packet_id]["status"], "result_submitted")
        result = ledger["results"][ledger["packets"][packet_id]["result_ids"][-1]]
        self.assertNotIn("decision", json.loads(result["body"]))
        self.assertTrue(_open_packets(ledger, kind="flowguard_check"))

    def test_high_standard_contract_rejects_hidden_decision_wrapper(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]

        _complete_open_packet(
            ledger,
            packet_id,
            _pass_body(
                "PM accepted the high-standard contract.",
                requirements=[
                    {
                        "requirement_id": "hsr-001",
                        "classification": "hard_current",
                        "summary": "Complete the requested outcome.",
                    }
                ],
            ),
        )

        packet = ledger["packets"][packet_id]
        self.assertEqual(packet["status"], "superseded_after_repair")
        result = ledger["results"][packet["superseded_by_result_id"]]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertEqual(result["contract_family_id"], "task.high_standard_contract")
        self.assertIn("decision", result["forbidden_fields_seen"])
        self.assertIn("pm_visible_summary", result["forbidden_fields_seen"])
        reissue_id = _open_packets(ledger, scope="high_standard_contract")[0]
        reissue_body = json.loads(ledger["packets"][reissue_id]["body"])
        self.assertEqual(reissue_body["required_result_body_fields"], ["requirements", "acceptance_item_registry"])
        self.assertIn("decision", reissue_body["forbidden_fields_seen"])

    def test_high_standard_contract_reissue_names_missing_requirements(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]

        _complete_open_packet(ledger, packet_id, json.dumps({"overall_contract": "complete the work"}))

        packet = ledger["packets"][packet_id]
        self.assertEqual(packet["status"], "superseded_after_repair")
        result = ledger["results"][packet["superseded_by_result_id"]]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        expected_missing = [
            "requirements",
            "acceptance_item_registry",
            "requirements[].requirement_id",
            "requirements[].classification",
            "requirements[].summary",
            "requirements[].source_user_intent",
            "requirements[].closure_rule",
            "acceptance_item_registry.items[]",
            "acceptance_item_registry.items[].acceptance_item_id",
            "acceptance_item_registry.items[].source_type",
            "acceptance_item_registry.items[].summary",
            "acceptance_item_registry.items[].quality_floor",
            "acceptance_item_registry.items[].future_evidence_rule",
            "acceptance_item_registry.items[].status",
        ]
        self.assertEqual(result["missing_required_fields"], expected_missing)
        self.assertEqual(result["forbidden_fields_seen"], ["overall_contract"])
        reissue_id = _open_packets(ledger, scope="high_standard_contract")[0]
        reissue_body = json.loads(ledger["packets"][reissue_id]["body"])
        self.assertEqual(reissue_body["required_result_body_fields"], ["requirements", "acceptance_item_registry"])
        self.assertEqual(reissue_body["missing_required_fields"], expected_missing)
        self.assertEqual(reissue_body["forbidden_fields_seen"], ["overall_contract"])

    def test_high_standard_contract_requires_acceptance_item_registry(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]
        payload = json.loads(_high_standard_contract_body())
        payload.pop("acceptance_item_registry")

        _complete_open_packet(ledger, packet_id, json.dumps(payload))

        packet = ledger["packets"][packet_id]
        result = ledger["results"][packet["superseded_by_result_id"]]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn("acceptance_item_registry", result["missing_required_fields"])

    def test_high_standard_contract_requires_closure_rule_field(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]
        body = json.loads(_high_standard_contract_body())
        del body["requirements"][0]["closure_rule"]

        _complete_open_packet(
            ledger,
            packet_id,
            json.dumps(body),
        )

        packet = ledger["packets"][packet_id]
        self.assertEqual(packet["status"], "superseded_after_repair")
        result = ledger["results"][packet["superseded_by_result_id"]]
        self.assertEqual(result["missing_required_fields"], ["requirements[].closure_rule"])
        self.assertIn("requirements[].closure_rule", result["quarantine_reason"])

    def test_discovery_reissue_names_missing_required_fields(self) -> None:
        ledger = _ledger()
        _complete_task_chain(
            ledger,
            _open_packets(ledger, scope="high_standard_contract")[0],
            _high_standard_contract_body(),
        )
        packet_id = _open_packets(ledger, scope="discovery")[0]

        _complete_open_packet(ledger, packet_id, json.dumps({"decision": "pass", "material_sources": ["startup"]}))

        packet = ledger["packets"][packet_id]
        self.assertEqual(packet["status"], "superseded_after_repair")
        result = ledger["results"][packet["superseded_by_result_id"]]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn("material_sufficiency", result["quarantine_reason"])
        reissue_id = _open_packets(ledger, scope="discovery")[0]
        reissue_body = json.loads(ledger["packets"][reissue_id]["body"])
        self.assertEqual(
            reissue_body["required_result_body_fields"],
            [
                "decision",
                "material_sources",
                "material_sufficiency",
                "candidate_skill_inventory",
            ],
        )

    def test_skill_standard_rejects_default_and_selected_skills_paths(self) -> None:
        ledger = _ledger()
        _complete_task_chain(
            ledger,
            _open_packets(ledger, scope="high_standard_contract")[0],
            _high_standard_contract_body(),
        )
        _complete_task_chain(ledger, _open_packets(ledger, scope="discovery")[0], _discovery_body())
        packet_id = _open_packets(ledger, scope="skill_standard")[0]

        _complete_open_packet(ledger, packet_id, json.dumps({"decision": "pass"}))

        packet = ledger["packets"][packet_id]
        self.assertEqual(packet["status"], "superseded_after_repair")
        result = ledger["results"][packet["superseded_by_result_id"]]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        expected_missing = ["obligations", *_contract_child_fields("task.skill_standard")]
        self.assertEqual(result["missing_required_fields"], expected_missing)
        reissue_id = _open_packets(ledger, scope="skill_standard")[0]
        reissue_body = json.loads(ledger["packets"][reissue_id]["body"])
        self.assertEqual(reissue_body["required_result_body_fields"], ["decision", "obligations"])
        self.assertEqual(reissue_body["missing_required_fields"], expected_missing)

        _complete_open_packet(
            ledger,
            reissue_id,
            json.dumps(
                {
                    "decision": "pass",
                    "selected_skills": [
                        {
                            "skill": "flowguard-development-process-flow",
                            "classification": "required",
                        }
                    ],
                }
            ),
        )

        second_packet = ledger["packets"][reissue_id]
        self.assertEqual(second_packet["status"], "superseded_after_repair")
        second_result = ledger["results"][second_packet["superseded_by_result_id"]]
        self.assertEqual(second_result["missing_required_fields"], expected_missing)
        self.assertEqual(second_result["forbidden_fields_seen"], ["selected_skills"])

    def test_skill_standard_reissue_names_missing_obligation_child_fields(self) -> None:
        ledger = _ledger()
        _complete_task_chain(
            ledger,
            _open_packets(ledger, scope="high_standard_contract")[0],
            _high_standard_contract_body(),
        )
        _complete_task_chain(ledger, _open_packets(ledger, scope="discovery")[0], _discovery_body())
        packet_id = _open_packets(ledger, scope="skill_standard")[0]

        _complete_open_packet(
            ledger,
            packet_id,
            json.dumps(
                {
                    "decision": "pass",
                    "obligations": [
                        {
                            "obligation_id": "skill-std-001",
                            "classification": "required",
                            "role_use": "flowguard_operator",
                            "use_context": "node_validation",
                            "evidence_rule": "FlowGuard operator produces current model/report evidence in its own packet.",
                        }
                    ],
                }
            ),
        )

        packet = ledger["packets"][packet_id]
        result = ledger["results"][packet["superseded_by_result_id"]]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertEqual(result["missing_required_fields"], ["obligations[].skill"])
        reissue_id = _open_packets(ledger, scope="skill_standard")[0]
        reissue_body = json.loads(ledger["packets"][reissue_id]["body"])
        self.assertEqual(reissue_body["missing_required_fields"], ["obligations[].skill"])
        self.assertEqual(reissue_body["contract_family_id"], "task.skill_standard")

    def test_preplanning_gates_run_before_pm_planning(self) -> None:
        ledger = _ledger()

        self.assertEqual(ledger["packets"][_open_packets(ledger, scope="high_standard_contract")[0]]["envelope"]["route_scope"], "high_standard_contract")
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "before high-standard preplanning gates"):
            runtime.materialize_route_from_planning_result(ledger, "missing-result")

        _complete_preplanning(ledger)

        self.assertTrue(runtime.preplanning_gates_accepted(ledger))
        self.assertEqual(ledger["packets"][_open_packets(ledger, scope="planning")[0]]["envelope"]["route_scope"], "planning")

    def test_node_task_requires_accepted_node_acceptance_plan(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)

        node_id = ledger["execution_frontier"]["active_node_id"]
        self.assertEqual(_open_packets(ledger, scope="node_acceptance_plan"), [ledger["packets"][_open_packets(ledger, scope="node_acceptance_plan")[0]]["packet_id"]])
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "requires accepted node acceptance plan"):
            runtime.ensure_next_node_task_packet(ledger)

        _complete_node_acceptance_plan(ledger)

        self.assertFalse(_open_packets(ledger, scope="node_prework_flowguard"))
        self.assertEqual(ledger["packets"][_open_packets(ledger, scope="node")[0]]["envelope"]["route_node_id"], node_id)
        self.assertTrue(ledger["route_nodes"][node_id]["node_acceptance_plan_id"])

    def test_ordinary_node_acceptance_plan_releases_worker_without_prework_flowguard(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        _complete_node_acceptance_plan(ledger)

        node_id = ledger["execution_frontier"]["active_node_id"]
        context_id = ledger["route_nodes"][node_id]["node_context_package_id"]
        self.assertTrue(context_id)
        self.assertTrue(runtime._node_context_package_current(ledger, node_id))
        self.assertFalse(_open_packets(ledger, scope="node_prework_flowguard"))
        node = ledger["route_nodes"][node_id]
        self.assertEqual(_open_packets(ledger, scope="node"), [_open_packets(ledger, scope="node")[0]])
        worker_packet = _open_packets(ledger, scope="node")[0]
        body = json.loads(ledger["packets"][worker_packet]["body"])
        self.assertEqual(ledger["packets"][worker_packet]["envelope"]["node_context_package_id"], context_id)
        self.assertEqual(body["node_context_package_id"], context_id)
        self.assertTrue(node["node_acceptance_plan_id"])
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "no longer a supported current FlowPilot path"):
            runtime.ensure_node_prework_flowguard_packet(ledger, node_id)

    def test_node_acceptance_plan_requires_node_context_package(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)

        packet_id = _open_packets(ledger, scope="node_acceptance_plan")[0]
        result_id = _complete_open_packet(
            ledger,
            packet_id,
            _pass_body(
                "PM submitted a mechanically complete node plan without the required node context.",
                repair_policy="repair_scope_replacement_default",
            ),
        )

        node_id = ledger["execution_frontier"]["active_node_id"]
        self.assertEqual(ledger["results"][result_id]["status"], "mechanical_contract_blocked")
        self.assertEqual(
            ledger["results"][result_id]["missing_required_fields"],
            ["node_context_package"],
        )
        self.assertEqual(ledger["packets"][packet_id]["status"], "superseded_after_repair")
        self.assertTrue(_open_packets(ledger, scope="node_acceptance_plan"))
        self.assertFalse(runtime._node_context_package_current(ledger, node_id))
        self.assertFalse(_open_packets(ledger, scope="node_prework_flowguard"))
        self.assertFalse(_open_packets(ledger, scope="node"))

    def test_node_acceptance_plan_requires_current_contract_projection_fields(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)

        packet_id = _open_packets(ledger, scope="node_acceptance_plan")[0]
        node_id = ledger["execution_frontier"]["active_node_id"]
        result_id = _complete_open_packet(
            ledger,
            packet_id,
            json.dumps(
                {
                    "decision": "pass",
                    "node_context_package": {
                        "node_id": node_id,
                        "purpose": "Old thin node package.",
                        "acceptance_criteria": ["criterion"],
                        "relevant_references": ["reference"],
                        "known_risks": ["risk"],
                    },
                }
            ),
        )

        result = ledger["results"][result_id]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn("node_context_package.acceptance_item_projection", result["missing_required_fields"])

    def test_node_acceptance_plan_reviewer_block_keeps_staged_effect_pending(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        node_id = ledger["execution_frontier"]["active_node_id"]
        packet_id = _open_packets(ledger, scope="node_acceptance_plan")[0]

        result_id = _complete_open_packet(ledger, packet_id, _node_context_body(ledger))
        self.assertEqual(ledger["results"][result_id]["staged_effect"]["effect_kind"], "commit_node_acceptance_plan")
        self.assertEqual(ledger["results"][result_id]["staged_effect"]["status"], "pending")

        _complete_open_packet(
            ledger,
            _open_packets(ledger, kind="review")[0],
            _review_block_body(
                "Reviewer rejected the real node acceptance plan.",
                blocker_class="local_artifact",
                recommended_resolution="Reviewer rejected the real node acceptance plan.",
            ),
        )

        self.assertEqual(ledger["results"][result_id]["staged_effect"]["status"], "pending")
        self.assertEqual(ledger["packets"][packet_id]["status"], "review_blocked")
        self.assertTrue(ledger["packets"][packet_id]["active_blocker_id"])
        self.assertFalse(ledger["node_acceptance_plans"])
        self.assertFalse(ledger["node_context_packages"])
        self.assertFalse(runtime._node_context_package_current(ledger, node_id))
        self.assertFalse(_open_packets(ledger, scope="node_prework_flowguard"))
        self.assertFalse(_open_packets(ledger, scope="node"))
        active = [row for row in ledger["active_blockers"].values() if row["status"] == "active"]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["required_recheck_role"], "reviewer")
        self.assertTrue(_open_packets(ledger, kind="pm_repair_decision"))

    def test_node_context_package_follows_worker_postflowguard_and_reviewer_packets(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        _complete_node_acceptance_plan(ledger)

        node_id = ledger["execution_frontier"]["active_node_id"]
        context_id = ledger["route_nodes"][node_id]["node_context_package_id"]
        self.assertFalse(_open_packets(ledger, scope="node_prework_flowguard"))

        worker_packet = _open_packets(ledger, scope="node")[0]
        worker_body = json.loads(ledger["packets"][worker_packet]["body"])
        self.assertEqual(ledger["packets"][worker_packet]["envelope"]["node_context_package_id"], context_id)
        self.assertEqual(worker_body["node_context_package_id"], context_id)
        self.assertIn("minimum baseline", worker_body["instruction"])

        _complete_open_packet(
            ledger,
            worker_packet,
            _pass_body("Worker completed the current node task.", node_id=node_id),
        )
        post_flowguard = _open_packets(ledger, kind="flowguard_check")[0]
        post_body = json.loads(ledger["packets"][post_flowguard]["body"])
        self.assertEqual(ledger["packets"][post_flowguard]["envelope"]["node_context_package_id"], context_id)
        self.assertEqual(post_body["node_context_package_id"], context_id)

        _complete_open_packet(
            ledger,
            post_flowguard,
            _flowguard_pass_body("Post-result FlowGuard accepted the worker result."),
        )
        review_packet = _open_packets(ledger, kind="review")[0]
        review_body = json.loads(ledger["packets"][review_packet]["body"])
        self.assertEqual(ledger["packets"][review_packet]["envelope"]["node_context_package_id"], context_id)
        self.assertEqual(review_body["node_context_package_id"], context_id)
        self.assertIn("as the review boundary", review_body["instruction"])

    def test_worker_result_review_packet_marks_result_stage_boundary(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        _complete_node_acceptance_plan(ledger)

        node_id = ledger["execution_frontier"]["active_node_id"]
        worker_packet = _open_packets(ledger, scope="node")[0]
        worker_result_id = _complete_open_packet(
            ledger,
            worker_packet,
            _pass_body("Worker completed the current node task.", node_id=node_id),
        )
        post_flowguard = _open_packets(ledger, kind="flowguard_check")[0]
        flowguard_result_id = _complete_open_packet(
            ledger,
            post_flowguard,
            _flowguard_pass_body("Post-result FlowGuard accepted the worker result."),
        )

        review_packet = _open_packets(ledger, kind="review")[0]
        review = ledger["packets"][review_packet]
        review_body = json.loads(review["body"])
        self.assertNotIn("plan-stage review", review_body["instruction"])
        self.assertIn("When matching FlowGuard evidence is required", review_body["instruction"])
        self.assertTrue(review_body["flowguard_evidence_manifest"]["matching_flowguard_result_reads_required"])
        self.assertEqual(review_body["target_result_id"], worker_result_id)
        self.assertEqual(
            review_body["flowguard_evidence_manifest"]["entries"][0]["flowguard_result_id"],
            flowguard_result_id,
        )
        read_purposes = {entry["purpose"] for entry in review["envelope"]["authorized_result_reads"]}
        self.assertIn("subject_result_for_review", read_purposes)
        self.assertIn("matching_flowguard_result_for_review", read_purposes)

    def test_node_acceptance_redesign_route_flowguard_block_prevents_route_mutation(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        node_id = ledger["execution_frontier"]["active_node_id"]
        old_route_version = ledger["active_route_version"]

        _complete_open_packet(
            ledger,
            _open_packets(ledger, scope="node_acceptance_plan")[0],
            json.dumps(
                {
                    "decision": "redesign_route",
                    "reason": "PM found the node too coarse and replaced it with smaller work.",
                    "route_plan": _route_plan_obj(
                        [
                            {
                                "node_id": "node-redesign-blocked-001",
                                "title": "Blocked redesign node",
                                "responsibility": "worker",
                                "modeled_target": "development_process",
                                "acceptance_criteria": ["FlowGuard should block this structural change."],
                            }
                        ]
                    ),
                }
            ),
        )

        gate = _latest_pm_decision_gate(ledger)
        self.assertEqual(gate["status"], "awaiting_flowguard")
        self.assertEqual(gate["staged_effect"]["effect_kind"], "commit_route_redesign")
        flowguard_packet = _open_packets(ledger, kind="flowguard_check")[0]
        body = json.loads(ledger["packets"][flowguard_packet]["body"])
        self.assertEqual(body["structural_route_simulation_focus"]["pm_absorption_required_after_pass"], True)
        matrix = body["subject_stage_evidence_matrix"]
        self.assertEqual(matrix["family_id"], "task.node_acceptance_plan")
        self.assertEqual(matrix["lifecycle_stage"], "node_plan_definition")
        self.assertNotIn("moved_fields", matrix)
        self.assertNotIn("deleted_fields", matrix)
        targets = " ".join(body["modeled_subject_policy"]["required_simulation_targets"])
        self.assertIn("node_context_package carries the node's five-field starting context", targets)
        self.assertIn("current staged route or node effect can commit", targets)

        _complete_open_packet(
            ledger,
            flowguard_packet,
            _flowguard_block_body(
                "FlowGuard blocked the proposed route redesign.",
                blocker_class="flowguard_failure",
                recommended_resolution="PM must rewrite the proposed route before mutation.",
            ),
        )

        self.assertEqual(gate["status"], "flowguard_blocked")
        self.assertEqual(ledger["active_route_version"], old_route_version)
        self.assertNotEqual(ledger["route_nodes"][node_id]["status"], "superseded")
        self.assertFalse(_open_packets(ledger, kind="pm_flowguard_acceptance"))
        self.assertFalse(_open_packets(ledger, kind="review"))
        self.assertFalse(_open_packets(ledger, scope="node"))

    def test_node_acceptance_redesign_route_requires_pm_absorption_before_reviewer(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        node_id = ledger["execution_frontier"]["active_node_id"]
        old_route_version = ledger["active_route_version"]

        _complete_open_packet(
            ledger,
            _open_packets(ledger, scope="node_acceptance_plan")[0],
            json.dumps(
                {
                    "decision": "redesign_route",
                    "reason": "PM split the active node into a fresh route slice.",
                    "route_plan": _route_plan_obj(
                        [
                            {
                                "node_id": "node-redesign-accepted-001",
                                "title": "Accepted redesign node",
                                "responsibility": "worker",
                                "modeled_target": "development_process",
                                "acceptance_criteria": ["Redesigned node is reviewed before execution."],
                            }
                        ]
                    ),
                }
            ),
        )

        gate = _latest_pm_decision_gate(ledger)
        self.assertEqual(gate["status"], "awaiting_flowguard")
        self.assertTrue(_open_packets(ledger, kind="flowguard_check"))
        self.assertFalse(_open_packets(ledger, kind="review"))

        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], _flowguard_pass_body("FlowGuard passed the route redesign."))
        self.assertEqual(gate["status"], "awaiting_pm_flowguard_acceptance")
        self.assertTrue(_open_packets(ledger, kind="pm_flowguard_acceptance"))
        self.assertFalse(_open_packets(ledger, kind="review"))

        pm_acceptance_packet = _open_packets(ledger, kind="pm_flowguard_acceptance")[0]
        pm_acceptance_body = json.loads(ledger["packets"][pm_acceptance_packet]["body"])
        self.assertEqual(pm_acceptance_body["allowed_decisions"], ["accept", "redesign_route", "block", "stop_for_user"])
        self.assertIn("There is no optional or uncertain FlowGuard branch", pm_acceptance_body["instruction"])
        _complete_pm_flowguard_acceptance(ledger)

        self.assertEqual(gate["status"], "awaiting_review")
        review_packet = _open_packets(ledger, kind="review")[0]
        review_body = json.loads(ledger["packets"][review_packet]["body"])
        self.assertTrue(review_body["structural_pm_flowguard_acceptance_gate"]["pm_flowguard_acceptance_required"])
        _complete_open_packet(ledger, review_packet, _review_pass_body("Reviewer accepted the PM-absorbed redesign."))

        self.assertEqual(gate["status"], "applied")
        self.assertEqual(ledger["active_route_version"], old_route_version + 1)
        self.assertEqual(ledger["route_nodes"][node_id]["status"], "superseded")
        self.assertEqual(ledger["execution_frontier"]["active_node_id"], "redesign-module-001")
        self.assertIn("node-redesign-accepted-001", ledger["route_nodes"]["redesign-module-001"]["child_node_ids"])
        self.assertTrue(_open_packets(ledger, scope="node_acceptance_plan"))

    def test_pm_flowguard_acceptance_rewrite_restarts_flowguard_cycle(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        old_route_version = ledger["active_route_version"]

        _complete_open_packet(
            ledger,
            _open_packets(ledger, scope="node_acceptance_plan")[0],
            json.dumps(
                {
                    "decision": "redesign_route",
                    "reason": "PM first proposed an overly thin split.",
                    "route_plan": _route_plan_obj(
                        [
                            {
                                "node_id": "node-first-redesign-001",
                                "title": "First redesign node",
                                "responsibility": "worker",
                                "modeled_target": "development_process",
                                "acceptance_criteria": ["First redesign is replaced after FlowGuard."],
                            }
                        ]
                    ),
                }
            ),
        )
        first_gate = _latest_pm_decision_gate(ledger)
        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], _flowguard_pass_body("FlowGuard passed with PM suggestions."))

        _complete_pm_flowguard_acceptance(
            ledger,
            decision="redesign_route",
            route_plan=_route_plan_obj(
                [
                    {
                        "node_id": "node-pm-rewrite-001",
                        "title": "PM rewritten route node",
                        "responsibility": "worker",
                        "modeled_target": "development_process",
                        "acceptance_criteria": ["PM rewrite must run a fresh FlowGuard cycle."],
                    }
                ]
            ),
        )

        self.assertEqual(first_gate["status"], "replaced_by_pm_flowguard_acceptance")
        second_gate = _latest_pm_decision_gate(ledger)
        self.assertNotEqual(second_gate["gate_id"], first_gate["gate_id"])
        self.assertEqual(second_gate["status"], "awaiting_flowguard")
        self.assertEqual(ledger["active_route_version"], old_route_version)
        self.assertTrue(_open_packets(ledger, kind="flowguard_check"))
        self.assertFalse(_open_packets(ledger, kind="review"))

    def test_pm_flowguard_acceptance_rejects_optional_decisions(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)

        _complete_open_packet(
            ledger,
            _open_packets(ledger, scope="node_acceptance_plan")[0],
            json.dumps(
                {
                    "decision": "redesign_route",
                    "reason": "PM proposed a structural route change.",
                    "route_plan": _route_plan_obj(
                        [
                            {
                                "node_id": "node-redesign-optional-001",
                                "title": "Optional branch should fail",
                                "responsibility": "worker",
                                "modeled_target": "development_process",
                                "acceptance_criteria": ["Optional FlowGuard is not allowed."],
                            }
                        ]
                    ),
                }
            ),
        )
        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], _flowguard_pass_body("FlowGuard passed the redesign."))
        packet_id = _open_packets(ledger, kind="pm_flowguard_acceptance")[0]
        gate = _latest_pm_decision_gate(ledger)
        order = ledger["flowguard_work_orders"][gate["flowguard_order_id"]]

        result_id = _complete_open_packet(
            ledger,
            packet_id,
            json.dumps(
                {
                    "decision": "optional_flowguard",
                    "reason": "PM tried to make FlowGuard optional.",
                    "flowguard_absorption": "PM did not make a current binary choice.",
                    "accepted_flowguard_result_id": order["proof_result_id"],
                }
            ),
        )

        self.assertEqual(ledger["results"][result_id]["status"], "mechanical_contract_blocked")
        self.assertEqual(gate["status"], "awaiting_pm_flowguard_acceptance")
        self.assertFalse(_open_packets(ledger, kind="review"))
        self.assertFalse(_open_packets(ledger, scope="node"))

    def test_pm_disposition_repair_current_scope_creates_replacement_node(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        _complete_node_acceptance_plan(ledger)
        node_id = _complete_active_node_packet_loop(ledger)
        _complete_open_packet(
            ledger,
            _open_packets(ledger, kind="pm_disposition")[0],
            _pm_disposition_body(
                "PM chose current-node repair.",
                decision="repair_current_scope",
                reason="needs deeper evidence",
            ),
        )

        self.assertEqual(ledger["active_route_version"], 2)
        replacement_id = ledger["execution_frontier"]["active_node_id"]
        self.assertNotEqual(replacement_id, node_id)
        self.assertEqual(ledger["route_nodes"][node_id]["status"], "superseded")
        self.assertTrue(_open_packets(ledger, scope="node_acceptance_plan"))
        self.assertFalse(_open_packets(ledger, scope="node"))
        _complete_node_acceptance_plan(ledger)
        self.assertEqual(ledger["packets"][_open_packets(ledger, scope="node")[0]]["envelope"]["route_node_id"], replacement_id)

    def test_pm_disposition_summary_is_not_reason_fallback(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        _complete_node_acceptance_plan(ledger)
        _complete_active_node_packet_loop(ledger)
        packet_id = _open_packets(ledger, kind="pm_disposition")[0]

        result_id = _complete_open_packet(
            ledger,
            packet_id,
            json.dumps(
                {
                    "decision": "accept",
                    "summary": "legacy PM disposition summary must not be accepted as reason",
                }
            ),
        )

        self.assertEqual(ledger["results"][result_id]["status"], "mechanical_contract_blocked")
        self.assertEqual(ledger["packets"][packet_id]["status"], "superseded_after_repair")
        self.assertFalse(ledger["pm_dispositions"])
        self.assertIn("reason", ledger["results"][result_id]["missing_required_fields"])
        self.assertIn("acceptance_item_disposition", ledger["results"][result_id]["missing_required_fields"])
        self.assertEqual(ledger["results"][result_id]["forbidden_fields_seen"], ["summary"])

        fresh_packet_id = runtime._ensure_pm_disposition_packet_for_node(
            ledger,
            ledger["execution_frontier"]["active_node_id"],
            ledger["packets"][packet_id]["envelope"]["subject_id"],
        )

        self.assertNotEqual(fresh_packet_id, packet_id)
        self.assertEqual(ledger["packets"][packet_id]["status"], "superseded_after_repair")
        self.assertEqual(ledger["packets"][fresh_packet_id]["envelope"]["packet_kind"], "pm_disposition")
        fresh_body = json.loads(ledger["packets"][fresh_packet_id]["body"])
        self.assertIn("reason", fresh_body["missing_required_fields"])
        self.assertIn("acceptance_item_disposition", fresh_body["missing_required_fields"])
        self.assertEqual(fresh_body["forbidden_fields_seen"], ["summary"])

    def test_pm_disposition_accept_requires_acceptance_item_disposition_table(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        _complete_node_acceptance_plan(ledger)
        _complete_active_node_packet_loop(ledger)
        packet_id = _open_packets(ledger, kind="pm_disposition")[0]

        result_id = _complete_open_packet(
            ledger,
            packet_id,
            json.dumps({"decision": "accept", "reason": "thin PM accept"}),
        )

        result = ledger["results"][result_id]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn("acceptance_item_disposition", result["missing_required_fields"])

    def test_pm_repair_parent_scope_requires_structured_repair_child_specs(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_task_chain(
            ledger,
            _open_packets(ledger, scope="planning")[0],
            _route_plan_body(
                [
                    {
                        "node_id": "node-parent",
                        "title": "Parent module",
                        "node_kind": "parent",
                        "responsibility": "worker",
                        "modeled_target": "development_process",
                        "acceptance_criteria": ["Parent module composes."],
                        "child_node_ids": ["node-child"],
                    },
                    {
                        "node_id": "node-child",
                        "title": "Child module",
                        "parent_node_id": "node-parent",
                        "responsibility": "worker",
                        "modeled_target": "development_process",
                        "acceptance_criteria": ["Child module works."],
                    },
                ]
            ),
        )
        blocker_id = "blocker-parent-scope"
        decision_id = "pm_repair_decision-parent-scope"
        ledger["active_blockers"][blocker_id] = {
            "blocker_id": blocker_id,
            "status": "active",
            "outcome_id": "outcome-parent-scope",
            "packet_id": "",
            "packet_kind": "task",
            "subject_packet_id": "",
            "repair_target_packet_id": "",
            "target_result_id": "",
            "result_id": "",
            "owner_role": "worker",
            "required_recheck_role": "reviewer",
            "gate_kind": "task",
            "blocker_class": "composition",
            "recommended_resolution": "bubble to parent",
            "route_version": ledger["active_route_version"],
            "route_node_id": "node-child",
            "route_scope": "node",
            "repair_generation": 0,
            "stale_evidence_ids": [],
            "created_at": runtime.now_iso(),
            "pm_repair_packet_id": "",
            "pm_repair_decision_id": decision_id,
            "cleared_by_outcome_id": "",
        }
        ledger["pm_repair_decisions"][decision_id] = {
            "decision_id": decision_id,
            "blocker_id": blocker_id,
            "packet_id": "packet-decision",
            "result_id": "result-decision",
            "decision": "repair_parent_scope",
            "reason": "Parent composition is invalid.",
            "created_at": runtime.now_iso(),
        }

        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "repair_parent_scope requires repair_parent_scope_contract"):
            runtime._apply_pm_repair_decision(ledger, blocker_id, decision_id)

    def test_pm_repair_parent_scope_replaces_parent_and_descendants_with_active_repair_children(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_task_chain(
            ledger,
            _open_packets(ledger, scope="planning")[0],
            _route_plan_body(
                [
                    {
                        "node_id": "node-parent",
                        "title": "Parent module",
                        "node_kind": "parent",
                        "responsibility": "worker",
                        "modeled_target": "development_process",
                        "acceptance_criteria": ["Parent module composes."],
                        "child_node_ids": ["node-child"],
                    },
                    {
                        "node_id": "node-child",
                        "title": "Child module",
                        "parent_node_id": "node-parent",
                        "responsibility": "worker",
                        "modeled_target": "development_process",
                        "acceptance_criteria": ["Child module works."],
                    },
                ]
            ),
        )
        blocker_id = "blocker-parent-scope"
        decision_id = "pm_repair_decision-parent-scope"
        ledger["active_blockers"][blocker_id] = {
            "blocker_id": blocker_id,
            "status": "active",
            "outcome_id": "outcome-parent-scope",
            "packet_id": "",
            "packet_kind": "task",
            "subject_packet_id": "",
            "repair_target_packet_id": "",
            "target_result_id": "",
            "result_id": "",
            "owner_role": "worker",
            "required_recheck_role": "reviewer",
            "gate_kind": "task",
            "blocker_class": "composition",
            "recommended_resolution": "bubble to parent",
            "route_version": ledger["active_route_version"],
            "route_node_id": "node-child",
            "route_scope": "node",
            "repair_generation": 0,
            "stale_evidence_ids": [],
            "created_at": runtime.now_iso(),
            "pm_repair_packet_id": "",
            "pm_repair_decision_id": decision_id,
            "cleared_by_outcome_id": "",
        }
        ledger["pm_repair_decisions"][decision_id] = {
            "decision_id": decision_id,
            "blocker_id": blocker_id,
            "packet_id": "packet-decision",
            "result_id": "result-decision",
            "decision": "repair_parent_scope",
            "reason": "Parent composition is invalid.",
            "repair_parent_scope_contract": _parent_repair_contract("node-parent"),
            "created_at": runtime.now_iso(),
        }

        runtime._apply_pm_repair_decision(ledger, blocker_id, decision_id)

        replacement_id = ledger["execution_frontier"]["active_node_id"]
        fresh_packet_id = ledger["repair_transactions"][decision_id]["fresh_packet_id"]
        self.assertEqual(ledger["route_nodes"]["node-parent"]["status"], "superseded")
        self.assertEqual(ledger["route_nodes"]["node-child"]["status"], "superseded")
        self.assertEqual(ledger["route_nodes"]["node-parent"]["superseded_by"], replacement_id)
        self.assertEqual(ledger["route_nodes"]["node-child"]["superseded_by"], replacement_id)
        self.assertEqual(ledger["route_nodes"][replacement_id]["child_node_ids"], ["node-parent-repair-child-001"])
        self.assertEqual(ledger["route_nodes"][replacement_id]["inherited_child_node_ids"], ["node-child"])
        self.assertEqual(ledger["route_nodes"]["node-parent-repair-child-001"]["parent_node_id"], replacement_id)
        self.assertEqual(ledger["route_nodes"]["node-parent-repair-child-001"]["node_kind"], "repair")
        self.assertIn("node-parent-repair-child-001", ledger["routes"][str(ledger["active_route_version"])]["node_order"])
        self.assertEqual(ledger["packets"][fresh_packet_id]["status"], "open")
        self.assertEqual(ledger["packets"][fresh_packet_id]["repair_blocker_id"], blocker_id)
        self.assertEqual(ledger["active_blockers"][blocker_id]["status"], "repair_packet_open")

    def test_parent_repair_replay_rejects_inherited_history_without_current_child_result(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        ledger["route_nodes"]["parent-repair"] = {
            "node_id": "parent-repair",
            "title": "Repair parent",
            "node_kind": "parent",
            "status": "awaiting_parent_backward_replay",
            "child_node_ids": [],
            "inherited_child_node_ids": ["old-child"],
            "inherited_accepted_result_ids": ["old-result"],
            "parent_repair_scope_contract_id": "parent-repair-contract-001",
        }

        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "active repair child_node_ids"):
            runtime.ensure_parent_backward_replay_packet(ledger, "parent-repair")

    def test_parent_repair_node_plan_rejects_prose_only_child_routing(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        ledger["route_nodes"]["parent-repair"] = {
            "node_id": "parent-repair",
            "title": "Repair parent",
            "node_kind": "parent",
            "status": "running",
            "child_node_ids": [],
            "inherited_child_node_ids": ["old-child"],
            "inherited_accepted_result_ids": ["old-result"],
            "parent_repair_scope_contract_id": "parent-repair-contract-001",
            "acceptance_criteria": ["Repair parent composition."],
            "acceptance_item_ids": [],
        }
        ledger["execution_frontier"] = {
            "active_route_version": ledger["active_route_version"],
            "active_node_id": "parent-repair",
            "completed_nodes": [],
            "status": "node_execution",
            "pending_route_mutation": None,
            "blocked_reason": "",
            "updated_at": runtime.now_iso(),
        }
        packet_id = runtime.ensure_node_acceptance_plan_packet(ledger, "parent-repair")
        payload = json.loads(_node_context_body(ledger))

        result_id = _complete_open_packet(ledger, packet_id, json.dumps(payload))
        result = ledger["results"][result_id]

        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn("route_node.child_node_ids", result["missing_required_fields"])
        self.assertIn("repair_parent_scope_contract.repair_child_specs", result["missing_required_fields"])

    def test_reviewer_block_routes_to_pm_repair_and_requires_recheck(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]
        _complete_open_packet(
            ledger,
            packet_id,
            _high_standard_contract_body(),
        )
        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], _flowguard_pass_body())

        review_packet = _open_packets(ledger, kind="review")[0]
        _complete_open_packet(
            ledger,
            review_packet,
            _review_block_body(
                "Reviewer rejected the current high-standard contract.",
                blocker_class="local_artifact",
                recommended_resolution="PM must reissue a sharper high-standard contract.",
            ),
        )

        self.assertEqual(ledger["packets"][packet_id]["status"], "review_blocked")
        self.assertTrue(ledger["packets"][packet_id]["active_blocker_id"])
        self.assertFalse(_open_packets(ledger, kind="validation"))
        active = [row for row in ledger["active_blockers"].values() if row["status"] == "active"]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["required_recheck_role"], "reviewer")
        pm_repair_packet = _open_packets(ledger, kind="pm_repair_decision")[0]

        _complete_open_packet(
            ledger,
            pm_repair_packet,
            _pm_repair_body_from_packet(
                ledger,
                pm_repair_packet,
                "PM chose local current-scope repair.",
                decision="repair_current_scope",
                reason="local fix",
            ),
        )

        gate = _latest_pm_decision_gate(ledger)
        self.assertEqual(gate["decision"], "repair_current_scope")
        self.assertEqual(gate["status"], "awaiting_flowguard")
        flowguard_packet = _open_packets(ledger, kind="flowguard_check")[0]
        _complete_open_packet(ledger, flowguard_packet, _flowguard_semantic_recheck_body_from_packet(ledger, flowguard_packet))
        _complete_pm_flowguard_acceptance(ledger)
        _complete_open_packet(ledger, _open_packets(ledger, kind="review")[0], _review_pass_body())
        self.assertEqual(gate["status"], "applied")

        repair_packets = [
            packet_id
            for packet_id, packet in ledger["packets"].items()
            if packet.get("repair_blocker_id") == active[0]["blocker_id"]
            and packet["status"] == "open"
            and packet.get("envelope", {}).get("packet_kind") == "task"
        ]
        self.assertEqual(len(repair_packets), 1)

        _complete_open_packet(ledger, repair_packets[0], _high_standard_contract_body())
        flowguard_packet = _open_packets(ledger, kind="flowguard_check")[0]
        _complete_open_packet(ledger, flowguard_packet, _flowguard_semantic_recheck_body_from_packet(ledger, flowguard_packet))
        _complete_open_packet(ledger, _open_packets(ledger, kind="review")[0], _review_pass_body())

        self.assertEqual(ledger["active_blockers"][active[0]["blocker_id"]]["status"], "cleared")
        self.assertFalse(_open_packets(ledger, kind="validation"))
        self.assertFalse(_open_packets(ledger, kind="closure"))
        self.assertTrue(ledger["system_closures"])

    def test_validator_and_closure_flowguard_operator_are_not_runtime_roles(self) -> None:
        ledger = _ledger()
        for responsibility in ("validator", "closure_flowguard_operator"):
            with self.subTest(responsibility=responsibility):
                with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "unknown responsibility"):
                    runtime.issue_task_packet(
                        ledger,
                        responsibility,
                        "Forbidden old role",
                        "SEALED_OLD_ROLE_BODY",
                    )

    def test_validation_and_closure_packet_kinds_are_rejected(self) -> None:
        ledger = _ledger()
        for packet_kind in ("validation", "closure"):
            with self.subTest(packet_kind=packet_kind):
                with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "unknown packet kind"):
                    runtime.issue_task_packet(
                        ledger,
                        "worker",
                        "Forbidden old packet kind",
                        "SEALED_OLD_PACKET_KIND_BODY",
                        packet_kind=packet_kind,
                    )

    def test_pm_repair_current_scope_for_packet_scope_is_gated_before_application(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        _complete_node_acceptance_plan(ledger)
        packet_id = _open_packets(ledger, scope="node")[0]
        _complete_open_packet(
            ledger,
            packet_id,
            _block_body(
                "Worker blocked on the current node.",
                blocker_class="local_artifact",
                recommended_resolution="sender fix",
            ),
        )
        blocker = [row for row in ledger["active_blockers"].values() if row["status"] == "active"][0]

        pm_repair_packet = _open_packets(ledger, kind="pm_repair_decision")[0]
        _complete_open_packet(
            ledger,
            pm_repair_packet,
            _pm_repair_body_from_packet(
                ledger,
                pm_repair_packet,
                "PM chose plain current-scope repair.",
                decision="repair_current_scope",
                reason="plain repair",
            ),
        )

        self.assertEqual(ledger["active_blockers"][blocker["blocker_id"]]["status"], "awaiting_pm_decision_gate")
        gate = next(iter(ledger["pm_decision_gates"].values()))
        self.assertEqual(gate["gate_kind"], "pm_repair_decision")
        self.assertEqual(gate["decision"], "repair_current_scope")
        self.assertEqual(gate["status"], "awaiting_flowguard")
        self.assertTrue(_open_packets(ledger, kind="flowguard_check"))
        self.assertFalse(_open_packets(ledger, kind="review"))
        self.assertFalse(
            [
                packet_id
                for packet_id, packet in ledger["packets"].items()
                if packet.get("repair_blocker_id") == blocker["blocker_id"]
                and packet["status"] == "open"
                and packet.get("envelope", {}).get("packet_kind") == "task"
            ]
        )

        flowguard_packet = _open_packets(ledger, kind="flowguard_check")[0]
        _complete_open_packet(ledger, flowguard_packet, _flowguard_semantic_recheck_body_from_packet(ledger, flowguard_packet))
        self.assertEqual(gate["status"], "awaiting_pm_flowguard_acceptance")
        self.assertTrue(_open_packets(ledger, kind="pm_flowguard_acceptance"))
        self.assertFalse(_open_packets(ledger, kind="review"))
        _complete_pm_flowguard_acceptance(ledger)
        self.assertEqual(gate["status"], "awaiting_review")
        _complete_open_packet(ledger, _open_packets(ledger, kind="review")[0], _review_pass_body())

        self.assertEqual(gate["status"], "applied")
        self.assertEqual(ledger["active_blockers"][blocker["blocker_id"]]["status"], "repair_packet_open")
        repair_packets = [
            packet_id
            for packet_id, packet in ledger["packets"].items()
            if packet.get("repair_blocker_id") == blocker["blocker_id"]
            and packet["status"] == "open"
            and packet.get("envelope", {}).get("packet_kind") == "task"
        ]
        self.assertEqual(len(repair_packets), 1)

    def test_pm_redesign_route_repair_is_gated_before_application(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        _complete_node_acceptance_plan(ledger)
        node_id = ledger["execution_frontier"]["active_node_id"]
        node_packet = _open_packets(ledger, scope="node")[0]
        _complete_open_packet(
            ledger,
            node_packet,
            _block_body(
                "Worker blocked because this node needs a route change.",
                blocker_class="local_artifact",
                recommended_resolution="route change",
            ),
        )
        blocker = [row for row in ledger["active_blockers"].values() if row["status"] == "active"][0]
        old_route_version = ledger["active_route_version"]

        pm_repair_packet = _open_packets(ledger, kind="pm_repair_decision")[0]
        _complete_open_packet(
            ledger,
            pm_repair_packet,
            _pm_repair_body_from_packet(
                ledger,
                pm_repair_packet,
                "PM chose route redesign for the current blocker.",
                decision="redesign_route",
                reason="current route plan is wrong",
                route_plan=_route_plan_obj(
                    [
                        {
                            "node_id": "node-redesign-001",
                            "title": "Redesigned repair node",
                            "responsibility": "worker",
                            "modeled_target": "development_process",
                            "acceptance_criteria": ["Redesigned route opens fresh repair work."],
                        }
                    ]
                ),
            ),
        )

        self.assertEqual(ledger["active_route_version"], old_route_version)
        self.assertEqual(ledger["active_blockers"][blocker["blocker_id"]]["status"], "awaiting_pm_decision_gate")
        gate = next(iter(ledger["pm_decision_gates"].values()))
        self.assertEqual(gate["status"], "awaiting_flowguard")
        self.assertTrue(_open_packets(ledger, kind="flowguard_check"))

        flowguard_packet = _open_packets(ledger, kind="flowguard_check")[0]
        _complete_open_packet(ledger, flowguard_packet, _flowguard_semantic_recheck_body_from_packet(ledger, flowguard_packet))
        self.assertEqual(gate["status"], "awaiting_pm_flowguard_acceptance")
        self.assertTrue(_open_packets(ledger, kind="pm_flowguard_acceptance"))
        self.assertFalse(_open_packets(ledger, kind="review"))
        _complete_pm_flowguard_acceptance(ledger)
        self.assertEqual(gate["status"], "awaiting_review")
        _complete_open_packet(ledger, _open_packets(ledger, kind="review")[0], _review_pass_body())
        self.assertEqual(gate["status"], "applied")
        self.assertEqual(ledger["active_route_version"], old_route_version + 1)
        self.assertEqual(ledger["route_nodes"][node_id]["status"], "superseded")
        self.assertEqual(ledger["active_blockers"][blocker["blocker_id"]]["status"], "repair_packet_open")
        self.assertFalse(_open_packets(ledger, kind="closure"))

    def test_pm_redesign_route_repair_reviewer_block_keeps_staged_effect_pending(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        _complete_node_acceptance_plan(ledger)
        node_id = ledger["execution_frontier"]["active_node_id"]
        node_packet = _open_packets(ledger, scope="node")[0]
        _complete_open_packet(
            ledger,
            node_packet,
            _block_body(
                "Worker blocked because this node needs a route change.",
                blocker_class="local_artifact",
                recommended_resolution="route change",
            ),
        )
        blocker = [row for row in ledger["active_blockers"].values() if row["status"] == "active"][0]
        old_route_version = ledger["active_route_version"]

        pm_repair_packet = _open_packets(ledger, kind="pm_repair_decision")[0]
        _complete_open_packet(
            ledger,
            pm_repair_packet,
            _pm_repair_body_from_packet(
                ledger,
                pm_repair_packet,
                "PM chose route redesign for the current blocker.",
                decision="redesign_route",
                reason="current route plan is wrong",
                route_plan=_route_plan_obj(
                    [
                        {
                            "node_id": "node-redesign-001",
                            "title": "Redesigned repair node",
                            "responsibility": "worker",
                            "modeled_target": "development_process",
                            "acceptance_criteria": ["Redesigned route opens fresh repair work."],
                        }
                    ]
                ),
            ),
        )
        gate = next(iter(ledger["pm_decision_gates"].values()))
        source_result_id = gate["source_result_id"]

        flowguard_packet = _open_packets(ledger, kind="flowguard_check")[0]
        _complete_open_packet(ledger, flowguard_packet, _flowguard_semantic_recheck_body_from_packet(ledger, flowguard_packet))
        self.assertEqual(gate["status"], "awaiting_pm_flowguard_acceptance")
        _complete_pm_flowguard_acceptance(ledger)
        _complete_open_packet(
            ledger,
            _open_packets(ledger, kind="review")[0],
            _review_block_body(
                "Reviewer rejected the real route redesign decision.",
                blocker_class="local_artifact",
                recommended_resolution="Reviewer rejected the real route redesign decision.",
            ),
        )

        self.assertEqual(gate["status"], "awaiting_review")
        self.assertEqual(gate["staged_effect"]["status"], "pending")
        self.assertEqual(ledger["results"][source_result_id]["staged_effect"]["status"], "pending")
        self.assertEqual(ledger["active_route_version"], old_route_version)
        self.assertNotEqual(ledger["route_nodes"][node_id]["status"], "superseded")
        self.assertEqual(ledger["active_blockers"][blocker["blocker_id"]]["status"], "retired_after_new_current_blocker")
        active_review_blocks = [
            row
            for row in ledger["active_blockers"].values()
            if row["status"] == "active" and row["gate_kind"] == "review"
        ]
        self.assertEqual(len(active_review_blocks), 1)
        self.assertEqual(active_review_blocks[0]["required_recheck_role"], "reviewer")

    def test_pm_redesign_route_disposition_is_gated_before_application(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        _complete_node_acceptance_plan(ledger)
        node_id = _complete_active_node_packet_loop(ledger)
        old_route_version = ledger["active_route_version"]

        _complete_open_packet(
            ledger,
            _open_packets(ledger, kind="pm_disposition")[0],
            _pm_disposition_body(
                "PM chose route redesign for the completed node.",
                decision="redesign_route",
                reason="node needs a different route",
            ),
        )

        self.assertEqual(ledger["active_route_version"], old_route_version)
        gate = next(iter(ledger["pm_decision_gates"].values()))
        self.assertEqual(gate["gate_kind"], "pm_disposition")
        self.assertEqual(gate["status"], "awaiting_flowguard")
        self.assertTrue(_open_packets(ledger, kind="flowguard_check"))

        _complete_open_packet(ledger, _open_packets(ledger, kind="flowguard_check")[0], _flowguard_pass_body())
        self.assertEqual(gate["status"], "awaiting_pm_flowguard_acceptance")
        _complete_pm_flowguard_acceptance(ledger)
        _complete_open_packet(ledger, _open_packets(ledger, kind="review")[0], _review_pass_body())

        self.assertEqual(gate["status"], "applied")
        self.assertEqual(ledger["active_route_version"], old_route_version + 1)
        self.assertEqual(ledger["route_nodes"][node_id]["status"], "superseded")
        self.assertFalse(_open_packets(ledger, kind="closure"))

    def test_workerlocked_result_routes_pm_repair_without_flowguard_pass(self) -> None:
        ledger = _ledger()
        packet_id = _open_packets(ledger, scope="high_standard_contract")[0]

        _complete_open_packet(
            ledger,
            packet_id,
            json.dumps(
                {
                    "schema_version": "black_box_flowpilot.packet_outcome.v1",
                    "decision": "block",
                    "blocking": True,
                    "blocker_class": "needs_user",
                    "recommended_resolution": "PM must clarify the high-standard contract before evidence work.",
                }
            ),
        )

        packet = ledger["packets"][packet_id]
        self.assertEqual(packet["status"], "superseded_after_repair")
        result = ledger["results"][packet["superseded_by_result_id"]]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertEqual(result["contract_family_id"], "task.high_standard_contract")
        self.assertIn("requirements", result["missing_required_fields"])
        self.assertIn("decision", result["forbidden_fields_seen"])
        self.assertFalse(_open_packets(ledger, kind="flowguard_check"))
        active = [row for row in ledger["active_blockers"].values() if row["status"] == "active"]
        self.assertEqual(active, [])
        reissue_id = _open_packets(ledger, scope="high_standard_contract")[0]
        reissue_body = json.loads(ledger["packets"][reissue_id]["body"])
        self.assertEqual(reissue_body["contract_family_id"], "task.high_standard_contract")
        self.assertEqual(reissue_body["required_result_body_fields"], ["requirements", "acceptance_item_registry"])

    def test_final_matrix_blocks_missing_node_acceptance_plan(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        planning_result = "planning-result"
        ledger["results"][planning_result] = {
            "result_id": planning_result,
            "body": _route_plan_body(
                [
                    {
                        "node_id": "node-001",
                        "title": "Implement behavior",
                        "acceptance_criteria": ["Behavior implementation accepted."],
                        "high_standard_requirement_ids": ["hsr-001"],
                        "skill_standard_obligation_ids": ["skill-std-001"],
                    }
                ]
            ),
        }
        runtime.materialize_route_from_planning_result(ledger, planning_result)
        node_id = ledger["execution_frontier"]["active_node_id"]
        ledger["route_nodes"][node_id]["status"] = "accepted"
        ledger["route_nodes"][node_id]["pm_disposition_id"] = "pm-disposition"
        ledger["route_nodes"][node_id]["accepted_result_id"] = "node-result"
        ledger["route_nodes"][node_id]["flowguard_order_ids"] = ["flowguard-1"]
        ledger["route_nodes"][node_id]["review_ids"] = ["review-1"]
        ledger["route_nodes"][node_id]["validation_evidence_ids"] = ["validation-1"]

        closure = runtime.attempt_final_closure(ledger, "validation-missing-plan")

        self.assertEqual(closure["decision"], "blocked")
        self.assertIn("node_acceptance_plan", json.dumps(closure["blockers"]))
        self.assertEqual(ledger["final_requirement_evidence_matrix"]["status"], "blocked")

    def test_final_matrix_requires_direct_evidence_not_accepted_node_only(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        ledger["route_nodes"] = {
            "node-001": {
                "node_id": "node-001",
                "status": "accepted",
                "high_standard_requirement_ids": ["hsr-001"],
                "pm_disposition_id": "pm-disposition-001",
                "accepted_result_id": "result-node-001",
                "flowguard_order_ids": ["flowguard-001"],
                "review_ids": ["review-001"],
                "validation_evidence_ids": [],
                "deliverable_checks": [],
            }
        }
        ledger["pm_dispositions"] = {
            "pm-disposition-001": {
                "disposition_id": "pm-disposition-001",
                "decision": "accept",
                "covered_requirement_ids": ["hsr-001"],
                "validation_evidence_ids": [],
                "waived_requirement_ids": [],
            }
        }

        matrix = runtime.build_final_requirement_evidence_matrix(ledger)
        requirement_rows = [
            row
            for row in matrix["rows"]
            if row["kind"] == "high_standard_requirement" and row["row_id"] == "hsr-001"
        ]
        self.assertEqual(requirement_rows[0]["status"], "missing")

    def test_route_plan_requires_every_active_acceptance_item_owner(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        packet_id = _open_packets(ledger, scope="planning")[0]

        _complete_open_packet(
            ledger,
            packet_id,
            _route_plan_body(
                [
                    {
                        "node_id": "node-001",
                        "title": "Implement only one item",
                        "modeled_target": "development_process",
                        "acceptance_criteria": ["One acceptance item is covered."],
                        "acceptance_item_ids": ["acc-001"],
                    }
                ]
            ),
        )

        result = ledger["results"][ledger["packets"][packet_id]["superseded_by_result_id"]]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn("acc-002", result["quarantine_reason"])

    def test_node_acceptance_plan_requires_acceptance_item_projection(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        packet_id = _open_packets(ledger, scope="node_acceptance_plan")[0]
        payload = json.loads(_node_context_body(ledger))
        payload["node_context_package"].pop("acceptance_item_projection")

        _complete_open_packet(ledger, packet_id, json.dumps(payload))

        result = ledger["results"][ledger["packets"][packet_id]["superseded_by_result_id"]]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn("node_context_package.acceptance_item_projection", result["missing_required_fields"])

    def test_pm_disposition_requires_acceptance_item_closure(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)
        _complete_node_acceptance_plan(ledger)
        _complete_active_node_packet_loop(ledger)
        packet_id = _open_packets(ledger, kind="pm_disposition")[0]
        payload = json.loads(_pm_disposition_body())
        payload["acceptance_item_disposition"] = [
            {
                "acceptance_item_id": "acc-001",
                "disposition": "accepted",
                "basis": "Current node evidence closes this item.",
            }
        ]

        _complete_open_packet(ledger, packet_id, json.dumps(payload))

        result = ledger["results"][ledger["packets"][packet_id]["superseded_by_result_id"]]
        self.assertEqual(result["status"], "mechanical_contract_blocked")
        self.assertIn("acc-002", result["quarantine_reason"])

    def test_route_deliverable_checks_cover_semantic_and_forbidden_artifacts(self) -> None:
        ledger = _ledger()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger["project_root"] = str(root)
            (root / "data.json").write_text(json.dumps({"completion_claim": False}), encoding="utf-8")
            (root / "report.md").write_text("current report without forbidden branch", encoding="utf-8")
            os.utime(root / "report.md", (1, 1))
            (root / "ui").mkdir()
            (root / "ui" / "index.html").write_text("<html></html>", encoding="utf-8")
            runtime._event(ledger, "final_requirement_evidence_matrix_built")
            node = {
                "node_id": "node-001",
                "deliverable_checks": [
                    {
                        "check_id": "claim-false",
                        "kind": "json_field_equals",
                        "path": "data.json",
                        "json_path": "completion_claim",
                        "expected_value": False,
                    },
                    {"check_id": "no-fallback-text", "kind": "text_forbids", "path": "report.md", "text": "fallback parser"},
                    {"check_id": "no-ui", "kind": "path_glob_absent", "pattern": "ui/*.html"},
                    {
                        "check_id": "fresh-report",
                        "kind": "fresh_after_event",
                        "path": "report.md",
                        "event_type": "final_requirement_evidence_matrix_built",
                    },
                ],
            }

            results = {row["check_id"]: row for row in runtime._evaluate_route_deliverable_checks(ledger, node)}

        self.assertEqual(results["claim-false"]["status"], "passed")
        self.assertEqual(results["no-fallback-text"]["status"], "passed")
        self.assertEqual(results["no-ui"]["status"], "failed")
        self.assertEqual(results["fresh-report"]["status"], "failed")

    def test_high_standard_closure_requires_terminal_backward_replay(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        runtime.record_validation_evidence(ledger, "validation-current", status="passed")

        closure = runtime.attempt_final_closure(ledger, "validation-current")

        self.assertIn("missing_terminal_backward_replay", closure["blockers"])

    def test_high_standard_terminal_backward_replay_is_current_packet_before_closure(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_task_chain(
            ledger,
            _open_packets(ledger, scope="planning")[0],
            _route_plan_body(
                [
                    {
                        "node_id": "node-001",
                        "title": "Implement behavior",
                        "acceptance_criteria": ["Behavior implementation accepted."],
                        "high_standard_requirement_ids": ["hsr-001"],
                        "skill_standard_obligation_ids": ["skill-std-001"],
                    }
                ]
            ),
        )
        runtime.ensure_node_acceptance_plan_packet(ledger, "node-001")
        _complete_node_acceptance_plan(ledger)
        node_id = _complete_active_node_packet_loop(ledger)
        _complete_open_packet(
            ledger,
            _open_packets(ledger, kind="pm_disposition")[0],
            _pm_disposition_body("PM accepted node after role evidence absorption."),
        )
        self.assertEqual(ledger["execution_frontier"]["status"], "ready_for_final_closure")

        boundary = runtime.run_until_wait(ledger)

        self.assertEqual(boundary["next_action"]["action_type"], "dispatch_current_role")
        terminal_packet_id = boundary["next_action"]["subject_id"]
        terminal_packet = ledger["packets"][terminal_packet_id]
        self.assertEqual(terminal_packet["envelope"]["packet_kind"], "review")
        self.assertEqual(terminal_packet["envelope"]["route_scope"], "terminal_backward_replay")
        self.assertEqual(runtime.attempt_final_closure(ledger, ledger["latest_validation_evidence_id"])["decision"], "blocked")

        _complete_open_packet(
            ledger,
            terminal_packet_id,
            _terminal_backward_replay_body(terminal_packet),
        )

        self.assertEqual(ledger["route_nodes"][node_id]["status"], "accepted")
        self.assertTrue(ledger["terminal_backward_replays"])
        self.assertTrue(ledger["closure_confirmed_by_backward_replay"])
        self.assertEqual(ledger["closure"]["decision"], "complete")
        self.assertEqual(runtime.router_next_action(ledger).action_type, "terminal_complete")

    def test_terminal_backward_replay_block_does_not_restart_planning(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        _complete_planning(ledger)

        for expected_node_id in ("node-001", "node-002", "node-003"):
            self.assertEqual(ledger["execution_frontier"]["active_node_id"], expected_node_id)
            _complete_node_acceptance_plan(ledger)
            _complete_active_node_packet_loop(ledger)
            _complete_open_packet(
                ledger,
                _open_packets(ledger, kind="pm_disposition")[0],
                _pm_disposition_body(f"PM accepted {expected_node_id} after absorbing role evidence."),
            )

        self.assertEqual(ledger["execution_frontier"]["status"], "ready_for_final_closure")
        self.assertEqual(ledger["closure"]["decision"], "blocked")
        self.assertEqual(ledger["closure"]["blockers"], ["missing_terminal_backward_replay"])

        action = runtime.router_next_action(ledger)

        self.assertEqual(action.action_type, "issue_terminal_backward_replay_packet")
        self.assertEqual(action.responsibility, "reviewer")
        boundary = runtime.run_until_wait(ledger)
        terminal_packet_id = boundary["next_action"]["subject_id"]
        terminal_packet = ledger["packets"][terminal_packet_id]
        self.assertEqual(boundary["next_action"]["action_type"], "dispatch_current_role")
        self.assertEqual(terminal_packet["envelope"]["route_scope"], "terminal_backward_replay")
        self.assertEqual(_open_packets(ledger, scope="planning"), [])

    def test_parent_node_requires_backward_replay_before_pm_disposition(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        planning_result = "planning-result"
        parent_nodes = [
            {
                "node_id": "parent-001",
                "title": "Parent feature",
                "node_kind": "parent",
                "child_node_ids": ["node-001"],
                "acceptance_criteria": ["Parent composes child evidence"],
                "high_standard_requirement_ids": ["hsr-001"],
                "skill_standard_obligation_ids": ["skill-std-001"],
            },
            {
                "node_id": "node-001",
                "title": "Child implementation",
                "node_kind": "leaf",
                "parent_node_id": "parent-001",
                "acceptance_criteria": ["Child proves the implementation slice"],
                "high_standard_requirement_ids": ["hsr-001"],
                "skill_standard_obligation_ids": ["skill-std-001"],
            },
        ]
        ledger["results"][planning_result] = {
            "result_id": planning_result,
            "body": _route_plan_body(parent_nodes),
        }
        runtime.materialize_route_from_planning_result(ledger, planning_result)
        runtime.ensure_node_acceptance_plan_packet(ledger, "parent-001")

        _complete_node_acceptance_plan(ledger)

        self.assertEqual(ledger["route_nodes"]["parent-001"]["status"], "awaiting_children")
        self.assertEqual(ledger["execution_frontier"]["active_node_id"], "node-001")
        self.assertFalse(_open_packets(ledger, scope="node"))
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "cannot receive a worker task packet"):
            runtime.ensure_next_node_task_packet(ledger | {"execution_frontier": {**ledger["execution_frontier"], "active_node_id": "parent-001"}})
        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "no longer a supported current FlowPilot path"):
            runtime.ensure_node_prework_flowguard_packet(ledger, "parent-001")

        _complete_node_acceptance_plan(ledger)
        child_id = _complete_active_node_packet_loop(ledger)
        self.assertEqual(child_id, "node-001")
        _complete_open_packet(
            ledger,
            _open_packets(ledger, kind="pm_disposition")[0],
            _pm_disposition_body("PM accepted child evidence."),
        )

        self.assertEqual(ledger["execution_frontier"]["active_node_id"], "parent-001")
        self.assertEqual(ledger["route_nodes"]["parent-001"]["status"], "awaiting_parent_backward_replay")
        parent_replay_packets = _open_packets(ledger, scope="parent_backward_replay")
        self.assertEqual(parent_replay_packets, [parent_replay_packets[0]])
        self.assertFalse(_open_packets(ledger, kind="pm_disposition"))

        _complete_task_chain(
            ledger,
            parent_replay_packets[0],
            _parent_backward_replay_body("parent-001", ["node-001"], [ledger["route_nodes"]["node-001"]["accepted_result_id"]]),
        )

        self.assertTrue(ledger["route_nodes"]["parent-001"]["parent_backward_replay_id"])
        self.assertTrue(_open_packets(ledger, kind="pm_disposition"))
        _complete_open_packet(
            ledger,
            _open_packets(ledger, kind="pm_disposition")[0],
            _pm_disposition_body("PM accepted parent composition."),
        )
        self.assertEqual(ledger["route_nodes"]["parent-001"]["status"], "accepted")

    def test_leaf_with_child_node_ids_is_rejected_by_strict_route_plan(self) -> None:
        ledger = _ledger()
        _complete_preplanning(ledger)
        ledger["results"]["planning-result"] = {
            "result_id": "planning-result",
            "body": _route_plan_body(
                [
                    {
                        "node_id": "node-001",
                        "title": "Invalid leaf",
                        "node_kind": "leaf",
                        "child_node_ids": ["node-002"],
                        "acceptance_criteria": ["Invalid leaf should be rejected"],
                    },
                    {
                        "node_id": "node-002",
                        "title": "Child",
                        "node_kind": "leaf",
                        "parent_node_id": "node-001",
                        "acceptance_criteria": ["Child exists only to expose the shape conflict"],
                    },
                ]
            ),
        }

        with self.assertRaisesRegex(runtime.BlackBoxRuntimeError, "leaf node node-001 must not have child_node_ids"):
            runtime.materialize_route_from_planning_result(ledger, "planning-result")


if __name__ == "__main__":
    unittest.main()
