"""Execute direct production-runtime scenarios for unified repair.

This is the sole native runtime-conformance owner.  It invokes the real
FlowPilot runtime and run-shell APIs against fresh in-memory or temporary-run
state.  It does not run pytest, inspect source text for markers, or treat model
output as product-runtime evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from typing import Any, Callable, Mapping

try:  # pragma: no cover - package execution
    from . import run_flowpilot_unified_repair_integrity_checks as unified
except ImportError:  # pragma: no cover - direct script execution
    import run_flowpilot_unified_repair_integrity_checks as unified

if str(unified.REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(unified.REPO_ROOT))

from tests.flowpilot_repair_test_helpers import runtime, seeded_ledger  # noqa: E402
from flowpilot_core_runtime import run_shell  # noqa: E402


RESULT_SCHEMA = "flowpilot.unified_repair_native_owner_result.v1"
CHECK_ID = "native_runtime_conformance"
EXECUTION_OWNER = "native.unified_repair.runtime_conformance"
OWNER_COMMAND = (
    "python simulations/run_flowpilot_unified_repair_native_runtime_conformance.py"
)
DEFAULT_RESULT_PATH = (
    unified.ROOT
    / "flowpilot_unified_repair_native_runtime_conformance_results.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _source_node_id(ledger: dict[str, Any]) -> str:
    route = ledger["routes"][str(ledger["active_route_version"])]
    return str(route["node_order"][0])


def _lease_ack_and_open(
    ledger: dict[str, Any],
    packet_id: str,
    role: str,
) -> str:
    lease_id = runtime.lease_agent(ledger, role, packet_id=packet_id)
    runtime.assign_packet(ledger, packet_id, lease_id)
    runtime.ack_lease(ledger, lease_id, packet_id)
    runtime.open_authorized_input_materials_for_role(
        ledger,
        packet_id,
        lease_id,
    )
    return lease_id


def _historical_decision_body(
    ledger: dict[str, Any],
    packet_id: str,
    *,
    decision: str,
    extra: dict[str, Any] | None = None,
) -> str:
    envelope = ledger["packets"][packet_id]["envelope"]
    payload: dict[str, Any] = {
        "decision": decision,
        "reason": f"Apply {decision} to the exact observed historical defect.",
        "target_repair_trigger_id": envelope["repair_trigger_id"],
        "target_node_id": envelope["historical_source_node_id"],
        "defect_summary": envelope["historical_defect_summary"],
        "impact_summary": envelope["historical_impact_summary"],
        "next_action": decision,
    }
    payload.update(extra or {})
    return json.dumps(payload, sort_keys=True)


def _stage_historical(
    ledger: dict[str, Any],
    source_node_id: str,
    *,
    decision: str = "repair_current_scope",
    extra: dict[str, Any] | None = None,
) -> tuple[str, str]:
    packet_id = runtime.ensure_pm_historical_repair_decision_packet(
        ledger,
        source_node_id,
        defect_summary="A completed node omitted one required deliverable.",
        impact_summary="The omission invalidates the node and its dependent consumers.",
        evidence_refs=["observation:native-runtime-conformance"],
    )
    lease_id = _lease_ack_and_open(ledger, packet_id, "pm")
    result_id = runtime.submit_result(
        ledger,
        lease_id,
        packet_id,
        _historical_decision_body(
            ledger,
            packet_id,
            decision=decision,
            extra=extra,
        ),
    )
    result = ledger["results"][result_id]
    return (
        str(result["pm_repair_decision_id"]),
        str(result.get("pm_decision_gate_id") or ""),
    )


def _apply_gate(ledger: dict[str, Any], gate_id: str) -> None:
    gate = ledger["pm_decision_gates"][gate_id]
    gate["status"] = "awaiting_system_closure"
    runtime._apply_staged_pm_decision_gate(
        ledger,
        gate,
        system_closure_id=f"native-system-closure:{gate_id}",
    )


def _role_result(summary: str) -> str:
    return json.dumps(
        {
            "decision": "pass",
            "pm_visible_summary": [summary],
            "current_evidence_refs": ["evidence:native-current"],
        },
        sort_keys=True,
    )


def _review_result(summary: str) -> str:
    return json.dumps(
        {
            "pm_visible_summary": [summary],
            "reviewed_by_role": "human_like_reviewer",
            "passed": True,
            "findings": [],
            "blockers": [],
            "pm_suggestion_items": [
                "PM may accept the current evidence or request a bounded repair."
            ],
            "contract_self_check": {
                "all_required_fields_present": True,
                "exact_field_names_used": True,
                "empty_required_arrays_explicit": True,
                "runtime_mechanical_validation_passed": True,
                "semantic_sufficiency_reviewed_by_runtime": False,
            },
        },
        sort_keys=True,
    )


def _flowguard_result(
    ledger: dict[str, Any],
    packet_id: str,
    blocker_id: str,
) -> str:
    packet = ledger["packets"][packet_id]
    required_read_ids = [
        str(row.get("result_id") or "")
        for row in packet["envelope"].get("authorized_result_reads", [])
        if row.get("required_before_submit") is True
        and str(row.get("result_id") or "")
    ]
    bindings = packet["envelope"].get(
        "result_contract_profile_bindings",
        {},
    )
    semantic_binding = (
        bindings.get("flowguard.semantic_recheck_required", {})
        if isinstance(bindings, dict)
        else {}
    )
    obligation_ids = [
        str(item)
        for item in semantic_binding.get("repair_obligation_ids") or []
        if str(item)
    ]
    return json.dumps(
        {
            "pm_visible_summary": [
                "FlowGuard passed the current repaired Worker result."
            ],
            "reviewed_by_role": "flowguard_operator",
            "passed": True,
            "modeled_boundary": "Current repair packet and current result only.",
            "blockers": [],
            "pm_suggestion_items": [],
            "semantic_recheck": {
                "blocker_id": blocker_id,
                "subject_result_consumed": True,
                "subject_bound_semantic_coverage": True,
                "coverage_boundary": "subject_bound_semantic",
                "consumed_authorized_result_read_ids": required_read_ids,
                "consumed_repair_obligation_ids": obligation_ids,
            },
            "contract_self_check": {
                "all_required_fields_present": True,
                "exact_field_names_used": True,
                "empty_required_arrays_explicit": True,
                "runtime_mechanical_validation_passed": True,
                "semantic_sufficiency_reviewed_by_runtime": False,
            },
        },
        sort_keys=True,
    )


def _write_flowguard_evidence(
    ledger: dict[str, Any],
    packet_id: str,
) -> Path:
    if not ledger.get("run_root"):
        ledger["run_root"] = tempfile.mkdtemp(
            prefix="flowpilot-native-runtime-owner-"
        )
    packet = ledger["packets"][packet_id]
    packet_body = json.loads(packet["body"])
    policy = packet_body.get("evidence_output_policy")
    if isinstance(policy, dict):
        root_text = str(policy.get("run_local_evidence_root") or "")
        if "<" in root_text or ">" in root_text:
            policy["run_local_evidence_root"] = str(
                Path(str(ledger["run_root"]))
                / "evidence"
                / "flowguard"
                / packet_id
            )
            packet["body"] = json.dumps(packet_body, sort_keys=True)
            packet["envelope"]["body_hash"] = runtime.hash_text(
                packet["body"]
            )
    path = runtime._flowguard_packet_evidence_artifact_path(
        ledger,
        packet,
    )
    _require(path is not None, "FlowGuard evidence path was not materialized")
    assert path is not None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "flowpilot.flowguard_evidence.v1",
                "model_test_alignment_report": {
                    "decision": "pass",
                    "failed_predicates": [],
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def _open_packet(
    ledger: dict[str, Any],
    *,
    packet_kind: str,
    route_node_id: str = "",
) -> str:
    matches = [
        str(packet_id)
        for packet_id, packet in ledger["packets"].items()
        if packet.get("status") == "open"
        and packet.get("envelope", {}).get("packet_kind") == packet_kind
        and (
            not route_node_id
            or packet.get("envelope", {}).get("route_node_id")
            == route_node_id
        )
    ]
    _require(
        len(matches) == 1,
        f"expected one open {packet_kind} packet, found {matches}",
    )
    return matches[0]


def _scenario_direct_local_repair() -> dict[str, Any]:
    ledger, _ = seeded_ledger()
    ledger["active_blockers"] = {}
    source_id = _source_node_id(ledger)
    decision_id, gate_id = _stage_historical(ledger, source_id)
    _require(not ledger["active_blockers"], "historical intake fabricated a blocker")
    _require(
        decision_id not in ledger["repair_transactions"],
        "repair committed before the decision gate",
    )
    _apply_gate(ledger, gate_id)
    transaction = ledger["repair_transactions"][decision_id]
    replacement_id = str(transaction["replacement_node_id"])
    route = ledger["routes"][str(ledger["active_route_version"])]
    _require(
        ledger["route_nodes"][source_id]["status"] == "superseded",
        "source node did not become immutable history",
    )
    _require(
        route["node_order"] == [replacement_id],
        "same-slot replacement did not become the singular current member",
    )
    worker_packet = ledger["packets"][transaction["fresh_packet_id"]]
    _require(
        worker_packet["envelope"]["responsibility"] == "worker",
        "substantive repair did not dispatch Worker",
    )
    _require(
        worker_packet["created_at"]
        > ledger["pm_decision_gates"][gate_id]["staged_effect"]["committed_at"],
        "Worker packet predates staged-effect commit",
    )
    return {
        "decision_id": decision_id,
        "source_node_id": source_id,
        "replacement_node_id": replacement_id,
        "worker_packet_id": worker_packet["packet_id"],
    }


def _scenario_subtree_repair_child() -> dict[str, Any]:
    ledger, _ = seeded_ledger()
    ledger["active_blockers"] = {}
    source_id = _source_node_id(ledger)
    child_id = "native-repair-child"
    decision_id, gate_id = _stage_historical(
        ledger,
        source_id,
        decision="repair_subtree",
        extra={
            "repair_subtree_scope": {
                "source_node_id": source_id,
                "include_descendants": True,
                "preserve_unaffected_siblings": True,
                "replay_policy": "derived_dependency_cone",
                "repair_child_specs": [
                    {
                        "node_id": child_id,
                        "purpose": "Repair the bounded omitted subwork.",
                        "required_evidence": [
                            "fresh Worker result",
                            "fresh validation",
                        ],
                    }
                ],
            }
        },
    )
    _apply_gate(ledger, gate_id)
    replacement_id = str(
        ledger["repair_transactions"][decision_id]["replacement_node_id"]
    )
    child = ledger["route_nodes"][child_id]
    _require(
        child["parent_node_id"] == replacement_id,
        "repair child was not attached beneath active replacement",
    )
    _require(
        child["parent_node_id"] != source_id,
        "repair child was attached beneath superseded source",
    )
    return {
        "replacement_node_id": replacement_id,
        "repair_child_node_id": child_id,
    }


def _scenario_membership_and_dependency_replay() -> dict[str, Any]:
    ledger, _ = seeded_ledger()
    ledger["active_blockers"] = {}
    source_id = _source_node_id(ledger)
    parent_id = "native-parent"
    sibling_id = "native-sibling"
    ledger["route_nodes"][source_id]["parent_node_id"] = parent_id
    ledger["route_nodes"][parent_id] = {
        "node_id": parent_id,
        "route_version": 1,
        "title": "Parent consumer",
        "node_kind": "module",
        "parent_node_id": "",
        "child_node_ids": [source_id, sibling_id],
        "status": "accepted",
        "repair_generation": 0,
        "accepted_result_id": "result:native-parent",
        "parent_backward_replay_id": "replay:native-parent",
        "pm_disposition_id": "pm:native-parent",
        "validation_evidence_ids": ["validation:native-parent"],
    }
    ledger["route_nodes"][sibling_id] = {
        "node_id": sibling_id,
        "route_version": 1,
        "title": "Unaffected sibling",
        "node_kind": "leaf",
        "parent_node_id": parent_id,
        "child_node_ids": [],
        "status": "accepted",
        "repair_generation": 0,
        "accepted_result_id": "result:native-sibling",
    }
    ledger["routes"]["1"]["node_order"] = [
        parent_id,
        source_id,
        sibling_id,
    ]
    decision_id, gate_id = _stage_historical(ledger, source_id)
    _apply_gate(ledger, gate_id)
    mutation = ledger["route_mutations"][-1]
    replacement_id = str(
        ledger["repair_transactions"][decision_id]["replacement_node_id"]
    )
    _require(
        mutation["affected_dependency_node_ids"] == [parent_id],
        "parent dependency cone was not derived",
    )
    _require(
        mutation["unaffected_rebound_ids"] == [sibling_id],
        "unaffected sibling was not explicitly rebound",
    )
    _require(
        ledger["route_nodes"][parent_id]["accepted_result_id"] == "",
        "affected parent retained stale accepted authority",
    )
    _require(
        ledger["route_nodes"][sibling_id]["accepted_result_id"]
        == "result:native-sibling",
        "unaffected sibling evidence was erased",
    )
    return {
        "replacement_node_id": replacement_id,
        "affected_dependency_node_ids": mutation[
            "affected_dependency_node_ids"
        ],
        "unaffected_rebound_ids": mutation["unaffected_rebound_ids"],
    }


def _scenario_repeated_generation() -> dict[str, Any]:
    ledger, _ = seeded_ledger()
    ledger["active_blockers"] = {}
    root_id = _source_node_id(ledger)
    first_id, first_gate = _stage_historical(ledger, root_id)
    _apply_gate(ledger, first_gate)
    first_replacement = str(
        ledger["repair_transactions"][first_id]["replacement_node_id"]
    )
    second_id, second_gate = _stage_historical(ledger, root_id)
    _apply_gate(ledger, second_gate)
    second_replacement = str(
        ledger["repair_transactions"][second_id]["replacement_node_id"]
    )
    second = ledger["route_nodes"][second_replacement]
    _require(second["repair_generation"] == 2, "repair generation did not increment")
    _require(second["repair_root_id"] == root_id, "repair root changed")
    _require(
        second["previous_repair_node_id"] == first_replacement,
        "repeated repair skipped the immediately previous generation",
    )
    return {
        "repair_root_id": root_id,
        "first_replacement_node_id": first_replacement,
        "second_replacement_node_id": second_replacement,
        "repair_generation": second["repair_generation"],
    }


def _scenario_terminal_worker_chain() -> dict[str, Any]:
    ledger, blocker_id = seeded_ledger()
    ledger["recursive_route_execution_required"] = True
    blocker = ledger["active_blockers"][blocker_id]
    blocker["route_scope"] = runtime.TERMINAL_BACKWARD_REPLAY_SCOPE
    blocker["blocker_class"] = "terminal_closure"
    blocker["recommended_resolution"] = (
        "Repair the terminal deliverable and rerun backward replay."
    )
    node_id = str(blocker["route_node_id"])
    acceptance_item_id = "acceptance:native-terminal-gap"
    ledger["acceptance_item_registry"] = {
        "items": [
            {
                "acceptance_item_id": acceptance_item_id,
                "status": "active",
            }
        ]
    }
    ledger["route_nodes"][node_id]["acceptance_item_ids"] = [
        acceptance_item_id
    ]
    pm_packet_id = runtime._ensure_pm_repair_decision_packet_for_blocker(
        ledger,
        blocker_id,
    )
    pm_packet_body = json.loads(ledger["packets"][pm_packet_id]["body"])
    obligations = pm_packet_body.get("repair_evidence_obligations") or []
    supplemental_contract = {
        "schema_version": "flowpilot.terminal_supplemental_repair_contract.v1",
        "contract_id": "native-terminal-supplemental-r1",
        "round_number": 1,
        "original_contract_hash": ledger["contract_hash"],
        "terminal_blocker_id": blocker_id,
        "terminal_gap_report_result_id": blocker["result_id"],
        "pm_reason": "The terminal reviewer found a current product gap.",
        "repair_items": [
            {
                "repair_item_id": "native-terminal-gap-r1-item-1",
                "gap_kind": "latent_high_standard_requirement",
                "original_goal_link": "Close the frozen acceptance contract.",
                "reviewer_gap": "The current delivered product misses one terminal item.",
                "required_repair": "Produce a fresh Worker repair and recheck it.",
                "owner_repair_node_id": node_id,
                "acceptance_item_ids": runtime._active_acceptance_item_ids(ledger),
                "required_evidence": [
                    "fresh Worker result",
                    "fresh FlowGuard result",
                    "fresh Reviewer result",
                ],
                "status": "open",
            }
        ],
    }
    pm_payload = {
        "decision": "repair_current_scope",
        "reason": "Repair the terminal gap through the shared engine.",
        "target_blocker_id": blocker_id,
        "next_action": "repair_current_scope",
        "supplemental_repair_contract": supplemental_contract,
    }
    if obligations:
        pm_payload["repair_obligation_disposition"] = (
            runtime._repair_obligation_disposition_minimal_shape(
                obligations,
                "repair_current_scope",
            )
        )
    pm_lease_id = _lease_ack_and_open(ledger, pm_packet_id, "pm")
    pm_result_id = runtime.submit_result(
        ledger,
        pm_lease_id,
        pm_packet_id,
        json.dumps(pm_payload, sort_keys=True),
    )
    _require(
        ledger["results"][pm_result_id]["status"] == "accepted",
        "terminal PM decision was not accepted: "
        + str(ledger["results"][pm_result_id].get("status") or "")
        + " / "
        + str(ledger["results"][pm_result_id].get("blocked_reason") or ""),
    )
    decision_id = str(blocker["pm_repair_decision_id"])
    gate_id = str(ledger["results"][pm_result_id]["pm_decision_gate_id"])
    _apply_gate(ledger, gate_id)
    transaction = ledger["repair_transactions"][decision_id]
    worker_packet_id = str(transaction["fresh_packet_id"])
    worker_packet = ledger["packets"][worker_packet_id]
    _require(
        worker_packet["envelope"]["responsibility"] == "worker",
        "terminal substantive repair did not dispatch Worker",
    )
    _require(
        worker_packet["envelope"]["supplemental_contract_id"]
        == supplemental_contract["contract_id"],
        "terminal Worker packet is not bound to supplemental contract",
    )
    worker_lease_id = _lease_ack_and_open(
        ledger,
        worker_packet_id,
        "worker",
    )
    worker_result_id = runtime.submit_result(
        ledger,
        worker_lease_id,
        worker_packet_id,
        _role_result("Worker produced a fresh terminal repair."),
    )
    _require(
        ledger["results"][worker_result_id]["status"] == "mechanically_valid",
        "fresh terminal Worker result did not enter substantive checks: "
        + json.dumps(
            {
                key: ledger["results"][worker_result_id].get(key)
                for key in (
                    "status",
                    "blocked_reason",
                    "missing_required_fields",
                    "contract_errors",
                    "body_contract_errors",
                )
                if ledger["results"][worker_result_id].get(key) not in (None, "", [])
            },
            sort_keys=True,
        ),
    )
    flowguard_packet_ids = [
        packet_id
        for packet_id, packet in ledger["packets"].items()
        if packet["status"] == "open"
        and packet["envelope"]["packet_kind"] == "flowguard_check"
        and packet["envelope"]["subject_id"] == worker_packet_id
    ]
    _require(
        len(flowguard_packet_ids) == 1,
        "fresh terminal Worker result did not dispatch one FlowGuard packet: "
        + json.dumps(
            [
                {
                    "packet_id": packet_id,
                    "packet_kind": packet["envelope"].get("packet_kind"),
                    "subject_id": packet["envelope"].get("subject_id"),
                    "route_node_id": packet["envelope"].get("route_node_id"),
                    "responsibility": packet["envelope"].get("responsibility"),
                }
                for packet_id, packet in ledger["packets"].items()
                if packet["status"] == "open"
            ],
            sort_keys=True,
        ),
    )
    flowguard_packet_id = flowguard_packet_ids[0]
    flowguard_lease_id = _lease_ack_and_open(
        ledger,
        flowguard_packet_id,
        "flowguard_operator",
    )
    _write_flowguard_evidence(ledger, flowguard_packet_id)
    flowguard_result_id = runtime.submit_result(
        ledger,
        flowguard_lease_id,
        flowguard_packet_id,
        _flowguard_result(ledger, flowguard_packet_id, blocker_id),
    )
    _require(
        ledger["results"][flowguard_result_id]["status"] == "accepted",
        "terminal FlowGuard recheck was not accepted",
    )
    review_packet_ids = [
        packet_id
        for packet_id, packet in ledger["packets"].items()
        if packet["status"] == "open"
        and packet["envelope"]["packet_kind"] == "review"
        and packet["envelope"]["subject_id"] == worker_packet_id
    ]
    _require(
        len(review_packet_ids) == 1,
        "fresh terminal FlowGuard result did not dispatch one Reviewer packet",
    )
    review_packet_id = review_packet_ids[0]
    review_lease_id = _lease_ack_and_open(
        ledger,
        review_packet_id,
        "reviewer",
    )
    review_result_id = runtime.submit_result(
        ledger,
        review_lease_id,
        review_packet_id,
        _review_result("Reviewer accepted the fresh terminal repair."),
    )
    _require(
        ledger["results"][review_result_id]["status"] == "accepted",
        "terminal Reviewer recheck was not accepted",
    )
    replacement_node_id = str(transaction["replacement_node_id"])
    pm_disposition_packet_ids = [
        packet_id
        for packet_id, packet in ledger["packets"].items()
        if packet["status"] == "open"
        and packet["envelope"]["packet_kind"] == "pm_disposition"
        and packet["envelope"]["route_node_id"] == replacement_node_id
    ]
    _require(
        len(pm_disposition_packet_ids) == 1,
        "fresh terminal Reviewer result did not dispatch one PM disposition packet: "
        + json.dumps(
            {
                "open_packets": [
                    {
                        "packet_id": packet_id,
                        "packet_kind": packet["envelope"].get("packet_kind"),
                        "subject_id": packet["envelope"].get("subject_id"),
                        "route_node_id": packet["envelope"].get("route_node_id"),
                        "responsibility": packet["envelope"].get("responsibility"),
                    }
                    for packet_id, packet in ledger["packets"].items()
                    if packet["status"] == "open"
                ],
                "replacement_node": ledger["route_nodes"][replacement_node_id],
                "execution_frontier": ledger.get("execution_frontier"),
                "latest_validation": ledger.get("validation_evidence", {}).get(
                    str(ledger.get("latest_validation_evidence_id") or "")
                ),
            },
            sort_keys=True,
        ),
    )
    pm_disposition_packet_id = pm_disposition_packet_ids[0]
    acceptance_item_ids = list(
        ledger["route_nodes"][replacement_node_id].get("acceptance_item_ids") or []
    )
    pm_disposition_lease_id = _lease_ack_and_open(
        ledger,
        pm_disposition_packet_id,
        "pm",
    )
    pm_disposition_result_id = runtime.submit_result(
        ledger,
        pm_disposition_lease_id,
        pm_disposition_packet_id,
        json.dumps(
            {
                "decision": "accept",
                "reason": "PM accepts the fresh Worker, FlowGuard, and Reviewer evidence.",
                "acceptance_item_disposition": [
                    {
                        "acceptance_item_id": item_id,
                        "disposition": "accepted",
                        "basis": (
                            "Fresh Worker, FlowGuard, Reviewer, and validation evidence."
                        ),
                    }
                    for item_id in acceptance_item_ids
                ],
            },
            sort_keys=True,
        ),
    )
    _require(
        ledger["results"][pm_disposition_result_id]["status"] == "accepted",
        "terminal repair PM disposition was not accepted",
    )
    node = ledger["route_nodes"][replacement_node_id]
    _require(
        bool(node.get("validation_evidence_ids")),
        "terminal repair did not create fresh validation evidence",
    )
    validation_id = str(node["validation_evidence_ids"][-1])
    route_gate_ledger = runtime.build_final_route_wide_gate_ledger(ledger)
    requirement_matrix = runtime.build_final_requirement_evidence_matrix(ledger)
    _require(
        runtime._final_gate_ledgers_clean_for_terminal_replay(ledger),
        "terminal repair did not close final gate ledgers: "
        + json.dumps(
            {
                "route_unresolved": route_gate_ledger.get("unresolved"),
                "requirement_unresolved": requirement_matrix.get("unresolved"),
                "replacement_node_status": node.get("status"),
                "pm_disposition_id": node.get("pm_disposition_id"),
            },
            sort_keys=True,
        ),
    )
    terminal_packet_id = runtime.ensure_terminal_backward_replay_packet(
        ledger,
        validation_id,
    )
    terminal_packet_body = json.loads(
        ledger["packets"][terminal_packet_id]["body"]
    )
    targets = terminal_packet_body["segment_targets"]
    terminal_payload = {
        "final_artifact_refs": [
            {
                "id": "delivered-product",
                "status": "closed",
                "basis": "The repaired product was inspected directly.",
            }
        ],
        "acceptance_item_closure": [
            {
                "id": str(target["segment_id"]).removeprefix(
                    "acceptance-item:"
                ),
                "status": "closed",
                "basis": (
                    "Current terminal replay evidence closes this acceptance item."
                ),
            }
            for target in targets
            if str(target.get("segment_id") or "").startswith("acceptance-item:")
        ],
        "route_segment_replay": [
            {
                "segment_id": target["segment_id"],
                "segment_kind": target["segment_kind"],
                "status": "closed",
                "basis": "Current repair evidence closes this segment.",
            }
            for target in targets
        ],
        "waiver_records": [],
        "final_blockers": [],
    }
    terminal_lease_id = _lease_ack_and_open(
        ledger,
        terminal_packet_id,
        "reviewer",
    )
    terminal_result_id = runtime.submit_result(
        ledger,
        terminal_lease_id,
        terminal_packet_id,
        json.dumps(terminal_payload, sort_keys=True),
    )
    _require(
        ledger["results"][terminal_result_id]["status"] == "accepted",
        "terminal backward replay did not accept current repair evidence",
    )
    identity_fields = (
        "supplemental_contract_id",
        "repair_generation",
        "source_generation",
    )
    for artifact in (
        ledger["results"][worker_result_id]["envelope"],
        ledger["results"][flowguard_result_id]["envelope"],
        ledger["results"][review_result_id]["envelope"],
        ledger["validation_evidence"][validation_id],
        ledger["terminal_backward_replays"][
            ledger["terminal_backward_replay_id"]
        ],
    ):
        for field in identity_fields:
            _require(
                artifact[field] == transaction[field],
                f"terminal evidence identity mismatch for {field}",
            )
    return {
        "decision_id": decision_id,
        "replacement_node_id": replacement_node_id,
        "worker_result_id": worker_result_id,
        "flowguard_result_id": flowguard_result_id,
        "review_result_id": review_result_id,
        "terminal_result_id": terminal_result_id,
        "supplemental_contract_id": supplemental_contract["contract_id"],
    }


def _scenario_terminal_round_cap() -> dict[str, Any]:
    ledger, blocker_id = seeded_ledger()
    blocker = ledger["active_blockers"][blocker_id]
    blocker["route_scope"] = runtime.TERMINAL_BACKWARD_REPLAY_SCOPE
    state = ledger["terminal_supplemental_repair"]
    state.update(
        {
            "status": "active",
            "current_round": 3,
            "active_contract_id": "native-terminal-r3",
        }
    )
    result = ledger["results"][blocker["result_id"]]
    runtime._record_terminal_supplemental_repair_exhausted(
        ledger,
        blocker,
        result,
    )
    _require(
        ledger["terminal_lifecycle"]["status"] == "repair_rounds_exhausted",
        "three-round terminal cap did not produce one hard disposition",
    )
    packet_ids_before = set(ledger["packets"])
    rejected_after_terminal = False
    try:
        runtime._ensure_pm_repair_decision_packet_for_blocker(
            ledger,
            blocker_id,
        )
    except runtime.BlackBoxRuntimeError as exc:
        rejected_after_terminal = "run is terminal" in str(exc)
    _require(
        rejected_after_terminal and set(ledger["packets"]) == packet_ids_before,
        "terminal cap incorrectly issued another PM repair packet",
    )
    return {
        "current_round": state["current_round"],
        "terminal_status": ledger["terminal_lifecycle"]["status"],
    }


def _scenario_completed_run_bridge() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(
        prefix="unified-repair-run-bridge-",
        dir=unified.REPO_ROOT / "tmp",
    ) as temp_dir:
        root = Path(temp_dir)
        old_shell = run_shell.create_run_shell(
            root,
            "Original goal",
            "Original contract",
            run_id="native-old-run",
        )
        old_ledger = run_shell.load_run_ledger(old_shell)
        old_ledger["startup_intake"] = {
            "status": "confirmed",
            "current_run_authority": True,
            "controller_may_read_body": False,
            "body_text_included": False,
            "startup_answers": {
                "background_collaboration_authorized": True
            },
        }
        runtime.create_route(old_ledger, "Original route", ["Deliver output"])
        packet_id = runtime.issue_task_packet(
            old_ledger,
            "worker",
            "Deliver output",
            json.dumps({"schema_version": "native.original.v1"}),
        )
        result_id = "native-old-result"
        body = "Original accepted output."
        old_ledger["results"][result_id] = {
            "result_id": result_id,
            "packet_id": packet_id,
            "producer_lease_id": "native-old-lease",
            "producer_agent_id": "native-old-worker",
            "route_version": old_ledger["active_route_version"],
            "status": "accepted",
            "mechanical_blockers": [],
            "non_authoritative": False,
            "quarantine_reason": "",
            "envelope": {
                "packet_id": packet_id,
                "result_id": result_id,
                "route_version": old_ledger["active_route_version"],
                "output_type": "artifact",
                "evidence_ids": ["evidence:native-old"],
                "evidence_generation": old_ledger["source_generation"],
                "body_hash": runtime.hash_text(body),
                "body_visibility": "sealed",
                "referenced_packet_body_hash": old_ledger["packets"][
                    packet_id
                ]["envelope"]["body_hash"],
                "output_contract": old_ledger["packets"][packet_id][
                    "envelope"
                ]["output_contract"],
                "ack_result_accepted_separate": True,
            },
            "body": body,
            "review_id": "native-old-review",
            "accepted": True,
            "created_at": runtime.now_iso(),
        }
        old_ledger["packets"][packet_id].update(
            {
                "result_ids": [result_id],
                "accepted_result_id": result_id,
                "status": "accepted",
            }
        )
        old_ledger["closure"] = {
            "decision": "complete",
            "blockers": [],
            "created_at": runtime.now_iso(),
        }
        run_shell.save_run_ledger(old_shell, old_ledger)
        old_hash = hashlib.sha256(old_shell.ledger_path.read_bytes()).hexdigest()
        new_shell = run_shell.create_historical_repair_run_shell(
            root,
            source_run_id=old_shell.run_id,
            defect_summary="A late defect was observed.",
            impact_summary="The bounded output needs a new repair run.",
            evidence_refs=["observation:native-post-run"],
            source_result_ids=[result_id],
            run_id="native-new-run",
        )
        new_ledger = run_shell.load_run_ledger(new_shell)
        imported_id = new_ledger["historical_repair_intake"][
            "imported_evidence_ids"
        ][0]
        imported = new_ledger["imported_evidence"][imported_id]
        _require(
            new_shell.run_id != old_shell.run_id,
            "completed-run repair reused the old run id",
        )
        _require(
            new_ledger["historical_repair_intake"][
                "old_control_state_reactivated"
            ]
            is False,
            "completed-run repair reactivated old control state",
        )
        _require(
            imported["read_only"] is True
            and imported["current_authority"] is False,
            "old output was promoted to current authority",
        )
        _require(
            hashlib.sha256(old_shell.ledger_path.read_bytes()).hexdigest()
            == old_hash,
            "old completed run changed during bridge creation",
        )
        return {
            "source_run_id": old_shell.run_id,
            "current_run_id": new_shell.run_id,
            "imported_evidence_id": imported_id,
        }


def _scenario_authorized_waiver_refinement() -> dict[str, Any]:
    ledger, _ = seeded_ledger()
    ledger["active_blockers"] = {}
    source_id = _source_node_id(ledger)
    packet_id = runtime.ensure_pm_historical_repair_decision_packet(
        ledger,
        source_id,
        defect_summary="A bounded historical defect was observed.",
        impact_summary="PM must explicitly disposition the defect.",
        evidence_refs=["observation:native-waiver"],
    )
    lease_id = _lease_ack_and_open(ledger, packet_id, "pm")
    result_id = runtime.submit_result(
        ledger,
        lease_id,
        packet_id,
        _historical_decision_body(
            ledger,
            packet_id,
            decision="waive_with_authority",
            extra={"authority_ref": "authority:native-user-waiver"},
        ),
    )
    decision_id = str(
        ledger["results"][result_id]["pm_repair_decision_id"]
    )
    decision = ledger["pm_repair_decisions"][decision_id]
    _require(
        decision["status"] == "waived",
        "authorized waiver did not reach terminal PM disposition",
    )
    _require(
        not decision.get("repair_packet_id"),
        "authorized waiver incorrectly opened a repair packet",
    )
    _require(
        ledger["route_nodes"][source_id]["late_defect_disposition"][
            "authority_ref"
        ]
        == "authority:native-user-waiver",
        "waiver authority was not preserved",
    )
    return {
        "model_action": "authorized_waiver",
        "runtime_action": "waive_with_authority",
        "authority_ref": "authority:native-user-waiver",
        "repair_packet_allowed": False,
        "terminal_disposition": True,
    }


SCENARIOS: tuple[
    tuple[str, tuple[str, ...], Callable[[], dict[str, Any]]],
    ...,
] = (
    (
        "direct_local_repair",
        (
            "unified_repair.pm_historical_direct_entry_no_blocker",
            "unified_repair.same_slot_replacement_single_authority",
            "unified_repair.decision_gate_before_effect_commit",
        ),
        _scenario_direct_local_repair,
    ),
    (
        "subtree_repair_child",
        ("unified_repair.repair_child_under_active_replacement",),
        _scenario_subtree_repair_child,
    ),
    (
        "membership_and_dependency_replay",
        (
            "unified_repair.unaffected_sibling_rebind_conservation",
            "unified_repair.affected_downstream_replay",
        ),
        _scenario_membership_and_dependency_replay,
    ),
    (
        "repeated_generation",
        ("unified_repair.repeated_lineage_generation",),
        _scenario_repeated_generation,
    ),
    (
        "terminal_worker_chain",
        (
            "unified_repair.worker_flowguard_reviewer_chain",
            "unified_repair.contract_evidence_generation",
            "unified_repair.terminal_shared_engine",
        ),
        _scenario_terminal_worker_chain,
    ),
    (
        "terminal_round_cap",
        ("unified_repair.terminal_round_cap_three",),
        _scenario_terminal_round_cap,
    ),
    (
        "completed_run_bridge",
        ("unified_repair.completed_run_distinct_current_import",),
        _scenario_completed_run_bridge,
    ),
    (
        "authorized_waiver_refinement",
        ("unified_repair.action_runtime_refinement",),
        _scenario_authorized_waiver_refinement,
    ),
)


def run_owner() -> dict[str, Any]:
    before = unified._source_fingerprints()
    scenario_rows: list[dict[str, Any]] = []
    covered: set[str] = set()
    waiver_details: dict[str, Any] = {}
    shared_engine_calls: list[dict[str, Any]] = []
    active_scenario_id = ""
    shared_engine_entrypoint = (
        "runtime._replace_scope_and_open_repair_packet"
    )
    original_shared_engine = runtime._replace_scope_and_open_repair_packet

    def observed_shared_engine(
        ledger: dict[str, Any],
        blocker: Mapping[str, Any] | None,
        decision_id: str,
        *,
        source_node_id: str,
        reason: str,
        supersede_descendants: bool = False,
        parent_repair_contract: Mapping[str, Any] | None = None,
    ) -> tuple[str, str]:
        replacement_node_id, fresh_packet_id = original_shared_engine(
            ledger,
            blocker,
            decision_id,
            source_node_id=source_node_id,
            reason=reason,
            supersede_descendants=supersede_descendants,
            parent_repair_contract=parent_repair_contract,
        )
        decision = ledger.get("pm_repair_decisions", {}).get(
            decision_id,
            {},
        )
        shared_engine_calls.append(
            {
                "scenario_id": active_scenario_id,
                "entrypoint": shared_engine_entrypoint,
                "decision_id": decision_id,
                "repair_trigger_origin": (
                    str(decision.get("repair_trigger_origin") or "")
                    if isinstance(decision, Mapping)
                    else ""
                ),
                "blocker_id": (
                    str(blocker.get("blocker_id") or "")
                    if isinstance(blocker, Mapping)
                    else ""
                ),
                "source_node_id": source_node_id,
                "replacement_node_id": replacement_node_id,
                "fresh_packet_id": fresh_packet_id,
            }
        )
        return replacement_node_id, fresh_packet_id

    runtime._replace_scope_and_open_repair_packet = observed_shared_engine
    try:
        for scenario_id, obligations, scenario in SCENARIOS:
            active_scenario_id = scenario_id
            try:
                details = scenario()
            except Exception as exc:  # direct owner preserves every native failure
                row = {
                    "scenario_id": scenario_id,
                    "status": "failed",
                    "covered_obligation_ids": list(obligations),
                    "failure_type": type(exc).__name__,
                    "failure": str(exc),
                    "details": {},
                }
            else:
                row = {
                    "scenario_id": scenario_id,
                    "status": "passed",
                    "covered_obligation_ids": list(obligations),
                    "failure_type": "",
                    "failure": "",
                    "details": details,
                }
                covered.update(obligations)
                if scenario_id == "authorized_waiver_refinement":
                    waiver_details = details
            scenario_rows.append(row)
    finally:
        runtime._replace_scope_and_open_repair_packet = original_shared_engine

    convergence_calls = [
        row
        for row in shared_engine_calls
        if row["scenario_id"]
        in {"direct_local_repair", "terminal_worker_chain"}
    ]
    convergence_by_scenario = {
        str(row["scenario_id"]): row for row in convergence_calls
    }
    midrun_trace = convergence_by_scenario.get("direct_local_repair")
    terminal_trace = convergence_by_scenario.get("terminal_worker_chain")
    convergence_ok = (
        len(convergence_calls) == 2
        and midrun_trace is not None
        and terminal_trace is not None
        and midrun_trace["entrypoint"] == shared_engine_entrypoint
        and terminal_trace["entrypoint"] == shared_engine_entrypoint
        and midrun_trace["repair_trigger_origin"]
        == "pm_historical_defect"
        and bool(terminal_trace["repair_trigger_origin"])
        and terminal_trace["repair_trigger_origin"]
        != midrun_trace["repair_trigger_origin"]
        and bool(midrun_trace["fresh_packet_id"])
        and bool(terminal_trace["fresh_packet_id"])
    )
    scenario_rows.append(
        {
            "scenario_id": (
                "midrun_terminal_shared_engine_convergence_trace"
            ),
            "status": "passed" if convergence_ok else "failed",
            "covered_obligation_ids": [
                "unified_repair.terminal_shared_engine"
            ],
            "failure_type": "" if convergence_ok else "AssertionError",
            "failure": (
                ""
                if convergence_ok
                else (
                    "mid-run and terminal traces did not enter the same "
                    "current shared repair engine"
                )
            ),
            "details": {
                "evidence_kind": "synthetic_e2e_convergence",
                "shared_engine_entrypoint": shared_engine_entrypoint,
                "trace_records": convergence_calls,
                "distinct_trigger_origins": (
                    sorted(
                        {
                            str(row["repair_trigger_origin"])
                            for row in convergence_calls
                        }
                    )
                ),
            },
        }
    )

    after = unified._source_fingerprints()
    source_stable = before == after
    required = set(unified.UNIFIED_REPAIR_OBLIGATION_IDS)
    missing_obligations = sorted(required - covered)
    input_fingerprints = unified._flatten_fingerprint_groups(
        after,
        (
            "unified_runtime_sources",
            "native_runtime_owner",
            "native_runtime_fixture",
        ),
    )
    ok = (
        source_stable
        and not missing_obligations
        and convergence_ok
        and all(row["status"] == "passed" for row in scenario_rows)
    )
    typed_runtime_evidence = []
    if waiver_details:
        typed_runtime_evidence.append(
            {
                "evidence_id": unified.WAIVER_TYPED_EVIDENCE_ID,
                "native_receipt_id": unified.REQUIRED_NATIVE_RECEIPTS[
                    CHECK_ID
                ]["receipt_id"],
                "status": "passed",
                "model_action": waiver_details["model_action"],
                "runtime_action": waiver_details["runtime_action"],
                "authority_ref_required": True,
                "terminal_disposition": waiver_details[
                    "terminal_disposition"
                ],
                "repair_packet_allowed": waiver_details[
                    "repair_packet_allowed"
                ],
                "covered_obligation_ids": [
                    "unified_repair.action_runtime_refinement"
                ],
            }
        )
    return {
        "schema_version": RESULT_SCHEMA,
        "check_id": CHECK_ID,
        "execution_owner": EXECUTION_OWNER,
        "result_status": "passed" if ok else "failed",
        "exit_code": 0 if ok else 1,
        "terminal": True,
        "current": ok,
        "immutable": True,
        "command": OWNER_COMMAND,
        "input_fingerprints": input_fingerprints,
        "source_fingerprints": after,
        "source_stable_during_execution": source_stable,
        "covered_obligation_ids": sorted(covered),
        "missing_obligation_ids": missing_obligations,
        "scenario_results": scenario_rows,
        "typed_runtime_evidence": typed_runtime_evidence,
        "claim_boundary": (
            "This artifact proves the listed direct production-runtime "
            "scenarios completed under one frozen owner. Exact ordinary tests "
            "remain owned by the separate exact-native-test owner."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=DEFAULT_RESULT_PATH,
    )
    args = parser.parse_args()
    result = run_owner()
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if result["result_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
