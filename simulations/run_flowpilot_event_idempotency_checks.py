"""Run checks for the FlowPilot external-event idempotency model."""

from __future__ import annotations

import argparse
import ast
import json
import re
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_event_idempotency_model as model


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "flowpilot_event_idempotency_results.json"
ROUTER_PATH = PROJECT_ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_router.py"

REQUIRED_LABELS = (
    "select_one_shot_same_key_replay",
    "select_one_shot_new_context_rejected",
    "select_route_mutation_same_transaction_replay",
    "select_route_mutation_new_transaction",
    "select_control_repair_new_transaction",
    "select_gate_decision_same_key_replay",
    "select_gate_decision_new_key",
    "select_repair_retry_below_budget",
    "select_repair_retry_exceeds_budget",
    "select_cycle_scoped_event_after_reset",
    "select_cycle_scoped_event_without_reset",
    "select_lifecycle_replay",
    "router_accepts_new_scoped_event_identity",
    "router_returns_already_recorded_for_same_dedupe_key",
    "router_returns_already_recorded_for_same_cycle_replay",
    "router_escalates_after_retry_budget",
    "router_rejects_one_shot_new_context_without_reset",
)

HAZARD_EXPECTED_FAILURES = {
    "global_flag_swallows_new_route_mutation": "new scoped event identity was swallowed by global event flag",
    "unconditional_repeat_duplicates_gate_decision": "duplicate side effect written for replayed event identity",
    "repair_retry_below_budget_swallowed": "new scoped event identity was swallowed by global event flag",
    "retry_budget_exceeded_without_escalation": "repair retry budget exceeded without explicit PM escalation",
    "cycle_reuse_without_reset": "cycle-scoped event reused without reset evidence",
    "accepted_without_dedupe_key_fields": "accepted scoped event without dedupe key fields",
    "no_legal_next_action_after_swallow": "new scoped event identity was swallowed by global event flag",
}

REQUIRED_SCOPED_EVENT_POLICIES = {
    "pm_mutates_route_after_review_block": {
        "family": "transaction",
        "dedupe_fields": ("control_blocker_id", "repair_transaction_id", "route_version"),
        "severity": "high",
        "why": "route mutation can recur for a later blocker/repair transaction and must write a new mutation",
    },
    "pm_records_control_blocker_repair_decision": {
        "family": "transaction",
        "dedupe_fields": ("control_blocker_id", "repair_transaction_id"),
        "severity": "medium",
        "why": "PM repair decisions are transaction records, not a single run-wide fact",
    },
    "role_records_gate_decision": {
        "family": "gate",
        "dedupe_fields": ("gate_id", "route_version", "decided_by_role"),
        "severity": "medium",
        "why": "gate decisions may recur for a later gate/version but same-gate replay must be idempotent",
    },
    "pm_requests_startup_repair": {
        "family": "startup_cycle",
        "dedupe_fields": ("startup_review_cycle", "startup_fact_report_hash"),
        "severity": "medium",
        "why": "startup repair can recur across review cycles but same report replay should not duplicate repair state",
    },
    "pm_writes_route_draft": {
        "family": "route_draft",
        "dedupe_fields": ("draft_version", "route_hash"),
        "severity": "medium",
        "why": "route drafts are editable before activation, but repeat handling should be version/hash scoped",
    },
    "pm_completes_current_node_from_reviewed_result": {
        "family": "node_completion",
        "dedupe_fields": ("node_id", "packet_id", "result_hash"),
        "severity": "low",
        "why": "completion retry is currently guarded by missing-write detection, but it still belongs to scoped idempotency",
    },
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|event={state.event_name}|family={state.family}|"
        f"flag={state.flag_already_true}|key={state.incoming_key}|prior={','.join(state.prior_keys)}|"
        f"retry={state.retry_attempt}/{state.retry_budget}|reset={state.cycle_reset_recorded}|"
        f"side_effect={state.side_effect_written}|duplicate={state.duplicate_side_effect_written}|"
        f"escalated={state.explicit_escalation_written}|stuck={state.no_legal_next_action}|"
        f"reason={state.terminal_reason}"
    )


def _build_graph() -> dict[str, Any]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    seen: list[model.State] = [initial]
    index = {initial: 0}
    edges: list[list[tuple[str, int]]] = []
    labels: set[str] = set()
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


def _safe_graph_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    terminals = [state for state in states if model.is_terminal(state)]
    accepted = [state for state in terminals if state.status == "accepted"]
    already_recorded = [state for state in terminals if state.status == "already_recorded"]
    escalated = [state for state in terminals if state.status == "escalated"]
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and {state.scenario for state in accepted} == model.ACCEPTED_SCENARIOS
        and {state.scenario for state in already_recorded} == model.IDEMPOTENT_SCENARIOS
        and {state.scenario for state in escalated} == model.ESCALATED_SCENARIOS,
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "accepted": sorted(state.scenario for state in accepted),
        "already_recorded": sorted(state.scenario for state in already_recorded),
        "escalated": sorted(state.scenario for state in escalated),
        "missing_labels": missing_labels,
        "invariant_failure_count": len(graph["invariant_failures"]),
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
            targets = [target for _label, target in outgoing]
            if source not in can_reach_terminal and any(target in can_reach_terminal for target in targets):
                can_reach_terminal.add(source)
                changed = True
    stuck = [_state_id(state) for idx, state in enumerate(states) if idx not in terminal and not edges[idx]]
    cannot_reach_terminal = [_state_id(state) for idx, state in enumerate(states) if idx not in can_reach_terminal]
    return {
        "ok": not stuck and not cannot_reach_terminal,
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
    ok = True
    hazards: dict[str, dict[str, object]] = {}
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in failures)
        ok = ok and detected
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": failures,
            "state": _state_id(state),
        }
    return {"ok": ok, "hazards": hazards}


def _extract_router_events() -> dict[str, dict[str, str]]:
    module = ast.parse(ROUTER_PATH.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == "EXTERNAL_EVENTS":
            return ast.literal_eval(node.value)
    raise RuntimeError("EXTERNAL_EVENTS not found")


def _extract_constant_strings(source: str) -> dict[str, str]:
    constants: dict[str, str] = {}
    module = ast.parse(source)
    for node in module.body:
        target_name = None
        value_node = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target_name = node.targets[0].id
            value_node = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name = node.target.id
            value_node = node.value
        if target_name and isinstance(value_node, ast.Constant) and isinstance(value_node.value, str):
            constants[target_name] = value_node.value
    return constants


def _extract_repeatable_exceptions(source: str) -> dict[str, dict[str, str]]:
    constants = _extract_constant_strings(source)
    exceptions: dict[str, dict[str, str]] = {}
    for match in re.finditer(r"(repeatable_[a-z_]+)\s*=\s*(?:\(\s*)?event\s*==\s*([A-Z_]+|\"[^\"]+\")", source):
        name = match.group(1)
        raw_event = match.group(2)
        event = raw_event.strip('"') if raw_event.startswith('"') else constants.get(raw_event, raw_event)
        line_end = source.find("\n", match.start())
        start_line = source[match.start() : line_end if line_end != -1 else match.start() + 240]
        if "(" in start_line and ")" not in start_line:
            end = source.find("\n    )", match.end())
        else:
            end = source.find("\n", match.end())
        if end == -1:
            end = match.start() + 500
        window = source[match.start() : end]
        if not window.strip():
            window = source[match.start() : match.start() + 500]
        condition = "unconditional" if " and " not in " ".join(window.split()) else "conditional"
        exceptions[event] = {"exception_name": name, "condition": condition, "source_excerpt": " ".join(window.split())[:240]}
    if "heartbeat_or_manual_resume_requested" in source:
        exceptions["heartbeat_or_manual_resume_requested"] = {
            "exception_name": "pre_dedupe_special_case",
            "condition": "append_only_tick",
            "source_excerpt": "handled before generic duplicate check",
        }
    return exceptions


def _extract_scoped_event_policies(source: str) -> dict[str, dict[str, object]]:
    constants = _extract_constant_strings(source)
    module = ast.parse(source)
    for node in module.body:
        target_name = None
        value_node = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target_name = node.targets[0].id
            value_node = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name = node.target.id
            value_node = node.value
        if target_name != "SCOPED_EVENT_IDENTITY_POLICIES" or not isinstance(value_node, ast.Dict):
            continue
        policies: dict[str, dict[str, object]] = {}
        for key_node, item_node in zip(value_node.keys, value_node.values):
            if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                event = key_node.value
            elif isinstance(key_node, ast.Name):
                event = constants.get(key_node.id, key_node.id)
            else:
                continue
            value = ast.literal_eval(item_node)
            if isinstance(value, dict):
                policies[event] = value
        return policies
    return {}


def _source_audit_report() -> dict[str, object]:
    source = ROUTER_PATH.read_text(encoding="utf-8")
    events = _extract_router_events()
    repeatable = _extract_repeatable_exceptions(source)
    scoped_policies = _extract_scoped_event_policies(source)
    findings: list[dict[str, object]] = []

    for event, policy in REQUIRED_SCOPED_EVENT_POLICIES.items():
        meta = events.get(event)
        if not meta:
            findings.append({"event": event, "severity": "high", "issue": "required scoped event not registered"})
            continue
        scoped_policy = scoped_policies.get(event)
        if scoped_policy:
            scoped_fields = set(scoped_policy.get("dedupe_fields") or ())
            missing_fields = [field for field in policy["dedupe_fields"] if field not in scoped_fields]
            if not missing_fields:
                continue
            findings.append(
                {
                    "event": event,
                    "severity": policy["severity"],
                    "issue": "scoped idempotency policy is missing required dedupe fields",
                    "flag": meta.get("flag"),
                    "family": policy["family"],
                    "dedupe_fields": policy["dedupe_fields"],
                    "production_policy_fields": sorted(scoped_fields),
                    "missing_fields": missing_fields,
                    "why": policy["why"],
                }
            )
            continue
        repeat = repeatable.get(event)
        if repeat is None:
            findings.append(
                {
                    "event": event,
                    "severity": policy["severity"],
                    "issue": "scoped event currently falls through generic global-flag dedupe",
                    "flag": meta.get("flag"),
                    "family": policy["family"],
                    "dedupe_fields": policy["dedupe_fields"],
                    "why": policy["why"],
                }
            )
            continue
        if repeat["condition"] == "unconditional":
            findings.append(
                {
                    "event": event,
                    "severity": policy["severity"],
                    "issue": "repeatable event has no visible same-key idempotency guard at generic dedupe boundary",
                    "flag": meta.get("flag"),
                    "family": policy["family"],
                    "dedupe_fields": policy["dedupe_fields"],
                    "repeatable_exception": repeat,
                    "why": policy["why"],
                }
            )
        elif not any(field in repeat["source_excerpt"] for field in policy["dedupe_fields"]):
            findings.append(
                {
                    "event": event,
                    "severity": policy["severity"],
                    "issue": "repeatable event is conditionally allowed but generic boundary does not show scoped dedupe key use",
                    "flag": meta.get("flag"),
                    "family": policy["family"],
                    "dedupe_fields": policy["dedupe_fields"],
                    "repeatable_exception": repeat,
                    "why": policy["why"],
                }
            )

    return {
        "ok": True,
        "router_path": str(ROUTER_PATH.relative_to(PROJECT_ROOT)),
        "external_event_count": len(events),
        "scoped_policy_count": len(scoped_policies),
        "scoped_policies": scoped_policies,
        "repeatable_exception_count": len(repeatable),
        "repeatable_exceptions": repeatable,
        "required_scoped_event_count": len(REQUIRED_SCOPED_EVENT_POLICIES),
        "finding_count": len(findings),
        "findings": findings,
        "model_confidence": "source-audit checks that required scoped events have production idempotency policies; targeted router tests cover key runtime behavior",
    }


def run_checks() -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    flowguard = _flowguard_report()
    hazards = _hazard_report()
    source_audit = _source_audit_report()
    return {
        "ok": bool(safe_graph["ok"] and progress["ok"] and flowguard["ok"] and hazards["ok"] and source_audit["ok"]),
        "model": "flowpilot_event_idempotency",
        "model_boundary": "external-event dedupe, retry, and scoped idempotency; no production code mutation",
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": flowguard,
        "hazard_detection": hazards,
        "source_audit": source_audit,
        "repair_principle": {
            "dedupe_key": "event_name + explicit scope identity, not event_name + run-wide flag",
            "same_key": "return already_recorded without side effects",
            "new_key": "execute the event writer even when the run-wide flag for that event is already true",
            "retry_budget": "after a configured retry budget, emit explicit PM escalation/dead-end instead of silently swallowing",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args()
    result = run_checks()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
