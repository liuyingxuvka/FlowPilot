"""Run checks for the FlowPilot PM decision-liveness model."""

from __future__ import annotations

import argparse
import ast
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_decision_liveness_model as model


ROOT = Path(__file__).resolve().parents[1]
ROUTER_PATH = ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_router.py"
RUNTIME_KIT_ROOT = ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit"
MANIFEST_PATH = RUNTIME_KIT_ROOT / "manifest.json"
CONTRACT_INDEX_PATH = RUNTIME_KIT_ROOT / "contracts" / "contract_index.json"

REQUIRED_LABELS = (
    "pm_decision_context_opened_with_always_available_work_request_channel",
    "pm_opens_advisory_role_work_request_before_final_decision",
    "pm_requests_model_miss_officer_analysis_via_generic_work_request",
    "pm_requests_evidence_before_modeling_via_generic_work_request",
    "pm_role_work_request_packet_created",
    "pm_role_work_request_packet_relayed_to_role",
    "role_work_result_returned_to_packet_ledger",
    "role_work_result_ledger_checked_before_pm_relay",
    "role_work_result_routed_to_pm_after_ledger_check",
    "pm_absorbs_role_work_result_before_dependent_decision",
    "pm_continues_decision_after_absorbing_advisory_request",
    "pm_authorizes_model_backed_repair_after_generic_officer_result",
    "pm_reopens_triage_after_absorbing_evidence_request",
    "pm_records_controlled_stop_for_user",
    "controlled_user_stop_recorded_after_pm_stop_decision",
    "decision_liveness_paused_for_user",
    "pm_records_out_of_scope_model_miss_decision",
    "repair_packet_opened_after_closed_model_miss_triage",
    "terminal_closure_after_resolved_pm_requests",
    "decision_liveness_complete",
)

HAZARD_EXPECTED_FAILURES = {
    "request_officer_decision_dead_ends_on_same_pm_event": "accepted nonterminal PM decision looped back to same PM event instead of opening next channel",
    "needs_evidence_decision_dead_ends_on_same_pm_event": "accepted nonterminal PM decision looped back to same PM event instead of opening next channel",
    "stop_for_user_decision_dead_ends_on_same_pm_event": "accepted nonterminal PM decision looped back to same PM event instead of opening next channel",
    "pm_context_without_work_request_channel": "PM decision context opened without always-available role-work-request channel",
    "pm_work_request_without_recipient": "PM work request registered without a valid recipient role",
    "pm_work_request_without_output_contract": "PM work request registered without an output contract",
    "duplicate_open_pm_work_request_id": "duplicate open PM work request id would overwrite request ledger state",
    "controller_spawned_work_without_pm_request": "Controller spawned role work without a PM work request",
    "controller_reads_pm_work_request_body": "Controller read a sealed PM work-request or result body",
    "pm_work_request_special_cased_outside_generic_channel": "PM role work was special-cased instead of using the generic request channel",
    "blocking_request_ignored_by_pm_final_decision": "PM recorded dependent final decision while blocking role work request was unresolved",
    "advisory_result_unresolved_at_terminal_closure": "terminal closure recorded with unresolved advisory role work request",
    "role_work_result_routed_without_ledger_check": "role work result routed to PM before packet-ledger check",
    "role_work_result_wrong_request_id": "role work result returned for the wrong PM request id",
    "role_work_result_wrong_role": "role work result returned from the wrong recipient role",
    "model_backed_repair_without_supporting_role_result": "model-backed repair authorized before PM reviewed supporting role work result",
    "repair_packet_opened_after_unclosed_triage": "repair packet opened before model-miss triage closed",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|holder={state.holder}|pm_ctx={state.pm_decision_context_open},"
        f"channel={state.pm_work_request_channel_available}|"
        f"decision={state.decision},{state.decision_recorded}|next={state.next_channel_opened}|"
        f"same_event={state.same_event_wait_materialized}|pm_blocker={state.pm_decision_required_blocker_written}|"
        f"request={state.request_id},{state.request_registered},{state.request_recipient_role},"
        f"{state.request_output_contract_id},{state.request_mode},{state.request_kind},"
        f"{state.request_status},generic={state.request_marked_as_generic_channel}|"
        f"packet={state.request_packet_created},{state.request_packet_relayed}|"
        f"result={state.result_returned},{state.result_request_id_matches},"
        f"{state.result_from_expected_role},{state.result_ledger_checked},"
        f"{state.result_routed_to_pm},{state.pm_absorbed_result}|"
        f"closed={state.model_miss_triage_closed}|repair={state.repair_authorized},"
        f"{state.repair_packet_opened}|final={state.dependent_pm_final_decision_recorded},"
        f"{state.controlled_user_stop_recorded},{state.terminal_closure_recorded},"
        f"supporting={state.supporting_role_result_absorbed}"
    )


def _build_reachable_graph() -> dict[str, object]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    seen: list[model.State] = [initial]
    index = {initial: 0}
    labels: set[str] = set()
    edges: list[list[tuple[str, int]]] = []
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        source_index = index[state]
        while len(edges) <= source_index:
            edges.append([])

        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})

        for transition in model.next_safe_states(state):
            labels.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(seen)
                seen.append(transition.state)
                queue.append(transition.state)
            edges[source_index].append((transition.label, index[transition.state]))

    return {
        "states": seen,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _safe_graph_report(graph: dict[str, object]) -> dict[str, object]:
    labels = set(graph["labels"])
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    states: list[model.State] = graph["states"]
    invariant_failures = graph["invariant_failures"]
    return {
        "ok": not invariant_failures
        and not missing_labels
        and any(model.is_success(state) for state in states)
        and any(state.status == "blocked" for state in states),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "labels": sorted(labels),
        "missing_labels": missing_labels,
        "complete_state_count": sum(1 for state in states if state.status == "complete"),
        "blocked_state_count": sum(1 for state in states if state.status == "blocked"),
        "invariant_failures": invariant_failures,
    }


def _check_progress(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    success = {idx for idx, state in enumerate(states) if model.is_success(state)}

    can_reach_terminal = set(terminal)
    can_reach_success = set(success)
    changed = True
    while changed:
        changed = False
        for source, outgoing in enumerate(edges):
            targets = [target for _label, target in outgoing]
            if source not in can_reach_terminal and any(
                target in can_reach_terminal for target in targets
            ):
                can_reach_terminal.add(source)
                changed = True
            if source not in can_reach_success and any(target in can_reach_success for target in targets):
                can_reach_success.add(source)
                changed = True

    stuck = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in terminal and not edges[idx]
    ]
    cannot_reach_terminal = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in can_reach_terminal
    ]

    return {
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_success,
        "initial_can_reach_success": 0 in can_reach_success,
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "cannot_reach_terminal_samples": cannot_reach_terminal[:10],
    }


def _tarjan_scc(edges: list[list[tuple[str, int]]]) -> list[list[int]]:
    index = 0
    stack: list[int] = []
    on_stack: set[int] = set()
    indices: dict[int, int] = {}
    lowlinks: dict[int, int] = {}
    components: list[list[int]] = []

    def strongconnect(node: int) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for _label, target in edges[node]:
            if target not in indices:
                strongconnect(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[target])

        if lowlinks[node] == indices[node]:
            component: list[int] = []
            while True:
                item = stack.pop()
                on_stack.remove(item)
                component.append(item)
                if item == node:
                    break
            components.append(component)

    for node in range(len(edges)):
        if node not in indices:
            strongconnect(node)
    return components


def _check_loops(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    closed_nonterminal_components: list[list[str]] = []

    for component in _tarjan_scc(edges):
        members = set(component)
        if any(model.is_terminal(states[index]) for index in members):
            continue
        has_outgoing_to_other_component = any(
            target not in members
            for index in members
            for _label, target in edges[index]
        )
        if not has_outgoing_to_other_component:
            closed_nonterminal_components.append(
                [_state_id(states[index]) for index in component[:5]]
            )

    return {
        "ok": not closed_nonterminal_components,
        "nonterminating_component_count": len(closed_nonterminal_components),
        "nonterminating_component_samples": closed_nonterminal_components[:10],
    }


def _run_flowguard_explorer() -> dict[str, object]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=lambda _input, state, _trace: model.is_terminal(state),
        success_predicate=lambda state, _trace: model.is_success(state),
        required_labels=REQUIRED_LABELS,
    ).explore()
    return {
        "ok": report.ok,
        "summary": report.summary,
        "violation_count": len(report.violations),
        "dead_branch_count": len(report.dead_branches),
        "exception_branch_count": len(report.exception_branches),
        "reachability_failure_count": len(report.reachability_failures),
        "reachability_failures": [
            failure.message for failure in report.reachability_failures
        ],
    }


def _check_hazards() -> dict[str, object]:
    results: dict[str, object] = {}
    ok = True
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in failures)
        results[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": failures,
            "state": state.__dict__,
        }
        ok = ok and detected
    return {"ok": ok, "hazards": results}


def _literal_set_assignment(source: str, name: str) -> set[str]:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            continue
        value = ast.literal_eval(node.value)
        return {str(item) for item in value}
    raise KeyError(name)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _contract_entries(contract_index: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for key in ("selection_rules", "contracts"):
        value = contract_index.get(key, [])
        if isinstance(value, list):
            entries.extend(item for item in value if isinstance(item, dict))
    return entries


def _router_static_audit() -> dict[str, object]:
    source = ROUTER_PATH.read_text(encoding="utf-8")
    manifest = _load_json(MANIFEST_PATH)
    contract_index = _load_json(CONTRACT_INDEX_PATH)

    allowed = _literal_set_assignment(source, "PM_MODEL_MISS_TRIAGE_DECISION_ALLOWED_VALUES")
    repair_authorized = _literal_set_assignment(
        source,
        "PM_MODEL_MISS_TRIAGE_REPAIR_AUTHORIZED_VALUES",
    )
    non_authorizing = sorted(allowed - repair_authorized)

    card_ids = {
        str(card.get("id"))
        for card in manifest.get("cards", [])
        if isinstance(card, dict) and card.get("id")
    }
    contract_entries = _contract_entries(contract_index)
    officer_model_miss_contracts = [
        entry
        for entry in contract_entries
        if entry.get("task_family") == "officer.model_miss_report"
    ]
    officer_model_miss_contract_declared = bool(officer_model_miss_contracts)
    generic_pm_work_request_event_declared = (
        "PM_ROLE_WORK_REQUEST_EVENT" in source
        and "pm_registers_role_work_request" in source
    )
    generic_role_work_result_event_declared = (
        "ROLE_WORK_RESULT_RETURNED_EVENT" in source
        and "role_work_result_returned" in source
    )
    generic_pm_work_absorption_event_declared = (
        "PM_ROLE_WORK_RESULT_DECISION_EVENT" in source
        and "pm_records_role_work_result_decision" in source
    )
    generic_pm_work_card_declared = "pm.role_work_request" in card_ids
    generic_pm_work_packet_relay_declared = "relay_pm_role_work_request_packet" in source
    generic_pm_work_result_relay_declared = "relay_pm_role_work_result_to_pm" in source
    generic_pm_work_request_index_declared = "pm_work_requests" in source
    model_miss_officer_uses_generic_request = (
        "request_officer_model_miss_analysis" in source
        and "model_miss_triage_followup_request" in source
        and "pm_registers_role_work_request" in source
    )
    evidence_decision_uses_generic_request = (
        "needs_evidence_before_modeling" in source
        and "model_miss_evidence_followup_request" in source
        and "pm_registers_role_work_request" in source
    )
    controlled_stop_declared = (
        "stop_for_user" in source
        and "model_miss_triage_controlled_stop" in source
    )
    non_authorizing_flag_reset_present = (
        "model_miss_triage_decision not in PM_MODEL_MISS_TRIAGE_REPAIR_AUTHORIZED_VALUES"
        in source
    )
    generic_channel_declared = all(
        (
            generic_pm_work_request_event_declared,
            generic_role_work_result_event_declared,
            generic_pm_work_absorption_event_declared,
            generic_pm_work_card_declared,
            generic_pm_work_packet_relay_declared,
            generic_pm_work_result_relay_declared,
            generic_pm_work_request_index_declared,
        )
    )

    finding_by_decision: dict[str, dict[str, object]] = {}
    for decision in sorted(allowed):
        if decision in repair_authorized:
            finding_by_decision[decision] = {
                "status": "ok",
                "reason": "repair-authorizing value closes triage only after its decision-specific payload checks pass",
            }
            continue

        missing: list[str] = []
        if decision == model.DECISION_REQUEST_OFFICER:
            if not generic_channel_declared:
                missing.append("generic PM role-work-request channel")
            if not officer_model_miss_contract_declared:
                missing.append("officer.model_miss_report output contract")
            if not model_miss_officer_uses_generic_request:
                missing.append("model-miss officer-analysis decision mapped to generic PM work request")
            if non_authorizing_flag_reset_present and not model_miss_officer_uses_generic_request:
                missing.append("non-authorizing decision resets model_miss_triage_closed and waits on the same PM event")
        elif decision == model.DECISION_NEEDS_EVIDENCE:
            if not generic_channel_declared:
                missing.append("generic PM role-work-request channel")
            if not evidence_decision_uses_generic_request:
                missing.append("evidence-gathering decision mapped to generic PM work request")
            if non_authorizing_flag_reset_present and not evidence_decision_uses_generic_request:
                missing.append("non-authorizing decision resets model_miss_triage_closed and waits on the same PM event")
        elif decision == model.DECISION_STOP_FOR_USER:
            if not controlled_stop_declared:
                missing.append("controlled user-stop or pause channel opened from model-miss triage")
            if non_authorizing_flag_reset_present and not controlled_stop_declared:
                missing.append("non-authorizing decision resets model_miss_triage_closed and waits on the same PM event")
        else:
            missing.append("declared non-authorizing decision has no classified next-channel policy")

        finding_by_decision[decision] = {
            "status": "problem" if missing else "ok",
            "missing_channels": missing,
        }

    problem_decisions = [
        decision
        for decision, finding in finding_by_decision.items()
        if finding["status"] == "problem"
    ]
    runtime_occurrences = _runtime_decision_occurrences(problem_decisions)
    return {
        "ok": not problem_decisions,
        "allowed_decision_count": len(allowed),
        "repair_authorized_decisions": sorted(repair_authorized),
        "non_authorizing_decisions": non_authorizing,
        "problem_decision_count": len(problem_decisions),
        "problem_decisions": sorted(problem_decisions),
        "finding_by_decision": finding_by_decision,
        "catalog_facts": {
            "generic_pm_work_request_event_declared": generic_pm_work_request_event_declared,
            "generic_role_work_result_event_declared": generic_role_work_result_event_declared,
            "generic_pm_work_absorption_event_declared": generic_pm_work_absorption_event_declared,
            "generic_pm_work_card_declared": generic_pm_work_card_declared,
            "generic_pm_work_packet_relay_declared": generic_pm_work_packet_relay_declared,
            "generic_pm_work_result_relay_declared": generic_pm_work_result_relay_declared,
            "generic_pm_work_request_index_declared": generic_pm_work_request_index_declared,
            "officer_model_miss_contract_declared": officer_model_miss_contract_declared,
            "model_miss_officer_uses_generic_request": model_miss_officer_uses_generic_request,
            "evidence_decision_uses_generic_request": evidence_decision_uses_generic_request,
            "controlled_stop_declared": controlled_stop_declared,
            "non_authorizing_flag_reset_present": non_authorizing_flag_reset_present,
        },
        "runtime_problem_occurrence_count": len(runtime_occurrences),
        "runtime_problem_occurrences": runtime_occurrences,
    }


def _runtime_decision_occurrences(problem_decisions: list[str]) -> list[dict[str, object]]:
    problem_set = set(problem_decisions)
    occurrences: list[dict[str, object]] = []
    for path in sorted((ROOT / ".flowpilot" / "runs").glob("*/defects/model_miss_triage/*.pm_model_miss_triage_decision.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        decision = str(payload.get("decision") or "")
        if decision not in problem_set:
            continue
        occurrences.append(
            {
                "path": str(path.relative_to(ROOT)),
                "decision": decision,
                "repair_authorized": payload.get("repair_authorized"),
                "defect_or_blocker_id": payload.get("defect_or_blocker_id"),
            }
        )
    return occurrences


def run_checks(*, json_out_requested: bool = False) -> dict[str, object]:
    graph = _build_reachable_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _check_progress(graph)
    loops = _check_loops(graph)
    explorer = _run_flowguard_explorer()
    hazards = _check_hazards()
    static_audit = _router_static_audit()
    skipped_checks = {
        "production_conformance_replay": (
            "skipped_with_reason: this check performs a static router/runtime-kit "
            "audit and model exploration, not a full external-event replay"
        )
    }
    if not json_out_requested:
        skipped_checks["default_results_file"] = (
            "skipped_with_reason: no --json-out path was provided"
        )
    return {
        "ok": bool(safe_graph["ok"])
        and bool(progress["ok"])
        and bool(loops["ok"])
        and bool(explorer["ok"])
        and bool(hazards["ok"])
        and bool(static_audit["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "loop": loops,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "router_static_audit": static_audit,
        "skipped_checks": skipped_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Optional path for writing the JSON result payload.",
    )
    args = parser.parse_args()

    result = run_checks(json_out_requested=bool(args.json_out))
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
