"""Run checks for the FlowPilot repair transaction model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_repair_transaction_model as model


REQUIRED_LABELS = (
    "reviewer_blocker_detected",
    "router_registers_blocker_with_origin_and_failure_events",
    "pm_records_repair_decision_without_resolving_blocker",
    "router_opens_repair_transaction",
    "pm_writes_reissue_spec_inside_transaction",
    "router_atomically_commits_reissue_generation_and_outcome_table",
    "reviewer_recheck_requested_after_committed_generation",
    "reviewer_recheck_allows_dispatch",
    "reviewer_recheck_returns_followup_blocker",
    "reviewer_recheck_returns_protocol_blocker",
    "router_refreshes_visible_authorities_after_recheck",
)


HAZARD_EXPECTED_FAILURES = {
    "blocker_registered_without_nonterminal_events": "router blocker registration lacked origin or nonterminal repair events",
    "pm_decision_self_resolves_blocker": "PM repair decision resolved the blocker by itself",
    "reissue_spec_outside_transaction": "PM repair wrote replacement artifacts outside a repair transaction",
    "transaction_commits_packet_files_without_ledger": "repair transaction committed without packet files, ledger, dispatch index, router table, or atomic publication",
    "transaction_commits_ledger_without_dispatch_index": "repair transaction committed without packet files, ledger, dispatch index, router table, or atomic publication",
    "transaction_commits_without_router_outcome_table": "repair transaction committed without packet files, ledger, dispatch index, router table, or atomic publication",
    "partial_generation_published_before_commit": "repair transaction committed without packet files, ledger, dispatch index, router table, or atomic publication",
    "replacement_generation_keeps_old_generation_current": "replacement packet generation lacked supersession, canonical identity, replayable hashes, or explicit result targets",
    "replacement_generation_has_duplicate_identity": "replacement packet generation lacked supersession, canonical identity, replayable hashes, or explicit result targets",
    "success_only_outcome_table": "repair transaction router outcome table did not route success, blocker, and protocol outcomes",
    "reviewer_recheck_before_commit": "reviewer recheck was requested before a committed generation and complete outcome table",
    "reviewer_blocker_unroutable": "reviewer recheck outcome was not accepted by router",
    "reviewer_protocol_blocker_unroutable": "reviewer recheck outcome was not accepted by router",
    "blocked_terminal_without_followup_blocker": "repair transaction blocked without registering a follow-up blocker",
    "complete_terminal_without_authority_refresh": "terminal repair transaction state did not refresh ledger, frontier, and display authorities",
    "controller_no_legal_next_after_recheck": "repair transaction reached no legal next action",
}


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|holder={state.holder}|steps={state.steps}|"
        f"blocker={state.blocker_detected},{state.blocker_registered_in_router},"
        f"{state.blocker_has_origin_event},{state.blocker_has_allowed_nonterminal_events}|"
        f"pm={state.pm_repair_decision_recorded},self_resolve={state.pm_decision_resolves_blocker}|"
        f"tx={state.repair_transaction_opened},{state.transaction_id_recorded},{state.transaction_plan_kind}|"
        f"stage={state.replacement_spec_written},{state.packet_files_staged},"
        f"{state.ledger_entries_staged},{state.dispatch_index_staged},"
        f"{state.router_resolution_table_staged},commit={state.transaction_committed_atomically},"
        f"partial={state.partial_generation_published}|"
        f"gen={state.replacement_generation_published},{state.old_generation_superseded},"
        f"{state.canonical_packet_identity_unique},{state.packet_hashes_replayable},"
        f"{state.result_write_targets_explicit}|"
        f"outcomes={state.success_outcome_routable},{state.blocker_outcome_routable},"
        f"{state.protocol_outcome_routable}|"
        f"review={state.reviewer_recheck_requested},{state.reviewer_outcome},"
        f"accepted={state.router_accepted_reviewer_outcome}|"
        f"terminal={state.original_blocker_resolved},{state.followup_blocker_registered},"
        f"{state.packet_ledger_refreshed},{state.frontier_refreshed},"
        f"{state.display_refreshed},dead={state.no_legal_next_action}"
    )


def _build_graph() -> dict[str, object]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states: list[model.State] = [initial]
    index = {initial: 0}
    edges: list[list[tuple[str, int]]] = []
    labels: set[str] = set()
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        source = index[state]
        while len(edges) <= source:
            edges.append([])
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})
        for label, new_state in model.next_states(state):
            labels.add(label)
            if new_state not in index:
                index[new_state] = len(states)
                states.append(new_state)
                queue.append(new_state)
            edges[source].append((label, index[new_state]))
    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _progress_report(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for idx, outgoing in enumerate(edges):
            if idx not in can_reach_terminal and any(target in can_reach_terminal for _label, target in outgoing):
                can_reach_terminal.add(idx)
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
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_terminal,
        "terminal_state_count": len(terminal),
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "cannot_reach_terminal_samples": cannot_reach_terminal[:10],
    }


def _check_hazards() -> dict[str, object]:
    hazards: dict[str, object] = {}
    ok = True
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": failures,
            "state": state.__dict__,
        }
        ok = ok and detected
    return {"ok": ok, "hazards": hazards}


def _flowguard_report() -> dict[str, object]:
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
        "reachability_failures": [failure.message for failure in report.reachability_failures],
    }


def _architecture_candidate() -> dict[str, object]:
    return {
        "name": "repair_transaction_generation_commit",
        "principles": [
            "PM repair decisions open a transaction; they never resolve blockers directly.",
            "Replacement packets are committed as one generation across physical files, packet ledger, dispatch index, and router resolution table.",
            "The router publishes success, blocker, and protocol-blocker outcomes before reviewer recheck starts.",
            "A reviewer failure is a legal terminal blocked state with a router-visible follow-up blocker, not controller no-legal-next-action.",
            "Terminal success or blocked states refresh packet ledger, frontier, and display authorities together.",
        ],
        "minimal_runtime_change_set": [
            "Add a run-scoped repair_transaction record and transaction_id.",
            "Move packet reissue materialization behind one commit function.",
            "Replace allowed_resolution_events success-only lists with an outcome table containing success and non-success events.",
            "Require reviewer recheck to consume only committed generation ids.",
            "Refresh router_state, packet_ledger, execution_frontier, and display surfaces in the same commit/finalize path.",
        ],
    }


def run_checks(*, json_out_requested: bool = False) -> dict[str, object]:
    graph = _build_graph()
    labels = set(graph["labels"])
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    safe_graph = {
        "ok": not graph["invariant_failures"] and not missing_labels,
        "state_count": len(graph["states"]),
        "edge_count": graph["edge_count"],
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"],
    }
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _check_hazards()
    skipped_checks = {
        "production_mutation": (
            "covered_elsewhere: this runner validates the model contract; "
            "runtime conformance is exercised by router unit tests"
        ),
    }
    if not json_out_requested:
        skipped_checks["default_results_file"] = "skipped_with_reason: no --json-out path was provided"
    return {
        "ok": bool(safe_graph["ok"]) and bool(progress["ok"]) and bool(explorer["ok"]) and bool(hazards["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "architecture_candidate": _architecture_candidate(),
        "skipped_checks": skipped_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, help="Optional path for writing JSON result payload.")
    args = parser.parse_args()

    result = run_checks(json_out_requested=bool(args.json_out))
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
