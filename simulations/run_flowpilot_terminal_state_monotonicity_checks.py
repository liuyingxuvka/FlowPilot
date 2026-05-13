"""Run checks for the FlowPilot terminal-state monotonicity model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from flowguard import Explorer

import flowpilot_terminal_state_monotonicity_model as model


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
RESULTS_PATH = ROOT / "flowpilot_terminal_state_monotonicity_results.json"
ROUTER_PATH = PROJECT_ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_router.py"
CARD_RUNTIME_PATH = PROJECT_ROOT / "skills" / "flowpilot" / "assets" / "card_runtime.py"


REQUIRED_LABELS = tuple(
    [f"select_{scenario}" for scenario in model.SCENARIOS]
    + [f"merge_{scenario}_as_audit_only" for scenario in sorted(model.AUDIT_ONLY_SCENARIOS)]
    + [f"accept_{scenario}" for scenario in sorted(model.NEW_IDENTITY_ACCEPTED_SCENARIOS)]
    + [f"keep_{scenario}_blocking" for scenario in sorted(model.VALID_BLOCKING_SCENARIOS)]
)


HAZARD_EXPECTED_FAILURES = {
    "resolved_card_return_reopened_by_duplicate_ack": "terminal control-plane record was downgraded by same-identity replay",
    "resolved_bundle_return_reopened_by_duplicate_ack": "terminal control-plane record was downgraded by same-identity replay",
    "resolved_bundle_return_downgraded_to_incomplete": "terminal control-plane record was downgraded by same-identity replay",
    "pending_selector_ignores_resolved_at": "terminal-proven record still blocked downstream events",
    "pending_selector_ignores_completed_return": "terminal-proven record still blocked downstream events",
    "repair_channel_blocked_by_resolved_return": "terminal-proven record blocked the repair channel",
    "gate_pass_reopened_by_late_block": "terminal-proven record still blocked downstream events",
    "resolved_control_blocker_reactivated_by_stale_artifact": "terminal-proven record blocked the repair channel",
    "duplicate_pm_repair_created_new_blocker": "same-identity replay wrote a new side effect",
    "old_repair_generation_failure_reopened_success": "terminal-proven record blocked the repair channel",
    "new_repair_generation_failure_swallowed": "new scoped identity was swallowed by an old terminal record",
    "result_disposition_reopened_by_duplicate_result": "terminal control-plane record was downgraded by same-identity replay",
    "same_identity_replay_writes_duplicate_side_effect": "duplicate side effect written for terminal replay",
    "new_gate_identity_swallowed_by_old_pass": "new scoped identity was swallowed by an old terminal record",
    "new_control_blocker_swallowed_by_old_resolution": "new scoped identity was swallowed by an old terminal record",
    "new_result_identity_swallowed_by_old_disposition": "new scoped identity was swallowed by an old terminal record",
    "real_unresolved_return_released_by_overbroad_terminal_merge": "unresolved nonterminal control record was released",
}


def _state_id(state: model.State) -> str:
    return (
        f"scenario={state.scenario}|status={state.status}|kind={state.record_kind}|"
        f"terminal={state.terminal_status_before},marker={state.terminal_marker_present},"
        f"completed={state.completed_terminal_record_present}|same={state.incoming_same_identity},"
        f"new={state.incoming_new_identity},old_gen={state.incoming_from_old_generation}|"
        f"writer={state.writer_preserved_terminal},audit={state.audit_record_written},"
        f"selector={state.pending_selector_uses_terminal_proof}|blocked={state.downstream_blocked},"
        f"repair_blocked={state.repair_channel_blocked}|side_effect={state.new_side_effect_written},"
        f"dup_side_effect={state.duplicate_side_effect_written},new_blocker={state.new_blocker_created},"
        f"stale_block={state.stale_block_reactivated},old_reactivated={state.old_generation_reactivated},"
        f"new_swallowed={state.new_identity_swallowed},unresolved_released={state.unresolved_item_released}|"
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


def _safe_graph_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    terminal_states = [state for state in states if model.is_terminal(state)]
    audit_only = [state.scenario for state in terminal_states if state.status in {"audit_only", "already_recorded"}]
    accepted_new = [state.scenario for state in terminal_states if state.status == "accepted_new_identity"]
    valid_blocking = [state.scenario for state in terminal_states if state.status == "valid_blocking"]
    missing_labels = sorted(set(REQUIRED_LABELS) - set(graph["labels"]))
    return {
        "ok": not graph["invariant_failures"]
        and not missing_labels
        and set(audit_only) == model.AUDIT_ONLY_SCENARIOS
        and set(accepted_new) == model.NEW_IDENTITY_ACCEPTED_SCENARIOS
        and set(valid_blocking) == model.VALID_BLOCKING_SCENARIOS,
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "terminal_state_count": len(terminal_states),
        "audit_only_or_already_recorded": sorted(audit_only),
        "accepted_new_identity": sorted(accepted_new),
        "valid_blocking": sorted(valid_blocking),
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"][:10],
    }


def _progress_report(graph: dict[str, Any]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for idx, outgoing in enumerate(edges):
            targets = [target for _label, target in outgoing]
            if idx not in can_reach_terminal and any(target in can_reach_terminal for target in targets):
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
    ok = True
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in failures)
        ok = ok and detected
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": failures,
            "state": state.__dict__,
        }
    return {"ok": ok, "hazards": hazards}


def _window(text: str, needle: str, radius: int = 240) -> str:
    idx = text.find(needle)
    if idx == -1:
        return ""
    start = max(0, idx - radius)
    end = min(len(text), idx + len(needle) + radius)
    return " ".join(text[start:end].split())


def _function_block(text: str, function_name: str) -> str:
    marker = f"def {function_name}"
    start = text.find(marker)
    if start == -1:
        return ""
    next_def = text.find("\ndef ", start + len(marker))
    if next_def == -1:
        next_def = len(text)
    return text[start:next_def]


def _source_audit() -> dict[str, object]:
    router_source = ROUTER_PATH.read_text(encoding="utf-8")
    runtime_source = CARD_RUNTIME_PATH.read_text(encoding="utf-8")
    findings: list[dict[str, object]] = []

    selector_window = _function_block(router_source, "_pending_return_records")
    selector_uses_resolved_at = "resolved_at" in selector_window
    selector_uses_completed_keys = "completed_keys" in selector_window
    if not (selector_uses_resolved_at and selector_uses_completed_keys):
        findings.append(
            {
                "code": "pending_return_selector_status_only",
                "severity": "error",
                "summary": "Router pending-return selector does not visibly use resolved_at and completed-return proof.",
            }
        )

    writer_risks: list[dict[str, object]] = []
    runtime_lines = runtime_source.splitlines()
    for idx, line in enumerate(runtime_lines, start=1):
        if 'pending["status"] = "returned"' in line or 'pending["status"] = "bundle_ack_incomplete"' in line:
            nearby = "\n".join(runtime_lines[max(0, idx - 8) : min(len(runtime_lines), idx + 8)])
            guarded = "resolved_at" in nearby or "completed_returns" in nearby
            if not guarded:
                writer_risks.append(
                    {
                        "line": idx,
                        "assignment": line.strip(),
                        "summary": "card_runtime updates pending return status without a local terminal-state merge guard",
                    }
                )
    if writer_risks:
        findings.append(
            {
                "code": "card_runtime_pending_return_writer_can_dirty_terminal_record",
                "severity": "warning",
                "summary": "card_runtime can still dirty the raw ledger by writing returned onto a resolved pending record; Router read-side protection may mask it, but the writer is not terminal-monotone.",
                "samples": writer_risks,
            }
        )

    return_check_window = _function_block(router_source, "_apply_card_return_event_check")
    bundle_check_window = _function_block(router_source, "_apply_card_bundle_return_event_check")
    checks_write_resolved = (
        'item["status"] = "resolved"' in return_check_window
        and 'item["status"] = "resolved"' in bundle_check_window
        and "completed_returns" in return_check_window
        and "completed_returns" in bundle_check_window
    )
    if not checks_write_resolved:
        findings.append(
            {
                "code": "card_return_check_does_not_record_terminal_completion",
                "severity": "error",
                "summary": "Router card-return checks do not visibly set resolved status and completed-return proof for both card and bundle returns.",
            }
        )

    return {
        "ok": not any(finding["severity"] == "error" for finding in findings),
        "router_path": str(ROUTER_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "card_runtime_path": str(CARD_RUNTIME_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "router_pending_selector_uses_resolved_at": selector_uses_resolved_at,
        "router_pending_selector_uses_completed_keys": selector_uses_completed_keys,
        "router_card_return_checks_write_resolved_completion": checks_write_resolved,
        "finding_count": len(findings),
        "findings": findings,
    }


def _return_identity(record: dict[str, Any]) -> tuple[str, str, str]:
    return_kind = str(record.get("return_kind") or "system_card")
    identity = str(record.get("card_bundle_id") or record.get("delivery_attempt_id") or "")
    event = str(record.get("card_return_event") or "")
    return return_kind, identity, event


def _audit_return_ledger(path: Path) -> list[dict[str, object]]:
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(ledger, dict):
        return []
    completed_keys = {
        _return_identity(item)
        for item in ledger.get("completed_returns", [])
        if isinstance(item, dict) and item.get("status") == "resolved"
    }
    findings: list[dict[str, object]] = []
    for index, item in enumerate(ledger.get("pending_returns", [])):
        if not isinstance(item, dict):
            continue
        status = item.get("status")
        identity = _return_identity(item)
        terminal_proof = bool(item.get("resolved_at")) or identity in completed_keys
        if status in {"returned", "bundle_ack_incomplete"} and terminal_proof:
            findings.append(
                {
                    "path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    "pending_index": index,
                    "card_return_event": item.get("card_return_event"),
                    "identity": {
                        "return_kind": identity[0],
                        "delivery_or_bundle_id": identity[1],
                        "event": identity[2],
                    },
                    "raw_status": status,
                    "resolved_at": item.get("resolved_at"),
                    "would_block_if_query_used_status_only": True,
                    "blocked_by_terminal_aware_selector": False,
                }
            )
    return findings


def _live_metadata_audit(project_root: Path) -> dict[str, object]:
    run_root = project_root / ".flowpilot" / "runs"
    if not run_root.exists():
        return {
            "ok": True,
            "skipped": True,
            "skip_reason": ".flowpilot/runs not present",
            "dirty_terminal_pending_records": [],
        }
    findings: list[dict[str, object]] = []
    for ledger_path in sorted(run_root.glob("*/return_event_ledger.json")):
        findings.extend(_audit_return_ledger(ledger_path))
    return {
        "ok": True,
        "skipped": False,
        "return_event_ledger_count": len(list(run_root.glob("*/return_event_ledger.json"))),
        "dirty_terminal_pending_record_count": len(findings),
        "dirty_terminal_pending_records": findings,
        "interpretation": (
            "These are metadata-only findings. A dirty raw pending record is not "
            "necessarily an active blocker if the Router selector computes "
            "effective status from resolved_at/completed-return proof."
        ),
    }


def _same_class_findings() -> list[dict[str, str]]:
    return [
        {
            "class": "terminal_pending_return_downgrade",
            "where": "card and bundle ACK ledgers",
            "failure": "resolved return is written back to returned or bundle_ack_incomplete",
        },
        {
            "class": "status_only_pending_query",
            "where": "Router pending-return selection and no-legal-next checks",
            "failure": "raw returned status overrides resolved_at/completed-return proof",
        },
        {
            "class": "stale_gate_or_blocker_reactivation",
            "where": "gate outcome blocks and control blockers",
            "failure": "late old block remains active after matching pass/resolution",
        },
        {
            "class": "same_identity_side_effect_replay",
            "where": "PM repair decisions, result returns, and repair transactions",
            "failure": "duplicate event creates a new blocker, transaction, or gate release",
        },
        {
            "class": "old_generation_event_replay",
            "where": "repair rechecks and replacement generations",
            "failure": "old generation failure reopens a newer successful generation",
        },
        {
            "class": "new_identity_swallowed_by_old_terminal",
            "where": "new blocker, gate, generation, or result under same event family",
            "failure": "global terminal flag suppresses a legitimate new scoped event",
        },
        {
            "class": "overbroad_terminal_bypass",
            "where": "pending returns, blockers, gates, and result waits without terminal proof",
            "failure": "a real unresolved item is released because the merge helper treats a raw field as terminal proof",
        },
    ]


def _architecture_candidate() -> dict[str, object]:
    return {
        "name": "terminal_state_monotone_control_record_merge",
        "principles": [
            "Terminal wins: resolved, passed, completed, closed, or superseded records cannot be downgraded by the same identity.",
            "Merge by scoped identity, not by event name alone: run, role, delivery/gate/blocker/transaction/generation, and relevant hash decide whether input is replay or new work.",
            "Writers and readers both compute effective status; raw status is never the only pending/blocking predicate.",
            "Same identity replay appends audit metadata only and creates no new blocker, transaction, dispatch, or gate release.",
            "New identity remains routable even when an older identity in the same event family is terminal.",
            "Old generation inputs are quarantined or audit-only after a newer generation reaches terminal state.",
            "Repair-channel liveness is protected: stale terminal records cannot block PM/reviewer repair decisions.",
        ],
        "minimal_runtime_change_set_for_later_discussion": [
            "Introduce one small merge helper for control records: effective_status(existing, incoming, identity) plus merge_terminal_record(existing, incoming).",
            "Use that helper in card_runtime card ACK and bundle ACK writers before assigning pending return status.",
            "Keep Router pending-return selection on effective status: raw returned is pending only when no resolved_at and no matching resolved completed-return proof exist.",
            "Upsert completed_returns by identity instead of appending unbounded duplicate terminal records.",
            "Apply the same helper shape to gate/blocker/repair/result ledgers where terminal records and late events share an identity.",
            "Add focused runtime tests for duplicate card ACK, duplicate bundle ACK, incomplete bundle ACK after resolved, stale gate block after pass, duplicate PM repair, old repair generation replay, and new generation acceptance.",
            "Keep a negative path: unresolved records without terminal proof must remain blocking.",
        ],
        "what_this_avoids": [
            "No broad new state machine framework.",
            "No new approval role or extra PM/reviewer ceremony.",
            "No blanket bypass of unresolved-return checks.",
            "No status-field proliferation; the existing resolved_at/completed-return/gate-key/transaction identity fields are enough if status is merged consistently.",
        ],
    }


def run_checks(*, live_root: Path | None = PROJECT_ROOT, json_out_requested: bool = False) -> dict[str, object]:
    graph = _build_graph()
    safe_graph = _safe_graph_report(graph)
    progress = _progress_report(graph)
    flowguard = _flowguard_report()
    hazards = _hazard_report()
    source_audit = _source_audit()
    live_audit = (
        _live_metadata_audit(live_root)
        if live_root is not None
        else {
            "ok": True,
            "skipped": True,
            "skip_reason": "skipped_with_reason: --skip-live-audit was provided",
            "dirty_terminal_pending_records": [],
        }
    )
    skipped_checks = {
        "production_mutation": "skipped_with_reason: this FlowGuard runner is read-only and never mutates production code or live run state",
        "sealed_body_replay": "skipped_with_reason: model and live audit use metadata only",
    }
    if not json_out_requested:
        skipped_checks["default_results_file"] = "skipped_with_reason: no --json-out path was provided"
    return {
        "ok": bool(safe_graph["ok"] and progress["ok"] and flowguard["ok"] and hazards["ok"] and source_audit["ok"] and live_audit["ok"]),
        "model": "flowpilot_terminal_state_monotonicity",
        "model_boundary": "control-plane terminal-state merge/idempotency; no production mutation and no sealed body inspection",
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": flowguard,
        "hazard_detection": hazards,
        "source_audit": source_audit,
        "live_metadata_audit": live_audit,
        "same_class_findings": _same_class_findings(),
        "architecture_candidate": _architecture_candidate(),
        "skipped_checks": skipped_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--live-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--skip-live-audit", action="store_true")
    args = parser.parse_args()
    result = run_checks(
        live_root=None if args.skip_live_audit else args.live_root,
        json_out_requested=bool(args.json_out),
    )
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
