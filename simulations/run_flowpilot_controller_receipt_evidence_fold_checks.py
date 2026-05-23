"""Run checks for the FlowPilot Controller receipt evidence-fold model."""

from __future__ import annotations

import argparse
import ast
import json
import re
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_controller_receipt_evidence_fold_model as model


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = Path(__file__).resolve().with_name(
    "flowpilot_controller_receipt_evidence_fold_results.json"
)

REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"accept_{scenario}" for scenario in model.VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in model.NEGATIVE_SCENARIOS]
)

HAZARD_EXPECTED_FAILURES = {
    model.UNSUPPORTED_RECEIPT_WITH_PACKET_EVIDENCE: (
        "evidence-backed Controller receipt returned unsupported_stateful_controller_receipt"
    ),
    model.DIRECT_APPLY_ONLY_NO_RECEIPT_FOLD: (
        "direct apply writes a Router flag but Controller receipt has no registered evidence fold"
    ),
    model.RECEIPT_DONE_WITHOUT_CONTROLLER_RELAY_SIGNATURE: (
        "receipt done without controller relay signature"
    ),
    model.ROUTER_OWNED_STATE_PROJECTED_WITHOUT_REPLAY: (
        "Router-owned state action was projected to Controller receipt without registered state replay"
    ),
    model.FALSE_BLOCKER_WITH_EVIDENCE_AVAILABLE: (
        "control blocker was recorded even though Router-visible evidence could satisfy the postcondition"
    ),
    model.DUPLICATE_REQUEUE_WHILE_RECEIPT_DONE: (
        "same Controller action was requeued while the previous receipt or packet work was already in flight"
    ),
    model.DOWNSTREAM_WAIT_GATED_BY_UNFOLDED_DISPATCH: (
        "worker wait was gated by an unfurled dispatch flag instead of evidence-backed packet relay"
    ),
    model.RECONCILED_RECEIPT_WITHOUT_FLAG: (
        "registered receipt fold did not satisfy the Router-owned postcondition flag"
    ),
}

EVIDENCE_BACKED_RELAY_ACTIONS = {
    "relay_current_node_packet",
    "relay_current_node_result_to_pm",
    "relay_current_node_result_to_reviewer",
    "relay_material_scan_packets",
    "relay_material_scan_results_to_pm",
    "relay_material_scan_results_to_reviewer",
    "relay_pm_role_work_request_packet",
    "relay_pm_role_work_result_to_pm",
    "relay_research_packet",
    "relay_research_result_to_pm",
    "relay_research_result_to_reviewer",
}

STATE_LOAD_ACTION_PATTERN = re.compile(r"^load_[a-z0-9_]*_state$")


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|family={state.action_family}|"
        f"action={state.action_type}|postcondition={state.postcondition_name}|"
        f"receipt_possible={state.controller_receipt_possible}|receipt_done={state.controller_receipt_done}|"
        f"direct_flag={state.direct_apply_sets_flag}|fold={state.receipt_fold_registered}|"
        f"state_replay={state.router_owned_state_replay_registered}|"
        f"unsupported={state.unsupported_receipt_result}|evidence={state.router_visible_evidence_available}|"
        f"relay_sig={state.controller_relay_signature_recorded}|ledger_relay={state.packet_ledger_relay_recorded}|"
        f"path_only={state.path_only_handoff_reported}|"
        f"batch={state.packet_batch_relayed}|leases={state.active_holder_leases_issued}|"
        f"worker_open={state.worker_packet_opened_or_acknowledged}|pending={state.worker_result_still_pending}|"
        f"flag={state.router_postcondition_flag_satisfied}|reconciled={state.router_marked_receipt_reconciled}|"
        f"repair={state.repair_or_blocker_recorded}|false_blocker={state.false_control_blocker_recorded}|"
        f"requeued={state.same_action_requeued}|wait={state.downstream_wait_selected}|"
        f"reason={state.terminal_reason}"
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


def _safe_graph_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    terminal = [state for state in states if model.is_terminal(state)]
    accepted = [state for state in terminal if state.status == "accepted"]
    rejected = [state for state in terminal if state.status == "rejected"]
    accepted_scenarios = sorted(state.scenario for state in accepted)
    rejected_scenarios = sorted(state.scenario for state in rejected)
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and set(accepted_scenarios) == set(model.VALID_SCENARIOS)
        and set(rejected_scenarios) == set(model.NEGATIVE_SCENARIOS),
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted_scenarios": accepted_scenarios,
        "rejected_scenarios": rejected_scenarios,
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"][:5],
    }


def _progress_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for source, outgoing in enumerate(edges):
            if source not in can_reach_terminal and any(
                target in can_reach_terminal for _label, target in outgoing
            ):
                can_reach_terminal.add(source)
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
        "stuck_state_count": len(stuck),
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "samples": (stuck + cannot_reach_terminal)[:5],
    }


def _flowguard_report() -> dict[str, object]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=model.terminal_predicate,
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


def _hazard_report() -> dict[str, object]:
    hazards: dict[str, object] = {}
    failures: list[str] = []
    for name, state in model.hazard_states().items():
        scenario_failures = model.receipt_evidence_fold_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in scenario_failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": scenario_failures,
            "state": state.__dict__,
        }
        if not detected:
            failures.append(f"{name}: expected failure containing {expected!r}")
    return {"ok": not failures, "hazards": hazards, "failures": failures}


def _literal_string_set_from_ast(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: set[str] = set()

    class Visitor(ast.NodeVisitor):
        def visit_Constant(self, node: ast.Constant) -> None:  # noqa: N802
            if isinstance(node.value, str):
                values.add(node.value)

    Visitor().visit(tree)
    return values


def _literal_tuple_assignment_from_ast(path: Path, name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            continue
        if not isinstance(node.value, (ast.Tuple, ast.List, ast.Set)):
            continue
        for item in node.value.elts:
            if isinstance(item, ast.Constant) and isinstance(item.value, str):
                values.add(item.value)
    return values


def _direct_flag_writing_actions() -> dict[str, dict[str, object]]:
    handler_map_path = REPO_ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_router_action_handlers.py"
    assets_root = handler_map_path.parent
    handler_map_text = handler_map_path.read_text(encoding="utf-8")
    mapping: dict[str, str] = {}
    for action_type, function_name in re.findall(r'"([^"]+)":\s*(_apply_[A-Za-z0-9_]+)', handler_map_text):
        mapping[action_type] = function_name

    handler_files = list(assets_root.glob("flowpilot_router_action_handlers*.py"))
    function_bodies: dict[str, str] = {}
    function_pattern = re.compile(
        r"^def\s+(_apply_[A-Za-z0-9_]+)\s*\([^)]*\).*?(?=^def\s+_apply_|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    for path in handler_files:
        text = path.read_text(encoding="utf-8")
        for match in function_pattern.finditer(text):
            function_bodies[match.group(1)] = match.group(0)

    actions: dict[str, dict[str, object]] = {}
    flag_pattern = re.compile(r'run_state\["flags"\]\["([^"]+)"\]\s*=\s*True')
    for action_type, function_name in mapping.items():
        body = function_bodies.get(function_name, "")
        flags = sorted(set(flag_pattern.findall(body)))
        if flags:
            actions[action_type] = {
                "handler": function_name,
                "flags": flags,
            }
    return actions


def _receipt_registered_actions() -> set[str]:
    receipt_effects_path = (
        REPO_ROOT
        / "skills"
        / "flowpilot"
        / "assets"
        / "flowpilot_router_controller_scheduler_receipts_effects.py"
    )
    receipt_fold_registry_path = (
        REPO_ROOT
        / "skills"
        / "flowpilot"
        / "assets"
        / "flowpilot_router_controller_scheduler_receipts_packet_folds.py"
    )
    receipt_fold_registry_child_path = (
        REPO_ROOT
        / "skills"
        / "flowpilot"
        / "assets"
        / "flowpilot_router_controller_scheduler_receipts_packet_fold_registry.py"
    )
    literals = _literal_string_set_from_ast(receipt_effects_path)
    if receipt_fold_registry_path.exists():
        literals |= _literal_string_set_from_ast(receipt_fold_registry_path)
    if receipt_fold_registry_child_path.exists():
        literals |= _literal_string_set_from_ast(receipt_fold_registry_child_path)
    # Known literal action names in the receipt effect dispatcher or in the
    # shared receipt evidence-fold registry count as registered folds.
    return {
        value
        for value in literals
        if value
        in EVIDENCE_BACKED_RELAY_ACTIONS
        | {
            "load_role_recovery_state",
            "recover_role_agents",
            "rehydrate_role_agents",
            "confirm_controller_core_boundary",
            "write_display_surface_status",
            "deliver_mail",
        }
    }


def _router_owned_state_replay_actions() -> set[str]:
    contract_path = (
        REPO_ROOT
        / "skills"
        / "flowpilot"
        / "assets"
        / "flowpilot_control_plane_contracts.py"
    )
    return _literal_tuple_assignment_from_ast(
        contract_path,
        "ROUTER_OWNED_STATE_REPLAY_ACTION_TYPES",
    )


def _source_contract_report() -> dict[str, object]:
    direct_flag_actions = _direct_flag_writing_actions()
    receipt_registered = _receipt_registered_actions()
    router_owned_state_replay = _router_owned_state_replay_actions()
    evidence_backed_flag_actions = {
        action_type: details
        for action_type, details in sorted(direct_flag_actions.items())
        if action_type in EVIDENCE_BACKED_RELAY_ACTIONS
    }
    router_owned_state_flag_actions = {
        action_type: details
        for action_type, details in sorted(direct_flag_actions.items())
        if STATE_LOAD_ACTION_PATTERN.match(action_type)
    }
    missing = {
        action_type: details
        for action_type, details in sorted(evidence_backed_flag_actions.items())
        if action_type not in receipt_registered
    }
    missing_router_owned_state_replay = {
        action_type: details
        for action_type, details in sorted(router_owned_state_flag_actions.items())
        if action_type not in router_owned_state_replay
    }
    return {
        "ok": not missing and not missing_router_owned_state_replay,
        "direct_flag_actions": direct_flag_actions,
        "evidence_backed_relay_actions": sorted(EVIDENCE_BACKED_RELAY_ACTIONS),
        "evidence_backed_relay_flag_actions": evidence_backed_flag_actions,
        "router_owned_state_flag_actions": router_owned_state_flag_actions,
        "receipt_registered_actions": sorted(receipt_registered),
        "router_owned_state_replay_actions": sorted(router_owned_state_replay),
        "missing_receipt_fold_for_evidence_backed_relay_actions": missing,
        "missing_router_owned_state_replay_actions": missing_router_owned_state_replay,
        "rule": (
            "Any evidence-backed packet/result relay action whose direct apply handler sets "
            "a Router-owned flag must have an idempotent receipt evidence-fold path. "
            "Any load_*_state action whose direct apply handler sets a Router-owned flag "
            "must be registered as Router-owned state replay, so a Controller receipt can "
            "only trigger the Router action handler instead of acting as standalone proof."
        ),
    }


def run_checks(include_source_audit: bool = True) -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    flowguard = _flowguard_report()
    hazards = _hazard_report()
    source_contract = _source_contract_report() if include_source_audit else {"ok": True, "skipped": True}
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "ok": bool(safe_graph["ok"])
        and bool(progress["ok"])
        and bool(flowguard["ok"])
        and bool(hazards["ok"])
        and bool(source_contract["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": flowguard,
        "hazard_checks": hazards,
        "source_contract": source_contract,
        "model_boundary": (
            "focused Controller receipt evidence-fold contract for Router-owned postconditions; "
            "source audit checks direct flag writers against receipt fold registration"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument(
        "--skip-source-audit",
        action="store_true",
        help="Run only the abstract FlowGuard model and hazard checks.",
    )
    args = parser.parse_args()

    result = run_checks(include_source_audit=not args.skip_source_audit)
    args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
