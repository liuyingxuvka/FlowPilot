"""Current-run projection checks for the FlowPilot process liveness runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent

def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _maybe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return _read_json(path)
    except json.JSONDecodeError:
        return {"_invalid_json": True, "_path": str(path)}

def _severity_counts(findings: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        severity = str(finding.get("severity", "info"))
        counts[severity] = counts.get(severity, 0) + 1
    return counts


def _int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _lifecycle_guard_repeat_findings(ledger: Any) -> list[dict[str, object]]:
    if not isinstance(ledger, dict):
        return []
    guard = ledger.get("lifecycle_guard")
    if not isinstance(guard, dict):
        history = ledger.get("lifecycle_guard_history")
        if isinstance(history, list) and history and isinstance(history[-1], dict):
            guard = history[-1]
        else:
            return []
    config = ledger.get("lifecycle_guard_config") if isinstance(ledger.get("lifecycle_guard_config"), dict) else {}
    threshold = _int_value(config.get("max_repeated_action_without_event"), 3)
    action_key = str(guard.get("action_key") or "")
    observed_event_count = guard.get("observed_event_count")
    repeated_count = _int_value(guard.get("repeated_count"), 1)
    decision = str(guard.get("decision") or "")
    next_action = guard.get("next_action") if isinstance(guard.get("next_action"), dict) else {}
    action_type = str(next_action.get("action_type") or guard.get("action_type") or "")
    action_class = str(guard.get("next_action_class") or next_action.get("next_action_class") or "")
    history = ledger.get("lifecycle_guard_history") if isinstance(ledger.get("lifecycle_guard_history"), list) else []
    prior_stuck_same_action = any(
        isinstance(row, dict)
        and row.get("action_key") == action_key
        and row.get("observed_event_count") == observed_event_count
        and row.get("decision") == "control_plane_stuck"
        for row in history
    )
    threshold_exceeded = (
        repeated_count >= threshold
        and action_class not in {"role_dispatch", "router_internal"}
        and decision not in {
            "control_plane_stuck",
            "terminal_return",
            "wait_for_ack",
            "wait_for_result",
            "wait_for_resume",
            "resume_reconcile",
        }
    )
    if not action_key or decision == "control_plane_stuck" or not (prior_stuck_same_action or threshold_exceeded):
        return []
    return [
        {
            "id": "repeated_lifecycle_action_not_absorbed",
            "severity": "blocking",
            "summary": "lifecycle guard history shows a repeated nonterminal action that has not been absorbed into control_plane_stuck",
            "action_key": action_key,
            "action_type": action_type,
            "next_action_class": action_class,
            "decision": decision,
            "repeated_count": repeated_count,
            "threshold": threshold,
            "prior_stuck_same_action": prior_stuck_same_action,
            "observed_event_count": observed_event_count,
        }
    ]


def _lifecycle_guard_blocking_findings(ledger: Any) -> list[dict[str, object]]:
    if not isinstance(ledger, dict):
        return []
    guard = ledger.get("lifecycle_guard")
    if not isinstance(guard, dict):
        return []
    if str(guard.get("decision") or "") != "control_plane_stuck":
        return []
    next_action = guard.get("next_action") if isinstance(guard.get("next_action"), dict) else {}
    return [
        {
            "id": "lifecycle_guard_control_plane_stuck",
            "severity": "blocking",
            "summary": "current lifecycle guard is control_plane_stuck and must be repaired before live confidence",
            "action_key": str(guard.get("action_key") or ""),
            "action_type": str(next_action.get("action_type") or guard.get("action_type") or ""),
            "decision": "control_plane_stuck",
            "reason": str(guard.get("reason") or ""),
            "repeated_count": _int_value(guard.get("repeated_count"), 1),
        }
    ]


def _current_run_projection() -> dict[str, object]:
    findings: list[dict[str, object]] = []
    evidence_paths: list[str] = []
    current_path = PROJECT_ROOT / ".flowpilot" / "current.json"
    if not current_path.exists():
        return {
            "ok": True,
            "status": "missing_current_pointer",
            "current_run_can_continue": False,
            "permission": "no_current_run",
            "safe_to_claim_live_run_confidence": False,
            "metadata_only": True,
            "findings": [
                {
                    "id": "missing_current_pointer",
                    "severity": "blocking",
                    "summary": ".flowpilot/current.json is missing; no active run can be continued or claimed",
                }
            ],
        }

    current = _maybe_json(current_path)
    evidence_paths.append(str(current_path.relative_to(PROJECT_ROOT)))
    run_root_text = current.get("run_root")
    status = str(current.get("status") or "unknown")
    if not isinstance(run_root_text, str) or not run_root_text:
        findings.append(
            {
                "id": "run_root_missing",
                "severity": "blocking",
                "summary": ".flowpilot/current.json has no run_root",
            }
        )
        return {
            "ok": False,
            "status": status,
            "findings": findings,
            "evidence_paths": evidence_paths,
        }

    run_root = PROJECT_ROOT / run_root_text
    if not run_root.exists():
        findings.append(
            {
                "id": "run_root_missing_on_disk",
                "severity": "blocking",
                "summary": f"current run root does not exist: {run_root_text}",
            }
        )
        return {
            "ok": False,
            "status": status,
            "findings": findings,
            "evidence_paths": evidence_paths,
        }

    rel_run_root = str(run_root.relative_to(PROJECT_ROOT))
    frontier_path = run_root / "execution_frontier.json"
    router_path = run_root / "router_state.json"
    daemon_path = run_root / "runtime" / "router_daemon_status.json"
    ledger_path = run_root / "ledger.json"
    packet_path = run_root / "packet_ledger.json"
    final_summary_path = run_root / "final_summary.json"
    route_history_path = run_root / "route_memory" / "route_history_index.json"
    for path in (
        frontier_path,
        router_path,
        daemon_path,
        ledger_path,
        packet_path,
        final_summary_path,
        route_history_path,
    ):
        if path.exists():
            evidence_paths.append(str(path.relative_to(PROJECT_ROOT)))

    frontier = _maybe_json(frontier_path)
    router_state = _maybe_json(router_path)
    daemon_status = _maybe_json(daemon_path)
    ledger = _maybe_json(ledger_path)
    packet_ledger = _maybe_json(packet_path)
    final_summary = _maybe_json(final_summary_path)
    route_history = _maybe_json(route_history_path)

    frontier_status = str(frontier.get("status") or "unknown")
    frontier_terminal = bool(frontier.get("terminal"))
    terminal_event = str(frontier.get("terminal_event") or "")
    daemon_lifecycle = str(daemon_status.get("lifecycle_status") or "unknown")

    if status == "stopped_by_user" or terminal_event == "user_requests_run_stop":
        findings.append(
            {
                "id": "current_run_is_controlled_user_stop",
                "severity": "info",
                "summary": "current run is a controlled user stop, not a normal FlowPilot completion",
                "status": status,
                "frontier_status": frontier_status,
                "terminal_event": terminal_event,
            }
        )
    elif frontier_terminal and status not in {"complete", "stopped_by_user"}:
        findings.append(
            {
                "id": "terminal_frontier_status_not_classified",
                "severity": "warning",
                "summary": "execution frontier is terminal but current status is not clearly complete or stopped_by_user",
                "status": status,
                "frontier_status": frontier_status,
            }
        )

    active_blocker = router_state.get("active_control_blocker")
    if active_blocker:
        findings.append(
            {
                "id": "active_control_blocker_present",
                "severity": "blocking",
                "summary": "router_state still has active_control_blocker",
                "run_root": rel_run_root,
            }
        )

    unresolved_blockers: list[dict[str, object]] = []
    terminal_resolved_blockers: list[dict[str, object]] = []
    local_fix_misrouted_blockers: list[dict[str, object]] = []
    retry_budget_inconsistent_blockers: list[dict[str, object]] = []
    local_first_sources = {
        "controller_action_receipt_missing_router_postcondition",
        "startup_receipt_missing_router_postcondition",
        "startup_missing_postcondition",
    }
    for blocker in router_state.get("control_blockers", []) or []:
        if not isinstance(blocker, dict):
            continue
        resolution = str(blocker.get("resolution_status") or "")
        blocker_id = str(blocker.get("blocker_id") or "")
        source = str(blocker.get("source") or "")
        handling_lane = str(blocker.get("handling_lane") or "")
        artifact_path_text = blocker.get("blocker_artifact_path")
        if isinstance(artifact_path_text, str) and artifact_path_text:
            artifact_path = PROJECT_ROOT / artifact_path_text
            if artifact_path.exists() and artifact_path.suffix == ".json":
                evidence_paths.append(str(artifact_path.relative_to(PROJECT_ROOT)))
                artifact = _maybe_json(artifact_path)
                source = source or str(artifact.get("source") or "")
        direct_retry_budget = int(blocker.get("direct_retry_budget") or 0)
        direct_retry_attempts = int(blocker.get("direct_retry_attempts_used") or 0)
        direct_retry_exhausted = bool(blocker.get("direct_retry_budget_exhausted"))
        if direct_retry_budget <= direct_retry_attempts and not direct_retry_exhausted:
            retry_budget_inconsistent_blockers.append(
                {
                    "blocker_id": blocker_id,
                    "direct_retry_attempts_used": direct_retry_attempts,
                    "direct_retry_budget": direct_retry_budget,
                    "direct_retry_budget_exhausted": direct_retry_exhausted,
                    "handling_lane": handling_lane,
                }
            )
        if (
            source in local_first_sources
            and handling_lane in {
                "pm_repair",
                "pm_repair_decision_required",
            }
            and not direct_retry_exhausted
        ):
            local_fix_misrouted_blockers.append(
                {
                    "blocker_id": blocker_id,
                    "source": source,
                    "handling_lane": handling_lane,
                    "resolution_status": resolution,
                    "delivery_status": blocker.get("delivery_status"),
                }
            )
        if not resolution.startswith(("resolved", "superseded")):
            unresolved_blockers.append(
                {
                    "blocker_id": blocker_id,
                    "handling_lane": handling_lane,
                    "delivery_status": blocker.get("delivery_status"),
                    "resolution_status": resolution,
                }
            )
        elif blocker.get("resolved_by_event") == "user_requests_run_stop":
            terminal_resolved_blockers.append(
                {
                    "blocker_id": blocker_id,
                    "handling_lane": handling_lane,
                    "resolution_status": resolution,
                    "resolved_by_event": blocker.get("resolved_by_event"),
                }
            )
    if unresolved_blockers:
        findings.append(
            {
                "id": "unresolved_control_blockers",
                "severity": "blocking",
                "summary": "control blockers remain unresolved",
                "blockers": unresolved_blockers,
            }
        )
    if terminal_resolved_blockers:
        findings.append(
            {
                "id": "blocker_resolved_by_terminal_stop_not_repair",
                "severity": "info",
                "summary": "a blocker was cleared by user-stop terminal lifecycle, not by the normal PM repair return path",
                "blockers": terminal_resolved_blockers,
            }
        )
    if local_fix_misrouted_blockers:
        findings.append(
            {
                "id": "local_fix_style_blocker_routed_to_pm",
                "severity": "warning",
                "summary": "a blocker that looks like local settlement/reconciliation repair was routed to PM repair lane",
                "blockers": local_fix_misrouted_blockers,
            }
        )
    if retry_budget_inconsistent_blockers:
        findings.append(
            {
                "id": "blocker_retry_budget_flag_inconsistent",
                "severity": "warning",
                "summary": "a blocker retry budget is already exhausted by count but not marked exhausted",
                "blockers": retry_budget_inconsistent_blockers,
            }
        )

    findings.extend(_lifecycle_guard_blocking_findings(ledger))
    findings.extend(_lifecycle_guard_repeat_findings(ledger))

    controller_counts = (
        daemon_status.get("controller_action_ledger", {}).get("counts", {})
        if isinstance(daemon_status.get("controller_action_ledger"), dict)
        else {}
    )
    scheduler_counts = (
        daemon_status.get("router_scheduler_ledger", {}).get("counts", {})
        if isinstance(daemon_status.get("router_scheduler_ledger"), dict)
        else {}
    )
    open_controller_rows = int(controller_counts.get("pending") or 0) + int(
        controller_counts.get("waiting") or 0
    )
    open_scheduler_rows = int(scheduler_counts.get("queued") or 0) + int(
        scheduler_counts.get("waiting") or 0
    )
    if frontier_terminal and (open_controller_rows or open_scheduler_rows):
        findings.append(
            {
                "id": "terminal_run_retains_open_work_rows",
                "severity": "warning",
                "summary": "terminal run still has open Controller or scheduler rows; safe only as stopped-run history",
                "controller_open_rows": open_controller_rows,
                "scheduler_open_rows": open_scheduler_rows,
                "daemon_lifecycle": daemon_lifecycle,
            }
        )

    route_info = route_history.get("route") if isinstance(route_history.get("route"), dict) else {}
    review_markers = (
        route_history.get("review_markers")
        if isinstance(route_history.get("review_markers"), dict)
        else {}
    )
    effective_nodes = route_info.get("effective_nodes", [])
    if not isinstance(effective_nodes, list):
        effective_nodes = []
    route_node_count = int(route_info.get("route_node_count") or len(effective_nodes) or 0)
    review_pass_count = len(review_markers.get("passes") or [])
    completed_nodes = frontier.get("completed_nodes") or []
    if not isinstance(completed_nodes, list):
        completed_nodes = []
    if route_node_count == 0:
        severity = "blocking" if status == "complete" else "info"
        findings.append(
            {
                "id": "route_nodes_never_activated",
                "severity": severity,
                "summary": "no route nodes were activated, so per-node execution and reviewer coverage cannot be claimed",
                "route_node_count": route_node_count,
                "review_pass_count": review_pass_count,
                "completed_node_count": len(completed_nodes),
            }
        )
    elif status == "complete" and (
        len(completed_nodes) < route_node_count or review_pass_count < route_node_count
    ):
        findings.append(
            {
                "id": "completion_missing_per_node_review_coverage",
                "severity": "blocking",
                "summary": "run claims completion before every route node has completion and reviewer pass coverage",
                "route_node_count": route_node_count,
                "completed_node_count": len(completed_nodes),
                "review_pass_count": review_pass_count,
            }
        )

    flags = router_state.get("flags") if isinstance(router_state.get("flags"), dict) else {}
    if status == "complete":
        required_completion_flags = {
            "final_ledger_built": flags.get("final_ledger_built_clean") is True,
            "final_backward_replay": flags.get("final_backward_replay_passed") is True,
            "evidence_quality": flags.get("evidence_quality_reviewer_passed") is True,
        }
        missing = [name for name, ok in required_completion_flags.items() if not ok]
        if missing:
            findings.append(
                {
                    "id": "completion_missing_terminal_evidence",
                    "severity": "blocking",
                    "summary": "run claims completion but terminal ledger evidence is incomplete",
                    "missing": missing,
                }
            )
    else:
        findings.append(
            {
                "id": "normal_completion_not_claimed",
                "severity": "info",
                "summary": "normal route-wide completion was not claimed for the current run",
            }
        )

    packet_terminal = (
        packet_ledger.get("terminal_lifecycle", {})
        if isinstance(packet_ledger.get("terminal_lifecycle"), dict)
        else {}
    )
    if packet_terminal.get("status") == "stopped_by_user":
        findings.append(
            {
                "id": "packet_loop_stopped_by_user",
                "severity": "info",
                "summary": "packet loop was reconciled into stopped_by_user terminal lifecycle",
                "previous_active_packet_status": packet_terminal.get("previous_active_packet_status"),
            }
        )

    if final_summary and final_summary.get("run_lifecycle_status") == "stopped_by_user":
        findings.append(
            {
                "id": "terminal_summary_matches_user_stop",
                "severity": "info",
                "summary": "final summary reports stopped_by_user and forbids controller continuation",
            }
        )

    severity_counts = _severity_counts(findings)
    return {
        "ok": severity_counts.get("blocking", 0) == 0,
        "status": status,
        "run_root": rel_run_root,
        "frontier_status": frontier_status,
        "frontier_terminal": frontier_terminal,
        "daemon_lifecycle": daemon_lifecycle,
        "severity_counts": severity_counts,
        "findings": findings,
        "evidence_paths": evidence_paths,
    }
