"""Thin FlowGuard child models for the persistent Router daemon mesh.

The full `flowpilot_persistent_router_daemon` model remains available as a
unsupported_historical check. These child models provide the bounded evidence consumed by
the parent hierarchy for the `router_daemon_resume` partition.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from typing import Any, Iterable, Mapping, NamedTuple, Sequence

from flowguard.explorer import Explorer
from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


FAMILIES = (
    "startup_lock",
    "controller_actions",
    "wait_liveness",
    "terminal_projection",
)

MODEL_IDS = {
    "startup_lock": "flowpilot_daemon_startup_lock",
    "controller_actions": "flowpilot_daemon_controller_actions",
    "wait_liveness": "flowpilot_daemon_wait_liveness",
    "terminal_projection": "flowpilot_daemon_terminal_projection",
}

FAMILY_FIELDS: dict[str, dict[str, str]] = {
    "startup_lock": {
        "startup_daemon_before_controller": "startup daemon was not proven before Controller core load",
        "single_writer_lock": "daemon lock allowed more than one Router writer",
        "ledgers_atomic_and_parseable": "runtime ledgers were not proven atomic and parseable",
        "write_lock_settlement_recorded": "runtime write-lock settlement evidence was missing",
        "self_or_dead_lock_recovery_rejoins": "stale or dead-owner lock recovery did not rejoin daemon flow",
        "daemon_status_matches_process": "daemon status did not match lock and process liveness",
    },
    "controller_actions": {
        "startup_receipt_syncs_bootstrap": "startup receipt did not sync bootstrap flag, pending action, and Router row",
        "controller_receipts_required": "Controller action completion was accepted without a receipt",
        "stateful_postcondition_visible": "stateful Controller receipt lacked Router-visible postcondition evidence",
        "repair_budget_respected": "stateful deliverable repair budget was bypassed or overclaimed",
        "router_fact_updated_from_receipt": "Router-owned internal fact was not updated from Controller receipt",
        "same_action_not_reissued": "Controller action was reissued after a completed receipt",
    },
    "wait_liveness": {
        "wait_target_metadata_complete": "daemon-owned role wait lacked role, evidence, or reminder metadata",
        "reminders_are_controller_actions": "wait reminder was not handled as executable Controller work",
        "fresh_liveness_probe_used": "report wait reminder used stale role liveness",
        "mailbox_consumed_once": "mailbox evidence was not consumed exactly once",
        "external_event_closed_by_router": "matching external-event wait was not closed by Router",
        "foreground_standby_polls": "foreground standby did not keep polling daemon status and action ledger",
    },
    "terminal_projection": {
        "current_work_projects_active_owner": "current-work projection did not name the active role, Controller, or Router owner",
        "patrol_no_second_daemon": "patrol could start a second live daemon",
        "terminal_fence_immediate": "terminal lifecycle did not write an immediate daemon fence",
        "terminal_projection_cleared": "terminal projection still exposed nonterminal work",
        "terminal_stops_runtime": "terminal lifecycle left daemon, Controller, roles, patrol, or route work active",
        "cleanup_failure_does_not_block_fence": "terminal cleanup failure blocked the immediate fence",
    },
}

COMMON_FAILURES = {
    "model_registered": "daemon child evidence was not registered",
    "parent_contract_attached": "daemon child did not attach to router_daemon_resume partition",
    "child_evidence_current": "daemon child evidence was stale or foreign",
    "child_outputs_reattached": "daemon child output contract did not reattach to parent flow",
    "parent_consumes_child_evidence": "parent did not consume current daemon child evidence id",
}


@dataclass(frozen=True)
class Tick:
    """One daemon child-mesh classification tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    family: str = "none"
    scenario: str = "new"
    status: str = "new"  # new | selected | accepted | rejected
    decision: str = "none"
    parent_partition: str = "router_daemon_resume"
    model_registered: bool = True
    parent_contract_attached: bool = True
    child_evidence_current: bool = True
    child_outputs_reattached: bool = True
    parent_consumes_child_evidence: bool = True
    startup_daemon_before_controller: bool = True
    single_writer_lock: bool = True
    ledgers_atomic_and_parseable: bool = True
    write_lock_settlement_recorded: bool = True
    self_or_dead_lock_recovery_rejoins: bool = True
    daemon_status_matches_process: bool = True
    startup_receipt_syncs_bootstrap: bool = True
    controller_receipts_required: bool = True
    stateful_postcondition_visible: bool = True
    repair_budget_respected: bool = True
    router_fact_updated_from_receipt: bool = True
    same_action_not_reissued: bool = True
    wait_target_metadata_complete: bool = True
    reminders_are_controller_actions: bool = True
    fresh_liveness_probe_used: bool = True
    mailbox_consumed_once: bool = True
    external_event_closed_by_router: bool = True
    foreground_standby_polls: bool = True
    current_work_projects_active_owner: bool = True
    patrol_no_second_daemon: bool = True
    terminal_fence_immediate: bool = True
    terminal_projection_cleared: bool = True
    terminal_stops_runtime: bool = True
    cleanup_failure_does_not_block_fence: bool = True


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _valid_family_state(family: str) -> State:
    return State(
        family=family,
        scenario=f"valid_{family}",
        status="selected",
        decision="child_green_parent_reattached",
    )


def scenarios_for(family: str) -> dict[str, State]:
    if family not in FAMILY_FIELDS:
        raise ValueError(f"unknown daemon child family: {family}")
    valid = _valid_family_state(family)
    scenarios: dict[str, State] = {valid.scenario: valid}
    for field in COMMON_FAILURES:
        scenario = f"{family}_{field}_missing"
        scenarios[scenario] = replace(valid, scenario=scenario, **{field: False})
    for field in FAMILY_FIELDS[family]:
        scenario = f"{family}_{field}_broken"
        scenarios[scenario] = replace(valid, scenario=scenario, **{field: False})
    return scenarios


def valid_scenarios(family: str) -> set[str]:
    return {f"valid_{family}"}


def negative_scenarios(family: str) -> set[str]:
    return set(scenarios_for(family)) - valid_scenarios(family)


def child_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "new":
        return failures
    if state.parent_partition != "router_daemon_resume":
        failures.append("daemon child attached to wrong parent partition")
    for field, message in COMMON_FAILURES.items():
        if not getattr(state, field):
            failures.append(message)
    family_fields = FAMILY_FIELDS.get(state.family)
    if not family_fields:
        failures.append("unknown daemon child family")
        return sorted(set(failures))
    for field, message in family_fields.items():
        if not getattr(state, field):
            failures.append(message)
    return sorted(set(failures))


def next_safe_states(family: str, state: State) -> Iterable[Transition]:
    if state.status == "new":
        for name, scenario in sorted(scenarios_for(family).items()):
            yield Transition(f"select_{name}", scenario)
        return
    if state.status == "selected":
        terminal = "rejected" if child_failures(state) else "accepted"
        label = f"{terminal.removesuffix('ed')}_{state.scenario}"
        yield Transition(label, replace(state, status=terminal))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted"


class DaemonChildStep:
    """Model one parent-consumable persistent daemon child decision.

    Input x State -> Set(Output x State)
    reads: child result metadata, parent partition contract, family hazard
    evidence, child output contract
    writes: one accepted or rejected daemon child evidence decision
    idempotency: classification is pure over immutable result fingerprints and
    parent evidence ids
    """

    name = "DaemonChildStep"
    input_description = "daemon child evidence tick"
    output_description = "accepted or rejected daemon child evidence"
    reads = (
        "child_result_metadata",
        "parent_responsibility_ledger",
        "hazard_family_contract",
        "child_output_contract",
    )
    writes = ("daemon_child_evidence_decision",)
    idempotency = "pure classification keyed by model id and result fingerprint"

    def __init__(self, family: str) -> None:
        if family not in FAMILY_FIELDS:
            raise ValueError(f"unknown daemon child family: {family}")
        self.family = family

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(self.family, state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def build_workflow(family: str) -> Workflow:
    return Workflow((DaemonChildStep(family),), name=MODEL_IDS[family])


def required_labels(family: str) -> set[str]:
    labels = {f"select_{name}" for name in scenarios_for(family)}
    labels.update(f"accept_{name}" for name in valid_scenarios(family))
    labels.update(f"reject_{name}" for name in negative_scenarios(family))
    return labels


def invariant_failures(state: State) -> list[str]:
    if state.status == "accepted":
        failures = child_failures(state)
        if failures:
            return [f"accepted unsafe daemon child evidence: {failures}"]
    if state.status == "rejected" and not child_failures(state):
        return ["rejected valid daemon child evidence"]
    return []


def accepted_states_are_safe(state: State, _trace: Sequence[Any]) -> InvariantResult:
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "accepted_states_are_safe",
        "Accepted daemon child evidence must satisfy its parent reattachment and family contract.",
        accepted_states_are_safe,
    ),
)


def _state_id(state: State) -> str:
    return (
        f"family={state.family}|scenario={state.scenario}|status={state.status}|"
        f"decision={state.decision}|parent={state.parent_partition}|"
        f"registered={state.model_registered}|current={state.child_evidence_current}|"
        f"reattached={state.child_outputs_reattached}|consumed={state.parent_consumes_child_evidence}"
    )


def _walk_graph(family: str) -> dict[str, Any]:
    queue: deque[State] = deque([initial_state()])
    states: list[State] = [initial_state()]
    index = {initial_state(): 0}
    edges: list[list[tuple[str, int]]] = []
    labels_seen: set[str] = set()
    violations: list[dict[str, Any]] = []

    while queue:
        state = queue.popleft()
        source = index[state]
        while len(edges) <= source:
            edges.append([])
        failures = invariant_failures(state)
        if failures:
            violations.append({"state": _state_id(state), "failures": failures})
        for transition in next_safe_states(family, state):
            labels_seen.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                queue.append(transition.state)
            edges[source].append((transition.label, index[transition.state]))

    missing_labels = sorted(required_labels(family) - labels_seen)
    return {
        "ok": not violations and not missing_labels,
        "states": states,
        "edges": edges,
        "state_count": len(states),
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "labels_seen": sorted(labels_seen),
        "missing_labels": missing_labels,
        "violations": violations,
    }


def _graph_for_output(graph: Mapping[str, Any]) -> dict[str, Any]:
    states = graph["states"]
    return {
        "ok": graph["ok"],
        "state_count": graph["state_count"],
        "edge_count": graph["edge_count"],
        "terminal_state_count": sum(1 for state in states if is_terminal(state)),
        "accepted_state_count": sum(1 for state in states if state.status == "accepted"),
        "rejected_state_count": sum(1 for state in states if state.status == "rejected"),
        "missing_labels": graph["missing_labels"],
        "violations": graph["violations"],
    }


def _progress_report(graph: Mapping[str, Any]) -> dict[str, Any]:
    states: list[State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {index for index, state in enumerate(states) if is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for index, outgoing in enumerate(edges):
            if index not in can_reach_terminal and any(target in can_reach_terminal for _label, target in outgoing):
                can_reach_terminal.add(index)
                changed = True
    stuck = [
        _state_id(state)
        for index, state in enumerate(states)
        if index not in terminal and not edges[index]
    ]
    cannot_reach_terminal = [
        _state_id(state)
        for index, state in enumerate(states)
        if index not in can_reach_terminal
    ]
    return {
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_terminal,
        "stuck_state_count": len(stuck),
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "samples": (stuck + cannot_reach_terminal)[:10],
    }


def _flowguard_report(family: str) -> dict[str, Any]:
    report = Explorer(
        workflow=build_workflow(family),
        initial_states=(initial_state(),),
        external_inputs=(Tick(),),
        invariants=INVARIANTS,
        max_sequence_length=2,
        terminal_predicate=lambda _input, state, _trace: is_terminal(state),
        success_predicate=lambda state, _trace: is_success(state),
        required_labels=required_labels(family),
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


def _hazard_report(family: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    ok = True
    for name in sorted(negative_scenarios(family)):
        state = scenarios_for(family)[name]
        failures = child_failures(state)
        detected = bool(failures)
        ok = ok and detected
        rows.append(
            {
                "scenario": name,
                "detected": detected,
                "observed_failures": failures,
            }
        )
    return {"ok": ok, "hazards": rows}


def build_report(family: str) -> dict[str, Any]:
    graph = _walk_graph(family)
    progress = _progress_report(graph)
    flowguard = _flowguard_report(family)
    hazards = _hazard_report(family)
    ok = bool(graph["ok"] and progress["ok"] and flowguard["ok"] and hazards["ok"])
    return {
        "schema_version": "flowpilot.daemon_child_model_result.v1",
        "model": MODEL_IDS[family],
        "family": family,
        "result_type": "daemon_child_model",
        "parent_partition": "router_daemon_resume",
        "ok": ok,
        "routine_confidence": "current" if ok else "blocked",
        "release_confidence": "current" if ok else "blocked",
        "graph": _graph_for_output(graph),
        "progress": progress,
        "flowguard_explorer": flowguard,
        "hazard_checks": hazards,
        "parent_reattachment": {
            "parent": "meta",
            "partition": "router_daemon_resume",
            "unsupported_historical_full_model": "flowpilot_persistent_router_daemon",
            "parent_consumes_this_child": True,
            "child_output_contract": "daemon subdomain green result reattaches to router_daemon_resume",
        },
    }


__all__ = [
    "FAMILIES",
    "MODEL_IDS",
    "Action",
    "DaemonChildStep",
    "State",
    "Tick",
    "build_report",
    "build_workflow",
    "child_failures",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "required_labels",
    "scenarios_for",
]

