from __future__ import annotations

import copy
import json

from tests.flowpilot_current_authority_test_helpers import raw_current_authority_references
from tests.flowpilot_repair_test_helpers import runtime, seeded_ledger


def test_pm_repair_packet_receives_repair_dossier_context_and_reads() -> None:
    ledger, blocker_id = seeded_ledger(blocker_class="evidence_gap")

    pm_packet_id = runtime._ensure_pm_repair_decision_packet_for_blocker(ledger, blocker_id)
    packet = ledger["packets"][pm_packet_id]
    body = json.loads(packet["body"])
    reads = packet["envelope"].get("authorized_result_reads", [])

    assert body["repair_dossier_context"]["active_blocker_id"] == blocker_id
    assert body["repair_dossier_context"]["hard_next_action"] == "pm_repair_decision"
    assert body["repair_dossier_context"]["context_only_result_ids"]
    assert {row["purpose"] for row in reads}
    assert any("repair_dossier_context" in row["purpose"] for row in reads)


def test_repair_node_worker_packet_inherits_dossier_from_node_not_first_packet_only() -> None:
    ledger, blocker_id = seeded_ledger(blocker_class="evidence_gap")
    runtime._bind_route_node_repair_dossier_identity(
        ledger,
        ledger["execution_frontier"]["active_node_id"],
        blocker_id,
    )
    worker_packet_id = runtime.ensure_next_node_task_packet(ledger)
    worker_packet = ledger["packets"][worker_packet_id]
    body = json.loads(worker_packet["body"])

    assert worker_packet["repair_blocker_id"] == blocker_id
    assert body["repair_dossier_context"]["active_blocker_id"] == blocker_id
    assert worker_packet["envelope"]["authorized_result_reads"]


def test_normal_non_repair_packet_does_not_gain_parent_wide_authorization() -> None:
    ledger, _blocker_id = seeded_ledger(blocker_class="evidence_gap")
    normal_packet_id = runtime.issue_task_packet(
        ledger,
        "worker",
        "Normal non-repair packet",
        json.dumps({"schema_version": "test.normal.v1"}, sort_keys=True),
        route_node_id="node-normal",
        route_scope="node",
        required_flowguard_target="development_process",
    )
    normal_packet = ledger["packets"][normal_packet_id]
    body = json.loads(normal_packet["body"])

    assert "repair_dossier_context" not in body
    assert "authorized_result_reads" not in normal_packet["envelope"]


def test_repair_dossier_does_not_override_node_acceptance_plan_review_window() -> None:
    ledger, blocker_id = seeded_ledger(blocker_class="evidence_gap")
    node_id = ledger["active_blockers"][blocker_id]["route_node_id"]
    runtime._bind_route_node_repair_dossier_identity(ledger, node_id, blocker_id)

    packet_id = runtime.ensure_node_acceptance_plan_packet(ledger, node_id)
    lease_id = runtime.lease_agent(ledger, "pm", agent_id="pm-node-plan", packet_id=packet_id)
    runtime.assign_packet(ledger, packet_id, lease_id)
    runtime.ack_lease(ledger, lease_id, packet_id)
    runtime.open_authorized_input_materials_for_role(ledger, packet_id, lease_id)
    package = copy.deepcopy(
        runtime.packet_result_contracts.minimal_valid_shape_for_family("task.node_acceptance_plan")[
            "node_context_package"
        ]
    )
    package.update(
        {
            "node_id": node_id,
            "purpose": "Provide current starting context for the repair node.",
            "acceptance_criteria": ["Produce current evidence."],
            "relevant_references": raw_current_authority_references(
                ledger,
                include_repair=True,
                fixture_id=f"repair-dossier-{node_id}",
            ),
            "known_risks": ["worker evidence still belongs to result stage"],
            "acceptance_item_projection": [],
        }
    )

    runtime.submit_result(
        ledger,
        lease_id,
        packet_id,
        json.dumps({"decision": "pass", "node_context_package": package}, sort_keys=True),
    )

    review_packets = [
        packet
        for packet in ledger["packets"].values()
        if packet["envelope"]["packet_kind"] == "review"
        and packet["envelope"]["subject_id"] == packet_id
    ]
    assert len(review_packets) == 1
    review_packet = review_packets[0]
    review_body = json.loads(review_packet["body"])
    review_window = review_packet["envelope"]["review_window"]
    dossier_context = review_body["repair_dossier_context"]

    assert dossier_context["active_blocker_id"] == blocker_id
    assert "does not define the current subject deliverable" in dossier_context["current_evidence_rule"]
    assert review_window["subject_result_family_id"] == "task.node_acceptance_plan"
    assert review_window["subject_lifecycle_stage"] == "node_plan_definition"
    assert review_window["required_current_fields"] == ["decision", "node_context_package"]
    assert "current_evidence_refs" not in review_window["required_current_fields"]
    assert "worker_result_artifacts" in review_window["forbidden_future_stage_classes"]
    assert not review_body["flowguard_evidence_manifest"]["matching_flowguard_result_reads_required"]
