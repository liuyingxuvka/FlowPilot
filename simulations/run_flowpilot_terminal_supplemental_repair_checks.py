"""Run checks for the FlowPilot terminal supplemental repair model."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

import flowpilot_terminal_supplemental_repair_model as model


RESULTS_PATH = Path(__file__).resolve().with_name("flowpilot_terminal_supplemental_repair_results.json")

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.MISSING_SUPPLEMENTAL_CONTRACT: "terminal gap repair requires PM supplemental contract",
    model.ORIGINAL_CONTRACT_MUTATED: "terminal supplemental repair must not mutate frozen original contract",
    model.MISSING_REPAIR_ITEM_OWNER: "supplemental repair items require owner repair nodes",
    model.MISSING_ROUTE_NODE_PROJECTION: "repair route nodes must project supplemental contract and item ids",
    model.REPAIR_BYPASSES_EXISTING_GATES: "supplemental repair nodes must reuse existing FlowPilot gates",
    model.FINAL_LEDGER_OMITS_SUPPLEMENTAL: "final ledgers must include supplemental repair closure rows",
    model.TERMINAL_REPLAY_OMITS_SUPPLEMENTAL: "terminal backward replay must include supplemental repair segments",
    model.FOURTH_ROUND_PM_PACKET_OPENED: "runtime must stop instead of opening a fourth supplemental repair round",
    model.HYGIENE_GAP_NOT_CONTRACTUALIZED: "required final artifact hygiene gap requires PM supplemental repair contract",
    model.HYGIENE_CATEGORY_MISSING: "final artifact hygiene repair items require hygiene_category",
    model.FINAL_LEDGER_OMITS_HYGIENE: "final ledgers must include final artifact hygiene closure rows",
    model.TERMINAL_REPLAY_OMITS_HYGIENE_SEGMENT: "terminal backward replay must include final artifact hygiene segment",
    model.OPTIONAL_HYGIENE_NOTE_BLOCKS: "optional hygiene notes must not block closure unless PM imports them",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|round={state.current_round}|"
        f"lifecycle={state.terminal_lifecycle_status}"
    )


def _build_graph() -> dict[str, Any]:
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

        for transition in model.next_safe_states(state):
            labels.add(transition.label)
            if transition.state not in index:
                index[transition.state] = len(states)
                states.append(transition.state)
                queue.append(transition.state)
            edges[source].append((transition.label, index[transition.state]))

    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    states: list[model.State] = graph["states"]
    terminal = [state for state in states if model.is_terminal(state)]
    accepted = [state for state in terminal if state.status == "accepted"]
    rejected = [state for state in terminal if state.status == "rejected"]
    accepted_scenarios = sorted(state.scenario for state in accepted)
    rejected_scenarios = sorted(state.scenario for state in rejected)
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    hazard_failures = {
        scenario: model.repair_failures(model._scenario_state(scenario))
        for scenario in model.NEGATIVE_SCENARIOS
    }
    missing_expected_hazards = [
        scenario
        for scenario, expected in HAZARD_EXPECTED_FAILURES.items()
        if expected not in hazard_failures.get(scenario, [])
    ]
    ok = (
        not graph["invariant_failures"]
        and not missing_labels
        and not missing_expected_hazards
        and accepted_scenarios == sorted(model.VALID_SCENARIOS)
        and rejected_scenarios == sorted(model.NEGATIVE_SCENARIOS)
    )
    report: dict[str, object] = {
        "ok": ok,
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_scenarios": accepted_scenarios,
        "rejected_scenarios": rejected_scenarios,
        "missing_labels": missing_labels,
        "missing_expected_hazards": missing_expected_hazards,
        "hazard_failures": hazard_failures,
        "invariant_failures": graph["invariant_failures"],
    }
    RESULTS_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    report = run_checks()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
