from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile

import pytest

from tests.flowpilot_repair_test_helpers import runtime, seeded_ledger
from flowpilot_core_runtime import run_shell
from flowpilot_user_flow_diagram_generate import generate as generate_user_flow


def _source_node_id(ledger: dict[str, object]) -> str:
    route = ledger["routes"][str(ledger["active_route_version"])]
    return str(route["node_order"][0])


def _historical_decision_body(
    ledger: dict[str, object],
    packet_id: str,
    *,
    decision: str = "repair_current_scope",
    extra: dict[str, object] | None = None,
) -> str:
    packet = ledger["packets"][packet_id]
    envelope = packet["envelope"]
    payload: dict[str, object] = {
        "decision": decision,
        "reason": f"Apply the selected {decision} topology to the observed historical defect.",
        "target_repair_trigger_id": envelope["repair_trigger_id"],
        "target_node_id": envelope["historical_source_node_id"],
        "defect_summary": envelope["historical_defect_summary"],
        "impact_summary": envelope["historical_impact_summary"],
        "next_action": decision,
    }
    payload.update(extra or {})
    return json.dumps(payload, sort_keys=True)


def _stage_historical_repair(
    ledger: dict[str, object],
    source_node_id: str,
    *,
    decision: str = "repair_current_scope",
    extra: dict[str, object] | None = None,
) -> tuple[str, str, str]:
    packet_id = runtime.ensure_pm_historical_repair_decision_packet(
        ledger,
        source_node_id,
        defect_summary="The historical node omitted a required deliverable.",
        impact_summary="The omission invalidates the node result and every derived consumer.",
        evidence_refs=["observation:historical-node-gap-001"],
    )
    lease_id = runtime.lease_agent(
        ledger,
        "pm",
        packet_id=packet_id,
    )
    runtime.assign_packet(ledger, packet_id, lease_id)
    runtime.ack_lease(ledger, lease_id, packet_id)
    result_id = runtime.submit_result(
        ledger,
        lease_id,
        packet_id,
        _historical_decision_body(ledger, packet_id, decision=decision, extra=extra),
    )
    decision_id = str(ledger["results"][result_id]["pm_repair_decision_id"])
    gate_id = str(ledger["results"][result_id]["pm_decision_gate_id"])
    return decision_id, gate_id, result_id


def _apply_gate(ledger: dict[str, object], gate_id: str) -> None:
    gate = ledger["pm_decision_gates"][gate_id]
    gate["status"] = "awaiting_system_closure"
    runtime._apply_staged_pm_decision_gate(
        ledger,
        gate,
        system_closure_id=f"system-closure:{gate_id}",
    )


def _submit_historical_immediate_decision(
    ledger: dict[str, object],
    source_node_id: str,
    *,
    decision: str,
    extra: dict[str, object] | None = None,
) -> tuple[str, str]:
    packet_id = runtime.ensure_pm_historical_repair_decision_packet(
        ledger,
        source_node_id,
        defect_summary="A completed historical node has a newly observed defect.",
        impact_summary="PM must disposition the defect without fabricating a blocker.",
        evidence_refs=["observation:late-defect-immediate"],
    )
    lease_id = runtime.lease_agent(ledger, "pm", packet_id=packet_id)
    runtime.assign_packet(ledger, packet_id, lease_id)
    runtime.ack_lease(ledger, lease_id, packet_id)
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
    return str(ledger["results"][result_id]["pm_repair_decision_id"]), result_id


def test_historical_intake_requires_evidence_and_creates_no_blocker() -> None:
    ledger, _blocker_id = seeded_ledger()
    ledger["active_blockers"] = {}
    source_node_id = _source_node_id(ledger)

    with pytest.raises(runtime.BlackBoxRuntimeError, match="non-empty evidence_refs"):
        runtime.ensure_pm_historical_repair_decision_packet(
            ledger,
            source_node_id,
            defect_summary="Observed defect.",
            impact_summary="Observed impact.",
            evidence_refs=[],
        )

    packet_id = runtime.ensure_pm_historical_repair_decision_packet(
        ledger,
        source_node_id,
        defect_summary="Observed defect.",
        impact_summary="Observed impact.",
        evidence_refs=["observation:001"],
    )
    packet = ledger["packets"][packet_id]

    assert ledger["active_blockers"] == {}
    assert packet["envelope"]["repair_trigger_origin"] == "pm_historical_defect"
    assert packet["envelope"]["repair_trigger_id"] == packet["envelope"]["subject_id"]
    assert json.loads(packet["body"])["evidence_refs"] == ["observation:001"]
    assert "repair_triggers" not in ledger


def test_historical_result_is_bound_to_exact_trigger_authority() -> None:
    ledger, _ = seeded_ledger()
    ledger["active_blockers"] = {}
    packet_id = runtime.ensure_pm_historical_repair_decision_packet(
        ledger,
        _source_node_id(ledger),
        defect_summary="Exact defect.",
        impact_summary="Exact impact.",
        evidence_refs=["observation:exact"],
    )
    packet = ledger["packets"][packet_id]
    valid = {"body": _historical_decision_body(ledger, packet_id)}

    assert runtime._pm_repair_decision_result_violation(packet, valid, ledger).ok

    wrong_payload = json.loads(valid["body"])
    wrong_payload["defect_summary"] = "Self-attested replacement text."
    wrong = runtime._pm_repair_decision_result_violation(
        packet,
        {"body": json.dumps(wrong_payload)},
        ledger,
    )
    assert not wrong.ok
    assert "trigger authority" in wrong.blocked_reason


def test_pm_repair_packet_rejects_missing_or_unknown_trigger_origin() -> None:
    ledger, _ = seeded_ledger()

    with pytest.raises(runtime.BlackBoxRuntimeError, match="explicit current repair_trigger_origin"):
        runtime.issue_task_packet(
            ledger,
            "pm",
            "Invalid repair packet.",
            "{}",
            packet_kind="pm_repair_decision",
            route_scope="pm_repair_decision",
        )
    with pytest.raises(runtime.BlackBoxRuntimeError, match="explicit current repair_trigger_origin"):
        runtime.issue_task_packet(
            ledger,
            "pm",
            "Invalid repair packet.",
            "{}",
            packet_kind="pm_repair_decision",
            route_scope="pm_repair_decision",
            repair_trigger_origin="unknown_origin",
        )


def test_repeated_repair_lineage_is_mechanically_bound_to_the_failed_attempt() -> None:
    ledger, current_blocker_id = seeded_ledger(repair_depth=1)
    current_blocker = ledger["active_blockers"].pop(current_blocker_id)
    source_packet_id = str(current_blocker["repair_target_packet_id"])
    source_packet = ledger["packets"][source_packet_id]
    original_blocker_id = "blocker-original"
    original_blocker = {
        **current_blocker,
        "blocker_id": original_blocker_id,
        "status": "retired_after_new_current_blocker",
        "route_node_id": "node-root",
        "repair_generation": 0,
        "pm_repair_packet_id": "packet-pm-original",
        "pm_repair_decision_id": "decision-pm-original",
        "repair_packet_id": source_packet_id,
    }
    ledger["active_blockers"] = {
        original_blocker_id: original_blocker,
        current_blocker_id: current_blocker,
    }
    source_packet["repair_blocker_id"] = original_blocker_id
    source_packet["envelope"]["repair_blocker_id"] = original_blocker_id

    pm_packet_id = runtime._ensure_pm_repair_decision_packet_for_blocker(
        ledger,
        current_blocker_id,
    )
    pm_packet = ledger["packets"][pm_packet_id]
    packet_body = json.loads(pm_packet["body"])
    requirement = packet_body["repeated_repair_lineage_by_decision"]["repair_current_scope"]
    branch_shape = pm_packet["envelope"]["current_handoff_contract"]["required_report_contract"][
        "branch_valid_shapes"
    ]["decision=repair_current_scope"]

    assert packet_body["repeat_context"]["repair_lineage_required"] is True
    assert packet_body["repair_decision_contract"][
        "repeated_repair_lineage_is_mechanically_required"
    ] is True
    assert branch_shape["repair_lineage"] == requirement
    assert requirement["original_blocker_id"] == original_blocker_id
    assert requirement["prior_repair_packet_id"] == source_packet_id
    assert requirement["prior_repair_result_id"] == current_blocker["target_result_id"]
    assert requirement["failed_recheck_report_id"] == current_blocker["result_id"]

    valid_payload = {
        "decision": "repair_current_scope",
        "reason": "The failed attempt needs a materially different repair.",
        "target_blocker_id": current_blocker_id,
        "next_action": "repair_current_scope",
        "repair_lineage": {
            **requirement,
            "new_repair_delta": "Replace the missing current evidence and rerun both semantic gates.",
        },
        "repair_obligation_disposition": runtime._repair_obligation_disposition_minimal_shape(
            packet_body["repair_evidence_obligations"],
            "repair_current_scope",
        ),
    }
    assert runtime._pm_repair_decision_result_violation(
        pm_packet,
        {"body": json.dumps(valid_payload)},
        ledger,
    ).ok

    mutations = {
        "missing_lineage": lambda payload: payload.pop("repair_lineage"),
        "wrong_prior_packet": lambda payload: payload["repair_lineage"].update(
            {"prior_repair_packet_id": "packet-not-the-prior-repair"}
        ),
        "wrong_prior_result": lambda payload: payload["repair_lineage"].update(
            {"prior_repair_result_id": current_blocker["result_id"]}
        ),
        "missing_prior_evidence": lambda payload: payload["repair_lineage"].update(
            {"prior_repair_evidence_refs": [current_blocker["result_id"]]}
        ),
        "empty_new_delta": lambda payload: payload["repair_lineage"].update(
            {"new_repair_delta": ""}
        ),
        "wrong_return_gate": lambda payload: payload["repair_lineage"].update(
            {"return_gate": "reviewer_only"}
        ),
    }
    for mutation in mutations.values():
        invalid_payload = json.loads(json.dumps(valid_payload))
        mutation(invalid_payload)
        violation = runtime._pm_repair_decision_result_violation(
            pm_packet,
            {"body": json.dumps(invalid_payload)},
            ledger,
        )
        assert not violation.ok
        assert "repair_lineage" in (
            violation.blocked_reason
            + " "
            + " ".join(violation.missing_required_fields)
        )


def test_staged_historical_repair_has_no_early_effect_then_commits_same_slot() -> None:
    ledger, _ = seeded_ledger()
    ledger["active_blockers"] = {}
    source_node_id = _source_node_id(ledger)
    old_route_version = ledger["active_route_version"]
    decision_id, gate_id, _ = _stage_historical_repair(ledger, source_node_id)
    gate = ledger["pm_decision_gates"][gate_id]

    assert ledger["active_route_version"] == old_route_version
    assert ledger["route_nodes"][source_node_id]["status"] != "superseded"
    assert decision_id not in ledger["repair_transactions"]
    assert gate["staged_effect"]["status"] == "pending"
    assert ledger["terminal_supplemental_repair"]["current_round"] == 0

    _apply_gate(ledger, gate_id)

    transaction = ledger["repair_transactions"][decision_id]
    replacement_id = transaction["replacement_node_id"]
    replacement = ledger["route_nodes"][replacement_id]
    worker_packet = ledger["packets"][transaction["fresh_packet_id"]]
    route = ledger["routes"][str(ledger["active_route_version"])]

    assert ledger["route_nodes"][source_node_id]["status"] == "superseded"
    assert ledger["route_nodes"][source_node_id]["superseded_by"] == replacement_id
    assert replacement["repair_of_node_id"] == source_node_id
    assert replacement["repair_root_id"] == source_node_id
    assert replacement["previous_repair_node_id"] == ""
    assert replacement["repair_generation"] == 1
    assert route["node_order"] == route["current_mainline"]
    assert replacement_id in route["node_order"]
    assert source_node_id not in route["node_order"]
    assert gate["staged_effect"]["committed_at"] < replacement["created_at"]
    assert gate["staged_effect"]["committed_at"] < worker_packet["created_at"]
    assert worker_packet["envelope"]["repair_transaction_id"] == decision_id
    assert worker_packet["envelope"]["repair_trigger_origin"] == "pm_historical_defect"
    assert worker_packet["envelope"]["repair_root_id"] == source_node_id


def test_terminal_replacement_projects_committed_supplemental_contract_without_preseeding_source() -> None:
    ledger, _ = seeded_ledger()
    source_node_id = _source_node_id(ledger)
    contract_id = "terminal-contract-projection-r1"
    repair_item_id = "terminal-item-projection-r1"
    decision_id = "decision-terminal-projection-r1"
    timestamp = runtime.now_iso()
    assert "supplemental_repair_contract_ids" not in ledger["route_nodes"][source_node_id]
    assert "supplemental_repair_item_ids" not in ledger["route_nodes"][source_node_id]

    ledger["supplemental_repair_contracts"][contract_id] = {
        "schema_version": "flowpilot.terminal_supplemental_repair_contract.v1",
        "contract_id": contract_id,
        "status": "active",
        "repair_generation": 1,
        "source_generation": ledger["source_generation"],
        "created_at": timestamp,
        "committed_at": timestamp,
        "repair_items": [
            {
                "repair_item_id": repair_item_id,
                "owner_repair_node_id": source_node_id,
            }
        ],
    }
    ledger["pm_repair_decisions"][decision_id] = {
        "decision_id": decision_id,
        "repair_generation": 1,
        "source_generation": ledger["source_generation"],
        "supplemental_repair_contract_id": contract_id,
    }

    replacement_id = runtime._replace_route_node_for_repair(
        ledger,
        source_node_id,
        disposition_id=decision_id,
        reason="Commit the terminal supplemental repair replacement.",
    )
    replacement = ledger["route_nodes"][replacement_id]

    assert replacement["supplemental_repair_contract_ids"] == [contract_id]
    assert replacement["supplemental_repair_item_ids"] == [repair_item_id]
    assert ledger["route_nodes"][source_node_id]["status"] == "superseded"


def test_runtime_replacement_identity_materializes_into_on_demand_ui_history() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        shell = run_shell.create_run_shell(
            root,
            "Repair the current route.",
            "Only the active replacement may remain authoritative.",
            run_id="run-runtime-ui-repair",
        )
        ledger, _ = seeded_ledger()
        ledger["active_blockers"] = {}
        ledger["run_id"] = shell.run_id
        ledger["run_root"] = str(shell.run_root)
        source_node_id = _source_node_id(ledger)
        _decision_id, gate_id, _result_id = _stage_historical_repair(
            ledger,
            source_node_id,
        )
        _apply_gate(ledger, gate_id)
        mutation = ledger["route_mutations"][-1]
        replacement_node_id = str(mutation["replacement_node_id"])

        run_shell.save_run_ledger(shell, ledger)
        route_id = str(ledger["routes"][str(ledger["active_route_version"])]["route_id"])
        route_path = shell.run_root / "routes" / route_id / "flow.json"
        route_projection = json.loads(route_path.read_text(encoding="utf-8"))
        projected_by_id = {
            str(node["node_id"]): node
            for node in route_projection["nodes"]
        }

        assert route_projection["producer_authority"] == "canonical_run_ledger"
        assert projected_by_id[source_node_id]["status"] == "superseded"
        assert projected_by_id[source_node_id]["superseded_by"] == replacement_node_id
        assert projected_by_id[replacement_node_id]["repair_of_node_id"] == source_node_id
        assert projected_by_id[replacement_node_id]["repair_root_id"] == source_node_id
        assert route_projection["current_mainline"] == [replacement_node_id]

        default_payload = generate_user_flow(
            root,
            write=False,
            trigger="major_node_entry",
            cockpit_open=False,
            display_surface="chat",
            mark_chat_displayed=False,
            mark_ui_displayed=False,
            reviewer_check=False,
        )
        history_payload = generate_user_flow(
            root,
            write=False,
            trigger="major_node_entry",
            cockpit_open=False,
            display_surface="chat",
            mark_chat_displayed=False,
            mark_ui_displayed=False,
            reviewer_check=False,
            include_superseded_history=True,
        )

        assert default_payload["route_source_kind"] == "flow_json"
        assert default_payload["source_route_path"] == str(route_path)
        assert default_payload["replacement_history"]["producer_identity_status"] == "complete"
        assert default_payload["replacement_history"]["current_authority_node_ids"] == [
            replacement_node_id
        ]
        assert default_payload["replacement_history"]["rendered_visible"] is False
        assert "history only" not in default_payload["mermaid"]
        assert history_payload["replacement_history"]["rendered_visible"] is True
        assert "history only; repaired by" in history_payload["mermaid"]

        projected_by_id[replacement_node_id]["repair_root_id"] = ""
        route_projection["nodes"] = list(projected_by_id.values())
        route_path.write_text(
            json.dumps(route_projection, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        tampered_payload = generate_user_flow(
            root,
            write=False,
            trigger="major_node_entry",
            cockpit_open=False,
            display_surface="chat",
            mark_chat_displayed=True,
            mark_ui_displayed=False,
            reviewer_check=True,
            include_superseded_history=True,
        )
        assert tampered_payload["replacement_history"]["producer_identity_status"] == "incomplete"
        assert tampered_payload["replacement_history"]["rendered_visible"] is False
        assert tampered_payload["review"]["status"] == "blocked"


def test_repeated_repair_targets_latest_generation_and_keeps_stable_root() -> None:
    ledger, _ = seeded_ledger()
    ledger["active_blockers"] = {}
    root_id = _source_node_id(ledger)

    first_decision, first_gate, _ = _stage_historical_repair(ledger, root_id)
    _apply_gate(ledger, first_gate)
    first_replacement = ledger["repair_transactions"][first_decision]["replacement_node_id"]

    second_decision, second_gate, _ = _stage_historical_repair(ledger, root_id)
    _apply_gate(ledger, second_gate)
    second_replacement = ledger["repair_transactions"][second_decision]["replacement_node_id"]
    second = ledger["route_nodes"][second_replacement]

    assert ledger["route_nodes"][first_replacement]["status"] == "superseded"
    assert ledger["route_nodes"][first_replacement]["superseded_by"] == second_replacement
    assert second["repair_of_node_id"] == first_replacement
    assert second["previous_repair_node_id"] == first_replacement
    assert second["repair_root_id"] == root_id
    assert second["repair_generation"] == 2
    assert ledger["routes"][str(ledger["active_route_version"])]["node_order"] == [second_replacement]


def test_route_repair_rebinds_unaffected_siblings_into_new_effective_route() -> None:
    ledger, _ = seeded_ledger()
    ledger["active_blockers"] = {}
    source_id = _source_node_id(ledger)
    parent_id = "parent-scope"
    sibling_ids = ["sibling-a", "sibling-b"]
    ledger["route_nodes"][source_id]["parent_node_id"] = parent_id
    ledger["route_nodes"][parent_id] = {
        "node_id": parent_id,
        "route_version": 1,
        "title": "Parent",
        "node_kind": "module",
        "parent_node_id": "",
        "child_node_ids": [source_id, *sibling_ids],
        "status": "awaiting_children",
        "repair_generation": 0,
        "accepted_result_id": "",
    }
    for sibling_id in sibling_ids:
        ledger["route_nodes"][sibling_id] = {
            "node_id": sibling_id,
            "route_version": 1,
            "title": sibling_id,
            "node_kind": "leaf",
            "parent_node_id": parent_id,
            "child_node_ids": [],
            "status": "accepted",
            "repair_generation": 0,
            "accepted_result_id": f"result:{sibling_id}",
        }
    ledger["routes"]["1"]["node_order"] = [parent_id, source_id, *sibling_ids]

    decision_id, gate_id, _ = _stage_historical_repair(ledger, source_id)
    _apply_gate(ledger, gate_id)
    replacement_id = ledger["repair_transactions"][decision_id]["replacement_node_id"]
    active_version = ledger["active_route_version"]
    route = ledger["routes"][str(active_version)]
    effective_ids = [row["node_id"] for row in runtime._active_route_node_records(ledger)]

    assert route["node_order"] == [parent_id, replacement_id, *sibling_ids]
    assert ledger["route_nodes"][parent_id]["child_node_ids"] == [replacement_id, *sibling_ids]
    for node_id in [parent_id, *sibling_ids]:
        assert ledger["route_nodes"][node_id]["route_version"] == active_version
        assert ledger["route_nodes"][node_id]["accepted_result_id"] == (
            "" if node_id == parent_id else f"result:{node_id}"
        )
    assert effective_ids == route["node_order"]
    mutation = ledger["route_mutations"][-1]
    assert mutation["affected_dependency_node_ids"] == [parent_id]
    assert mutation["unaffected_rebound_ids"] == sibling_ids
    assert mutation["before_effective_member_ids"] == [
        parent_id,
        source_id,
        *sibling_ids,
    ]
    assert mutation["after_effective_member_ids"] == [
        parent_id,
        replacement_id,
        *sibling_ids,
    ]
    assert ledger["route_nodes"][parent_id]["repair_dependency_replay"]["status"] == "required"


def test_route_repair_final_ledger_and_terminal_targets_match_effective_members() -> None:
    ledger, _ = seeded_ledger()
    ledger["active_blockers"] = {}
    source_id = _source_node_id(ledger)
    sibling_id = "retained-sibling"
    ledger["route_nodes"][sibling_id] = {
        "node_id": sibling_id,
        "route_version": 1,
        "title": "Retained sibling",
        "node_kind": "leaf",
        "parent_node_id": "",
        "child_node_ids": [],
        "status": "accepted",
        "repair_generation": 0,
        "accepted_result_id": "result:retained-sibling",
    }
    ledger["routes"]["1"]["node_order"] = [source_id, sibling_id]

    decision_id, gate_id, _ = _stage_historical_repair(ledger, source_id)
    _apply_gate(ledger, gate_id)
    replacement_id = ledger["repair_transactions"][decision_id][
        "replacement_node_id"
    ]
    final_ledger = runtime.build_final_route_wide_gate_ledger(ledger)
    terminal_target_ids = [
        str(target["segment_id"])
        for target in runtime._terminal_backward_replay_segment_targets(ledger)
        if target["segment_kind"] == "route_node"
    ]

    assert final_ledger["effective_node_ids"] == [replacement_id, sibling_id]
    assert terminal_target_ids == final_ledger["effective_node_ids"]
    assert ledger["route_mutations"][-1]["after_effective_member_ids"] == (
        final_ledger["effective_node_ids"]
    )


def test_nested_dependency_cone_invalidates_only_ancestors_and_preserves_parallel_siblings() -> None:
    ledger, _ = seeded_ledger()
    ledger["active_blockers"] = {}
    source_id = _source_node_id(ledger)
    middle_id = "middle-parent"
    root_id = "root-parent"
    sibling_id = "parallel-sibling"
    ledger["route_nodes"][source_id]["parent_node_id"] = middle_id
    ledger["route_nodes"][middle_id] = {
        "node_id": middle_id,
        "route_version": 1,
        "title": "Middle parent",
        "node_kind": "module",
        "parent_node_id": root_id,
        "child_node_ids": [source_id],
        "status": "accepted",
        "repair_generation": 0,
        "accepted_result_id": "result:middle",
        "parent_backward_replay_id": "parent-replay:middle",
        "pm_disposition_id": "pm:middle",
        "validation_evidence_ids": ["validation:middle"],
    }
    ledger["route_nodes"][root_id] = {
        "node_id": root_id,
        "route_version": 1,
        "title": "Root parent",
        "node_kind": "module",
        "parent_node_id": "",
        "child_node_ids": [middle_id, sibling_id],
        "status": "accepted",
        "repair_generation": 0,
        "accepted_result_id": "result:root",
        "parent_backward_replay_id": "parent-replay:root",
        "pm_disposition_id": "pm:root",
        "validation_evidence_ids": ["validation:root"],
    }
    ledger["route_nodes"][sibling_id] = {
        "node_id": sibling_id,
        "route_version": 1,
        "title": "Parallel sibling",
        "node_kind": "leaf",
        "parent_node_id": root_id,
        "child_node_ids": [],
        "status": "accepted",
        "repair_generation": 0,
        "accepted_result_id": "result:sibling",
    }
    ledger["routes"]["1"]["node_order"] = [root_id, middle_id, source_id, sibling_id]
    ledger["execution_frontier"]["completed_nodes"] = [
        root_id,
        middle_id,
        source_id,
        sibling_id,
    ]
    ledger["closure_confirmed_by_backward_replay"] = True
    ledger["terminal_backward_replay_id"] = "terminal:old"

    decision_id, gate_id, _ = _stage_historical_repair(ledger, source_id)
    _apply_gate(ledger, gate_id)
    mutation = ledger["route_mutations"][-1]
    replacement_id = ledger["repair_transactions"][decision_id]["replacement_node_id"]

    assert mutation["affected_dependency_node_ids"] == [middle_id, root_id]
    assert mutation["unaffected_rebound_ids"] == [sibling_id]
    assert ledger["route_nodes"][middle_id]["child_node_ids"] == [replacement_id]
    assert ledger["route_nodes"][root_id]["child_node_ids"] == [middle_id, sibling_id]
    for affected_id in (middle_id, root_id):
        affected = ledger["route_nodes"][affected_id]
        assert affected["status"] == "awaiting_children"
        assert affected["accepted_result_id"] == ""
        assert affected["parent_backward_replay_id"] == ""
        assert affected["pm_disposition_id"] == ""
        assert affected["validation_evidence_ids"] == []
        assert affected["repair_dependency_replay"]["status"] == "required"
    assert ledger["route_nodes"][sibling_id]["accepted_result_id"] == "result:sibling"
    assert ledger["execution_frontier"]["completed_nodes"] == [sibling_id]
    assert ledger["closure_confirmed_by_backward_replay"] is False
    assert ledger["terminal_backward_replay_id"] == ""


@pytest.mark.parametrize("topology_error", ["missing_parent", "cycle"])
def test_dependency_cone_fails_closed_for_unknown_or_cyclic_topology(
    topology_error: str,
) -> None:
    ledger, _ = seeded_ledger()
    ledger["active_blockers"] = {}
    source_id = _source_node_id(ledger)
    if topology_error == "missing_parent":
        ledger["route_nodes"][source_id]["parent_node_id"] = "missing-parent"
    else:
        parent_id = "cycle-parent"
        ledger["route_nodes"][source_id]["parent_node_id"] = parent_id
        ledger["route_nodes"][source_id]["child_node_ids"] = [parent_id]
        ledger["route_nodes"][parent_id] = {
            "node_id": parent_id,
            "route_version": 1,
            "title": "Cycle parent",
            "node_kind": "module",
            "parent_node_id": source_id,
            "child_node_ids": [source_id],
            "status": "accepted",
            "repair_generation": 0,
        }
        ledger["routes"]["1"]["node_order"] = [parent_id, source_id]

    _decision_id, gate_id, _ = _stage_historical_repair(ledger, source_id)
    with pytest.raises(runtime.BlackBoxRuntimeError, match="repair dependency topology"):
        _apply_gate(ledger, gate_id)

    assert ledger["active_route_version"] == 1
    assert ledger["route_nodes"][source_id]["status"] != "superseded"
    assert ledger["pm_decision_gates"][gate_id]["status"] == "apply_failed"
    assert ledger["pm_decision_gates"][gate_id]["staged_effect"]["status"] == "disposed"


def test_structured_subtree_places_repair_children_under_active_replacement() -> None:
    ledger, _ = seeded_ledger()
    ledger["active_blockers"] = {}
    source_id = _source_node_id(ledger)
    subtree_scope = {
        "source_node_id": source_id,
        "include_descendants": True,
        "preserve_unaffected_siblings": True,
        "replay_policy": "derived_dependency_cone",
        "repair_child_specs": [
            {
                "node_id": "repair-child-a",
                "purpose": "Repair the bounded omitted deliverable.",
                "required_evidence": ["fresh_worker_result", "fresh_validation_evidence"],
            }
        ],
    }
    decision_id, gate_id, _ = _stage_historical_repair(
        ledger,
        source_id,
        decision="repair_subtree",
        extra={"repair_subtree_scope": subtree_scope},
    )
    _apply_gate(ledger, gate_id)

    replacement_id = ledger["repair_transactions"][decision_id]["replacement_node_id"]
    replacement = ledger["route_nodes"][replacement_id]
    child = ledger["route_nodes"]["repair-child-a"]

    assert replacement["status"] != "superseded"
    assert replacement["node_kind"] == "module"
    assert replacement["child_node_ids"] == ["repair-child-a"]
    assert child["parent_node_id"] == replacement_id
    assert child["status"] == "running"
    assert child["parent_node_id"] != source_id


def test_apply_preflight_failure_disposes_effect_and_leaves_no_partial_repair() -> None:
    ledger, _ = seeded_ledger()
    ledger["active_blockers"] = {}
    source_id = _source_node_id(ledger)
    decision_id, gate_id, _ = _stage_historical_repair(ledger, source_id)
    route_version = ledger["active_route_version"]
    packet_ids = set(ledger["packets"])
    ledger["pm_repair_decisions"][decision_id]["target_node_id"] = "missing-node"

    with pytest.raises(runtime.BlackBoxRuntimeError, match="missing route node"):
        _apply_gate(ledger, gate_id)

    gate = ledger["pm_decision_gates"][gate_id]
    assert gate["status"] == "apply_failed"
    assert gate["staged_effect"]["status"] == "disposed"
    assert ledger["active_route_version"] == route_version
    assert ledger["route_nodes"][source_id]["status"] != "superseded"
    assert set(ledger["packets"]) == packet_ids
    assert decision_id not in ledger["repair_transactions"]
    assert ledger["terminal_supplemental_repair"]["current_round"] == 0
    assert not ledger["supplemental_repair_contracts"]


def test_historical_parent_repair_replaces_parent_and_materializes_current_children() -> None:
    ledger, _ = seeded_ledger()
    ledger["active_blockers"] = {}
    source_id = _source_node_id(ledger)
    parent_id = "historical-parent"
    ledger["route_nodes"][source_id]["parent_node_id"] = parent_id
    ledger["route_nodes"][parent_id] = {
        "node_id": parent_id,
        "route_version": 1,
        "title": "Historical parent",
        "node_kind": "module",
        "parent_node_id": "",
        "child_node_ids": [source_id],
        "status": "accepted",
        "repair_generation": 0,
        "acceptance_criteria": ["Parent outcome is complete."],
    }
    ledger["routes"]["1"]["node_order"] = [parent_id, source_id]
    parent_contract = {
        "schema_version": "flowpilot.parent_repair_scope_contract.v1",
        "source_parent_node_id": parent_id,
        "inherit_existing_children": True,
        "repair_child_specs": [
            {
                "node_id": "parent-repair-child",
                "title": "Repair parent child",
                "purpose": "Rebuild the bounded parent outcome.",
                "required_evidence": ["fresh parent repair evidence"],
                "acceptance_criteria": ["Fresh child evidence composes into the parent."],
            }
        ],
    }

    decision_id, gate_id, _ = _stage_historical_repair(
        ledger,
        source_id,
        decision="repair_parent_scope",
        extra={"repair_parent_scope_contract": parent_contract},
    )
    _apply_gate(ledger, gate_id)
    transaction = ledger["repair_transactions"][decision_id]
    replacement_id = transaction["replacement_node_id"]
    replacement = ledger["route_nodes"][replacement_id]

    assert ledger["route_nodes"][parent_id]["status"] == "superseded"
    assert replacement["repair_of_node_id"] == parent_id
    assert replacement["child_node_ids"] == ["parent-repair-child"]
    assert ledger["route_nodes"]["parent-repair-child"]["parent_node_id"] == replacement_id
    assert source_id in replacement["inherited_child_node_ids"]
    assert source_id not in ledger["routes"][str(ledger["active_route_version"])]["node_order"]


def test_historical_route_redesign_uses_the_shared_staged_transaction() -> None:
    ledger, _ = seeded_ledger()
    ledger["active_blockers"] = {}
    source_id = _source_node_id(ledger)
    route_plan = runtime.packet_result_contracts.strict_route_plan_minimal_shape()

    decision_id, gate_id, _ = _stage_historical_repair(
        ledger,
        source_id,
        decision="redesign_route",
        extra={"route_plan": route_plan},
    )
    _apply_gate(ledger, gate_id)

    decision = ledger["pm_repair_decisions"][decision_id]
    assert decision["status"] == "repair_packet_open"
    assert decision["repair_packet_id"]
    assert ledger["repair_transactions"][decision_id]["decision"] == "redesign_route"
    assert ledger["active_route_version"] == 2
    assert ledger["active_blockers"] == {}


def test_historical_waiver_and_stop_are_packet_free_explicit_pm_dispositions() -> None:
    waiver_ledger, _ = seeded_ledger()
    waiver_ledger["active_blockers"] = {}
    waiver_source_id = _source_node_id(waiver_ledger)
    waiver_decision_id, _ = _submit_historical_immediate_decision(
        waiver_ledger,
        waiver_source_id,
        decision="waive_with_authority",
        extra={"authority_ref": "authority:explicit-user-acceptance"},
    )

    waiver_decision = waiver_ledger["pm_repair_decisions"][waiver_decision_id]
    assert waiver_decision["status"] == "waived"
    assert waiver_ledger["route_nodes"][waiver_source_id]["late_defect_disposition"][
        "authority_ref"
    ] == "authority:explicit-user-acceptance"
    assert waiver_ledger["active_blockers"] == {}
    assert not any(
        packet["status"] == "open"
        and packet["envelope"]["packet_kind"] != "pm_repair_decision"
        for packet in waiver_ledger["packets"].values()
    )

    stop_ledger, _ = seeded_ledger()
    stop_ledger["active_blockers"] = {}
    stop_source_id = _source_node_id(stop_ledger)
    stop_decision_id, _ = _submit_historical_immediate_decision(
        stop_ledger,
        stop_source_id,
        decision="stop_for_user",
    )

    assert stop_ledger["pm_repair_decisions"][stop_decision_id]["status"] == "stopped"
    assert stop_ledger["terminal_lifecycle"]["status"] == "stopped_by_user"
    assert stop_ledger["terminal_lifecycle"]["actor"] == "pm"
    assert stop_ledger["route_nodes"][stop_source_id]["late_defect_disposition"][
        "decision"
    ] == "stop_for_user"
    assert stop_ledger["active_blockers"] == {}


def test_completed_run_repair_creates_distinct_current_run_with_read_only_imports() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        old_shell = run_shell.create_run_shell(
            root,
            "Original goal",
            "Original acceptance contract",
            run_id="run-old-complete",
        )
        shell_runtime = run_shell.runtime
        old_ledger = run_shell.load_run_ledger(old_shell)
        old_ledger["startup_intake"] = {
            "status": "confirmed",
            "current_run_authority": True,
            "controller_may_read_body": False,
            "body_text_included": False,
            "startup_answers": {"background_collaboration_authorized": True},
        }
        shell_runtime.create_route(old_ledger, "Original route", ["Deliver output"])
        packet_id = shell_runtime.issue_task_packet(
            old_ledger,
            "worker",
            "Deliver original output",
            json.dumps({"schema_version": "test.original.v1", "instruction": "deliver"}),
        )
        result_id = "result-original-accepted"
        result_body = "Original accepted output body."
        old_ledger["results"][result_id] = {
            "result_id": result_id,
            "packet_id": packet_id,
            "producer_lease_id": "lease-original",
            "producer_agent_id": "worker-original",
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
                "evidence_ids": ["evidence:original"],
                "evidence_generation": old_ledger["source_generation"],
                "body_hash": shell_runtime.hash_text(result_body),
                "body_visibility": "sealed",
                "referenced_packet_body_hash": old_ledger["packets"][packet_id]["envelope"][
                    "body_hash"
                ],
                "output_contract": old_ledger["packets"][packet_id]["envelope"][
                    "output_contract"
                ],
                "ack_result_accepted_separate": True,
            },
            "body": result_body,
            "review_id": "review-original",
            "accepted": True,
            "created_at": shell_runtime.now_iso(),
        }
        old_ledger["packets"][packet_id]["result_ids"] = [result_id]
        old_ledger["packets"][packet_id]["accepted_result_id"] = result_id
        old_ledger["packets"][packet_id]["status"] = "accepted"
        old_ledger["closure"] = {
            "decision": "complete",
            "blockers": [],
            "created_at": shell_runtime.now_iso(),
        }
        run_shell.save_run_ledger(old_shell, old_ledger)
        old_ledger_bytes = old_shell.ledger_path.read_bytes()
        old_ledger_hash = hashlib.sha256(old_ledger_bytes).hexdigest()

        new_shell = run_shell.create_historical_repair_run_shell(
            root,
            source_run_id=old_shell.run_id,
            defect_summary="The accepted output omitted a required late-discovered detail.",
            impact_summary="The new run must repair and revalidate that bounded output.",
            evidence_refs=["observation:post-run-defect"],
            source_result_ids=[result_id],
            run_id="run-new-repair",
        )
        new_ledger = run_shell.load_run_ledger(new_shell)

        assert new_shell.run_id == "run-new-repair"
        assert new_shell.run_id != old_shell.run_id
        assert new_ledger["historical_repair_intake"]["source_run_id"] == old_shell.run_id
        assert new_ledger["historical_repair_intake"]["old_control_state_reactivated"] is False
        assert new_ledger["historical_repair_intake"]["status"] == "awaiting_current_pm_route"
        assert new_ledger["routes"] == {}
        assert new_ledger["packets"] == {}
        imported_id = new_ledger["historical_repair_intake"]["imported_evidence_ids"][0]
        imported = new_ledger["imported_evidence"][imported_id]
        assert imported["source_result_id"] == result_id
        assert imported["disposition"] == "imported_read_only"
        assert imported["read_only"] is True
        assert imported["current_authority"] is False
        assert hashlib.sha256(old_shell.ledger_path.read_bytes()).hexdigest() == old_ledger_hash
        assert json.loads((root / ".flowpilot" / "current.json").read_text(encoding="utf-8"))[
            "run_id"
        ] == new_shell.run_id

        with pytest.raises(
            shell_runtime.BlackBoxRuntimeError,
            match="distinct new run_id",
        ):
            run_shell.create_historical_repair_run_shell(
                root,
                source_run_id=old_shell.run_id,
                defect_summary="Defect",
                impact_summary="Impact",
                evidence_refs=["observation:same-run"],
                source_result_ids=[result_id],
                run_id=old_shell.run_id,
            )
