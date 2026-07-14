"""Live audit adapter for the FlowPilot cross-plane friction model."""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterable

from flowpilot_cross_plane_friction_model_hazards import _safe_base
from flowpilot_cross_plane_friction_model_invariants import invariant_failures
from flowpilot_cross_plane_friction_model_state import (
    BODY_PATH_NAMES,
    DONE_ITEM_STATUSES,
    CURRENT_ROLE_ARCHETYPES,
    TERMINAL_STATUSES,
    State,
)


RETIRED_MATERIAL_EVENTS = frozenset(
    {
        "pm_issues_material_and_capability_scan_packets",
        "router_direct_material_scan_dispatch_recheck_passed",
        "router_direct_material_scan_dispatch_recheck_blocked",
        "router_protocol_blocker_material_scan_dispatch_recheck",
        "worker_scan_packet_bodies_delivered_after_dispatch",
        "worker_scan_results_returned",
        "pm_records_material_scan_result_disposition",
        "reviewer_reports_material_sufficient",
        "reviewer_reports_material_insufficient",
        "pm_accepts_reviewed_material",
        "pm_requests_research_after_material_insufficient",
        "pm_writes_material_understanding",
    }
)
RETIRED_MATERIAL_CARD_IDS = frozenset(
    {
        "pm.material_scan",
        "reviewer.material_sufficiency",
        "pm.event.reviewer_report",
        "pm.material_absorb_or_research",
        "pm.material_understanding",
    }
)
RETIRED_MATERIAL_FIELDS = frozenset(
    {
        "pm_material_packets_issued",
        "pm_material_scan_card_delivered",
        "material_scan_direct_dispatch_recheck_passed",
        "material_scan_dispatch_recheck_blocked",
        "material_scan_dispatch_recheck_protocol_blocked",
        "material_scan_packets_relayed",
        "worker_scan_results_returned",
        "material_scan_results_relayed_to_reviewer",
        "material_scan_results_relayed_to_pm",
        "material_scan_result_disposition_recorded",
        "material_scan_results_absorbed_by_pm",
        "reviewer_material_sufficiency_card_delivered",
        "material_review_sufficient",
        "material_review_insufficient",
        "pm_reviewer_report_event_delivered",
        "pm_material_absorb_or_research_card_delivered",
        "material_accepted_by_pm",
        "pm_material_understanding_card_delivered",
        "material_understanding_written_by_pm",
    }
)
RETIRED_MATERIAL_PACKET_FAMILIES = frozenset({"material_scan"})
CURRENT_ROLE_CARD_PATHS = (
    "skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md",
    "skills/flowpilot/assets/runtime_kit/cards/roles/human_like_reviewer.md",
    "skills/flowpilot/assets/runtime_kit/cards/roles/flowguard_operator.md",
    "skills/flowpilot/assets/runtime_kit/cards/roles/worker.md",
    "skills/flowpilot/assets/runtime_kit/cards/roles/worker_research_report.md",
)


def _read_json(path: Path) -> tuple[Any, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, f"missing: {path}"
    except json.JSONDecodeError as exc:
        return None, f"invalid_json: {path}: {exc}"
    except OSError as exc:
        return None, f"unreadable: {path}: {exc}"


def _rel(project_root: Path, path: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return path.as_posix()


def _finding(
    *,
    code: str,
    severity: str,
    summary: str,
    matched_invariant: str,
    evidence: dict[str, object],
    minimal_fix: str,
) -> dict[str, object]:
    return {
        "code": code,
        "severity": severity,
        "summary": summary,
        "matched_invariant": matched_invariant,
        "evidence": evidence,
        "minimal_fix": minimal_fix,
    }


def _resolve_run_root(project_root: Path, run_id: str | None = None) -> tuple[str | None, Path | None, list[dict[str, object]]]:
    findings: list[dict[str, object]] = []
    if run_id:
        run_root = project_root / ".flowpilot" / "runs" / run_id
        if run_root.exists():
            return run_id, run_root, findings
        findings.append(
            _finding(
                code="requested_run_missing",
                severity="error",
                summary="Requested FlowPilot run root does not exist.",
                matched_invariant="active_task_policy_hides_history",
                evidence={"run_id": run_id, "path": _rel(project_root, run_root)},
                minimal_fix="Use a valid run_id or restore the missing run directory.",
            )
        )
        return run_id, run_root, findings

    current_path = project_root / ".flowpilot" / "current.json"
    current, current_error = _read_json(current_path)
    if isinstance(current, dict):
        current_run_id = str(current.get("run_id") or "")
        current_run_root = str(current.get("run_root") or "")
        if current_run_id and current_run_root:
            return current_run_id, project_root / current_run_root, findings
        findings.append(
            _finding(
                code="current_pointer_current_contract_invalid",
                severity="error",
                summary="current.json lacks current-contract run_id/run_root fields.",
                matched_invariant="active_task_policy_hides_history",
                evidence={
                    "path": _rel(project_root, current_path),
                    "has_run_id": bool(current.get("run_id")),
                    "has_run_root": bool(current.get("run_root")),
                    "legacy_aliases_rejected": [
                        key
                        for key in ("current_run_id", "current_run_root", "active_run_id", "active_run_root")
                        if key in current
                    ],
                },
                minimal_fix=(
                    "Rewrite current.json with run_id/run_root. "
                    "Do not translate current_run_id/current_run_root or active_run_id/active_run_root aliases."
                ),
            )
        )
        return None, None, findings
    elif current_error:
        findings.append(
            _finding(
                code="current_pointer_missing",
                severity="warning",
                summary=".flowpilot/current.json is missing; no current live-run audit can be claimed.",
                matched_invariant="active_task_policy_hides_history",
                evidence={"path": _rel(project_root, current_path), "error": current_error},
                minimal_fix="Start or explicitly select a current FlowPilot run before claiming live-run evidence.",
            )
        )
    return None, None, findings


def _terminal(value: Any) -> bool:
    return str(value or "").lower() in TERMINAL_STATUSES


def _status(value: Any) -> str:
    return str(value or "").lower()


def _iter_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item


def _node_id(node: dict[str, Any]) -> str:
    return str(node.get("node_id") or node.get("id") or "")


def _checklist_items(node: dict[str, Any]) -> list[dict[str, Any]]:
    return list(_iter_dicts(node.get("checklist")))


def _done_status(value: Any) -> bool:
    return _status(value) in DONE_ITEM_STATUSES


def _literal_assignment(path: Path, assignment_names: set[str]) -> Any:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, SyntaxError, OSError):
        return None
    for node in ast.walk(tree):
        target_name = ""
        value: ast.AST | None = None
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                target_name = node.target.id
            value = node.value
        elif isinstance(node, ast.Assign):
            target_name = next(
                (
                    target.id
                    for target in node.targets
                    if isinstance(target, ast.Name) and target.id in assignment_names
                ),
                "",
            )
            value = node.value
        if target_name not in assignment_names or value is None:
            continue
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return None
    return None


def _load_router_external_events(router_path: Path) -> dict[str, dict[str, Any]]:
    direct = _literal_assignment(router_path, {"EXTERNAL_EVENTS"})
    if isinstance(direct, dict):
        return {
            str(event): meta if isinstance(meta, dict) else {}
            for event, meta in direct.items()
        }

    events: dict[str, dict[str, Any]] = {}
    for path in sorted(router_path.parent.glob("flowpilot_router_protocol_external_event_data_*.py")):
        if path.name == "flowpilot_router_protocol_external_event_data.py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, SyntaxError, OSError):
            continue
        assignment_names = {
            node.target.id
            for node in ast.walk(tree)
            if isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id.endswith("_EXTERNAL_EVENT_DATA")
        }
        assignment_names.update(
            target.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
            and target.id.endswith("_EXTERNAL_EVENT_DATA")
        )
        for assignment_name in assignment_names:
            payload = _literal_assignment(path, {assignment_name})
            if not isinstance(payload, dict):
                continue
            events.update(
                {
                    str(event): meta if isinstance(meta, dict) else {}
                    for event, meta in payload.items()
                }
            )
    return events


def _load_router_event_names(router_path: Path) -> set[str]:
    return set(_load_router_external_events(router_path))


def _collect_events(value: Any) -> set[str]:
    events: set[str] = set()

    def walk(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                normalized = str(key)
                if normalized in {
                    "event",
                    "event_name",
                    "originating_event",
                    "resolved_by_event",
                    "pm_repair_rerun_target",
                    "expected_external_event",
                    "next_external_event",
                } and isinstance(child, str):
                    events.add(child)
                elif normalized in {
                    "allowed_resolution_events",
                    "allowed_external_events",
                } and isinstance(child, list):
                    events.update(str(event) for event in child if isinstance(event, str))
                else:
                    walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)

    walk(value)
    return events


def _collect_protocol_authority(value: Any) -> dict[str, set[str]]:
    authority = {
        "events": set(),
        "fields": set(),
        "card_ids": set(),
        "packet_families": set(),
        "packet_ids": set(),
    }

    def walk(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                normalized = str(key)
                if normalized in RETIRED_MATERIAL_FIELDS:
                    authority["fields"].add(normalized)
                if normalized in {
                    "event",
                    "event_name",
                    "originating_event",
                    "resolved_by_event",
                    "pm_repair_rerun_target",
                    "expected_external_event",
                    "next_external_event",
                } and isinstance(child, str):
                    authority["events"].add(child)
                elif normalized in {"allowed_resolution_events", "allowed_external_events"}:
                    if isinstance(child, list):
                        authority["events"].update(
                            str(event) for event in child if isinstance(event, str)
                        )
                elif normalized in {"card_id", "system_card_id", "current_card_id"}:
                    if isinstance(child, str):
                        authority["card_ids"].add(child)
                elif normalized in {"packet_type", "packet_family"}:
                    if isinstance(child, str):
                        authority["packet_families"].add(child)
                elif normalized == "packet_id" and isinstance(child, str):
                    authority["packet_ids"].add(child)
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)

    walk(value)
    return authority


def _merge_protocol_authority(
    target: dict[str, set[str]],
    source: dict[str, set[str]],
) -> None:
    for key in target:
        target[key].update(source.get(key, set()))


def _retired_material_protocol_findings(
    *,
    project_root: Path,
    run_root: Path,
    router_state: Any,
    frontier: Any,
    packet_ledger: Any,
) -> list[dict[str, object]]:
    authority = _collect_protocol_authority(
        {
            "router_state": router_state,
            "execution_frontier": frontier,
            "packet_ledger": packet_ledger,
        }
    )
    artifact_roots = (
        run_root / "control_blocks",
        run_root / "mailbox" / "outbox" / "events",
        run_root / "role_output_status",
    )
    for root in artifact_roots:
        for path in root.glob("*.json"):
            payload, _error = _read_json(path)
            _merge_protocol_authority(authority, _collect_protocol_authority(payload))

    retired_events = sorted(authority["events"].intersection(RETIRED_MATERIAL_EVENTS))
    retired_fields = sorted(authority["fields"].intersection(RETIRED_MATERIAL_FIELDS))
    retired_cards = sorted(authority["card_ids"].intersection(RETIRED_MATERIAL_CARD_IDS))
    retired_packet_families = sorted(
        authority["packet_families"].intersection(RETIRED_MATERIAL_PACKET_FAMILIES)
    )
    retired_packet_ids = sorted(
        packet_id
        for packet_id in authority["packet_ids"]
        if packet_id.startswith("material-scan")
    )
    if not any(
        (
            retired_events,
            retired_fields,
            retired_cards,
            retired_packet_families,
            retired_packet_ids,
        )
    ):
        return []
    return [
        _finding(
            code="retired_material_protocol_authority_present",
            severity="error",
            summary=(
                "The current run still exposes retired mandatory material-scan, "
                "sufficiency, or understanding authority."
            ),
            matched_invariant="current_prework_contract_has_single_authority",
            evidence={
                "events": retired_events,
                "fields": retired_fields,
                "card_ids": retired_cards,
                "packet_families": retired_packet_families,
                "packet_ids": retired_packet_ids[:20],
                "body_files_opened": False,
            },
            minimal_fix=(
                "Reject the retired event, field, card, or packet family and issue fresh ordinary "
                "PM/research work through the current packet/result/review path. Do not translate "
                "legacy material state into current completion evidence."
            ),
        )
    ]


def _packet_contract_row(path: Path, family_id: str) -> dict[str, Any]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, SyntaxError, OSError):
        return {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        row: dict[str, Any] = {}
        for key_node, value_node in zip(node.keys, node.values):
            if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
                continue
            try:
                row[key_node.value] = ast.literal_eval(value_node)
            except (ValueError, SyntaxError):
                continue
        if row.get("family_id") == family_id:
            return row
    return {}


def audit_current_prework_sources(project_root: str | Path = ".") -> dict[str, object]:
    """Reconcile current prework authorities without re-owning child semantics."""

    root = Path(project_root).resolve()
    assets = root / "skills" / "flowpilot" / "assets"
    router_path = assets / "flowpilot_router.py"
    planning_path = assets / "flowpilot_router_protocol_planning_cards.py"
    flags_path = assets / "flowpilot_router_protocol_runtime_flags.py"
    packet_contract_path = assets / "flowpilot_core_runtime" / "packet_result_contracts.py"

    events = _load_router_external_events(router_path)
    planning_payload = _literal_assignment(planning_path, {"PLANNING_SYSTEM_CARD_SEQUENCE"})
    planning_cards = [
        card for card in planning_payload if isinstance(card, dict)
    ] if isinstance(planning_payload, (list, tuple)) else []
    runtime_flags = _literal_assignment(flags_path, {"RUNTIME_FLAG_DEFAULTS"})
    runtime_flag_names = set(runtime_flags) if isinstance(runtime_flags, dict) else set()
    event_flag_names = {
        str(value)
        for meta in events.values()
        if isinstance(meta, dict)
        for value in (meta.get("flag"), meta.get("requires_flag"))
        if isinstance(value, str)
    }
    card_ids = {str(card.get("card_id") or "") for card in planning_cards}
    active_retired = {
        "events": sorted(set(events).intersection(RETIRED_MATERIAL_EVENTS)),
        "card_ids": sorted(card_ids.intersection(RETIRED_MATERIAL_CARD_IDS)),
        "fields": sorted(
            (runtime_flag_names | event_flag_names).intersection(RETIRED_MATERIAL_FIELDS)
        ),
    }

    findings: list[dict[str, object]] = []
    if any(active_retired.values()):
        findings.append(
            _finding(
                code="retired_material_protocol_still_active",
                severity="error",
                summary="Current source catalogs still expose retired mandatory material authority.",
                matched_invariant="current_prework_contract_has_single_authority",
                evidence=active_retired,
                minimal_fix=(
                    "Delete the retired event, card, and runtime flag from current authority. "
                    "Keep old names only in forbidden/deleted lists, negative tests, or history."
                ),
            )
        )

    discovery_contract = _packet_contract_row(packet_contract_path, "task.discovery")
    required_fields = tuple(discovery_contract.get("required_fields") or ())
    explicit_arrays = tuple(discovery_contract.get("explicit_array_fields") or ())
    if (
        "candidate_skill_inventory" not in required_fields
        or "candidate_skill_inventory" not in explicit_arrays
    ):
        findings.append(
            _finding(
                code="shallow_skill_inventory_contract_missing",
                severity="error",
                summary="The discovery packet no longer preserves mandatory shallow skill inventory.",
                matched_invariant="current_prework_contract_has_single_authority",
                evidence={
                    "path": _rel(root, packet_contract_path),
                    "required_fields": list(required_fields),
                    "explicit_array_fields": list(explicit_arrays),
                },
                minimal_fix=(
                    "Restore candidate_skill_inventory as a required explicit array in the existing "
                    "task.discovery result contract; PM remains the relevance-selection owner."
                ),
            )
        )

    cards_by_id = {
        str(card.get("card_id") or ""): card
        for card in planning_cards
        if card.get("card_id")
    }
    product_architecture = cards_by_id.get("pm.product_architecture", {})
    research_package = cards_by_id.get("pm.research_package", {})
    product_requires = str(product_architecture.get("requires_flag") or "")
    research_present = bool(research_package)
    if product_requires != "user_intake_delivered_to_pm" or not research_present:
        findings.append(
            _finding(
                code="ordinary_resource_work_became_mandatory_gate",
                severity="error",
                summary=(
                    "The current planning cards no longer keep ordinary PM/research work optional "
                    "beside the direct product-architecture path."
                ),
                matched_invariant="current_prework_contract_has_single_authority",
                evidence={
                    "path": _rel(root, planning_path),
                    "product_architecture_requires_flag": product_requires,
                    "research_package_card_present": research_present,
                },
                minimal_fix=(
                    "Keep pm.product_architecture directly after user intake and retain "
                    "pm.research_package only as an ordinary PM-selected evidence workstream."
                ),
            )
        )

    incomplete_role_cards: list[dict[str, object]] = []
    for relative_path in CURRENT_ROLE_CARD_PATHS:
        path = root / relative_path
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            text = ""
        missing_markers = [
            marker
            for marker in ("numbered plan", "workstream_plan_and_completion")
            if marker not in text
        ]
        if missing_markers:
            incomplete_role_cards.append(
                {
                    "path": relative_path,
                    "missing_markers": missing_markers,
                }
            )
    if incomplete_role_cards:
        findings.append(
            _finding(
                code="complete_workstream_role_contract_missing",
                severity="error",
                summary="A substantive role card lost its numbered complete-workstream report contract.",
                matched_invariant="current_prework_contract_has_single_authority",
                evidence={"role_cards": incomplete_role_cards},
                minimal_fix=(
                    "Restore the numbered local plan and contract_self_check."
                    "workstream_plan_and_completion requirements in the existing role card."
                ),
            )
        )

    projected_state = state_from_findings(findings)
    return {
        "ok": not findings,
        "findings": findings,
        "finding_count": len(findings),
        "projected_invariant_failures": invariant_failures(projected_state),
        "evidence": {
            "event_catalog_path": _rel(root, assets / "flowpilot_router_protocol_external_event_data.py"),
            "planning_cards_path": _rel(root, planning_path),
            "runtime_flags_path": _rel(root, flags_path),
            "discovery_contract_path": _rel(root, packet_contract_path),
            "role_card_paths": list(CURRENT_ROLE_CARD_PATHS),
        },
        "claim_boundary": (
            "This source reconciliation checks current catalog and role-contract projection only; "
            "the ordinary-resource and complete-workstream child models retain semantic ownership."
        ),
    }


def _audit_terminal(
    *,
    project_root: Path,
    run_root: Path,
    router_state: Any,
    frontier: Any,
    closure: Any,
    lifecycle: Any,
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    closure_is_terminal = isinstance(closure, dict) and _terminal(closure.get("status"))
    if not closure_is_terminal:
        return findings

    router_status = router_state.get("status") if isinstance(router_state, dict) else None
    frontier_status = frontier.get("status") if isinstance(frontier, dict) else None
    lifecycle_status = lifecycle.get("status") if isinstance(lifecycle, dict) else None
    lifecycle_path = run_root / "lifecycle" / "run_lifecycle.json"
    if not isinstance(lifecycle, dict):
        findings.append(
            _finding(
                code="terminal_authority_mismatch",
                severity="error",
                summary="Terminal closure suite is closed, but canonical lifecycle/run_lifecycle.json is missing.",
                matched_invariant="terminal_closure_has_single_authority",
                evidence={
                    "closure_path": _rel(project_root, run_root / "closure" / "terminal_closure_suite.json"),
                    "missing_lifecycle_path": _rel(project_root, lifecycle_path),
                    "router_status": router_status,
                    "frontier_status": frontier_status,
                },
                minimal_fix=(
                    "Make terminal closure and reconcile_current_run always write "
                    "lifecycle/run_lifecycle.json in the same transaction as router_state, "
                    "current.json, index.json, execution_frontier, and route_state_snapshot."
                ),
            )
        )
    elif not (_terminal(router_status) and _terminal(frontier_status) and _terminal(lifecycle_status)):
        findings.append(
            _finding(
                code="terminal_authority_mismatch",
                severity="error",
                summary="Terminal status disagrees across closure, router, frontier, or lifecycle authority.",
                matched_invariant="terminal_closure_has_single_authority",
                evidence={
                    "closure_status": closure.get("status"),
                    "router_status": router_status,
                    "frontier_status": frontier_status,
                    "lifecycle_status": lifecycle_status,
                },
                minimal_fix=(
                    "Use one terminal lifecycle writer to set all visible authorities "
                    "to a terminal status and record the source event."
                ),
            )
        )
    if isinstance(router_state, dict) and router_state.get("active_control_blocker"):
        findings.append(
            _finding(
                code="terminal_control_blocker_not_cleared",
                severity="error",
                summary="A terminal run still exposes an active control blocker.",
                matched_invariant="terminal_closure_has_single_authority",
                evidence={"active_control_blocker": router_state.get("active_control_blocker")},
                minimal_fix=(
                    "Clear active_control_blocker during terminal lifecycle reconciliation "
                    "after the closure suite has been accepted."
                ),
            )
        )
    lifecycle_obj = closure.get("lifecycle") if isinstance(closure.get("lifecycle"), dict) else {}
    if lifecycle_obj.get("manual_resume_binding_active") is True:
        findings.append(
            _finding(
                code="terminal_manual_resume_binding_still_active",
                severity="error",
                summary="Terminal closure records manual_resume_binding_active=true.",
                matched_invariant="terminal_closure_has_single_authority",
                evidence={"closure_lifecycle": lifecycle_obj},
                minimal_fix="Set manual_resume_binding_active=false in terminal closure and delete/update stale patrol records.",
            )
        )
    return findings


def _audit_route_snapshot(
    *,
    frontier: Any,
    snapshot: Any,
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    if not isinstance(frontier, dict) or not isinstance(snapshot, dict):
        return findings
    completed = {str(item) for item in frontier.get("completed_nodes") or []}
    if not completed:
        return findings
    route = snapshot.get("route") if isinstance(snapshot.get("route"), dict) else {}
    nodes = list(_iter_dicts(route.get("nodes")))
    if not nodes:
        return findings
    status_mismatches: list[dict[str, object]] = []
    checklist_mismatches: list[dict[str, object]] = []
    selected_conflations: list[dict[str, object]] = []
    for node in nodes:
        node_id = _node_id(node)
        if node_id not in completed:
            continue
        node_status = _status(node.get("status"))
        is_complete = node.get("is_complete")
        if node_status != "completed" or is_complete is not True:
            status_mismatches.append(
                {
                    "node_id": node_id,
                    "status": node.get("status"),
                    "is_complete": is_complete,
                }
            )
        pending_items = [
            str(item.get("id") or item.get("label") or "")
            for item in _checklist_items(node)
            if not _done_status(item.get("status"))
        ]
        if pending_items:
            checklist_mismatches.append(
                {
                    "node_id": node_id,
                    "pending_checklist_count": len(pending_items),
                    "sample": pending_items[:8],
                }
            )
        if node.get("is_active") is True or node_status in ACTIVE_STATUSES:
            selected_conflations.append(
                {
                    "node_id": node_id,
                    "status": node.get("status"),
                    "is_active": node.get("is_active"),
                }
            )
    if status_mismatches:
        findings.append(
            _finding(
                code="route_state_snapshot_status_mismatch",
                severity="error",
                summary="Completed frontier nodes are displayed as pending/current in route_state_snapshot.",
                matched_invariant="route_snapshot_uses_frontier_completion",
                evidence={"nodes": status_mismatches[:12], "count": len(status_mismatches)},
                minimal_fix=(
                    "Build route_state_snapshot.route.nodes by overlaying "
                    "execution_frontier.completed_nodes before raw flow.json status, "
                    "and set is_complete=true for completed nodes."
                ),
            )
        )
    if checklist_mismatches:
        findings.append(
            _finding(
                code="route_state_snapshot_completed_checklists_pending",
                severity="error",
                summary="Completed route nodes still have pending checklist items in route_state_snapshot.",
                matched_invariant="route_snapshot_uses_frontier_completion",
                evidence={"nodes": checklist_mismatches[:12], "count": len(checklist_mismatches)},
                minimal_fix=(
                    "When a major node is in execution_frontier.completed_nodes, "
                    "project all of its checklist items as completed unless the item "
                    "has an explicit terminal failed/blocked status."
                ),
            )
        )
    if selected_conflations:
        findings.append(
            _finding(
                code="selected_state_conflated_with_completed_state",
                severity="warning",
                summary="A completed node is still marked active/current in the route snapshot.",
                matched_invariant="route_snapshot_uses_frontier_completion",
                evidence={"nodes": selected_conflations[:12], "count": len(selected_conflations)},
                minimal_fix=(
                    "Treat selected/current as a separate UI overlay. If a run is terminal, "
                    "do not mark the completed active_node_id as in_progress."
                ),
            )
        )
    return findings


def _load_cockpit_adapter(project_root: Path) -> Any | None:
    adapter_path = project_root / "flowpilot_cockpit" / "source_adapter.py"
    if not adapter_path.exists():
        return None
    module_name = "_flowpilot_cockpit_source_adapter_for_audit"
    spec = importlib.util.spec_from_file_location(module_name, adapter_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    old_module = sys.modules.get(module_name)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if old_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = old_module
    return getattr(module, "CurrentRunAdapter", None)


def _audit_cockpit_projection(
    *,
    project_root: Path,
    run_id: str,
    frontier: Any,
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    adapter_cls = _load_cockpit_adapter(project_root)
    if adapter_cls is None:
        return findings
    try:
        snapshot = adapter_cls(project_root, run_id).load()
    except Exception as exc:  # pragma: no cover - diagnostic audit path
        findings.append(
            _finding(
                code="cockpit_adapter_unloadable",
                severity="warning",
                summary="Cockpit source adapter exists but could not load the current run.",
                matched_invariant="cockpit_uses_same_completion_projection",
                evidence={"error": repr(exc)},
                minimal_fix="Keep Cockpit source adapter importable and able to load metadata-only run snapshots.",
            )
        )
        return findings
    completed = set()
    if isinstance(frontier, dict):
        completed = {str(item) for item in frontier.get("completed_nodes") or []}
    checklist_mismatches: list[dict[str, object]] = []
    status_mismatches: list[dict[str, object]] = []
    for node in getattr(snapshot, "nodes", []):
        node_id = str(getattr(node, "node_id", ""))
        if node_id not in completed:
            continue
        if str(getattr(node, "status", "")) != "completed":
            status_mismatches.append({"node_id": node_id, "status": getattr(node, "status", "")})
        pending = [
            str(getattr(item, "item_id", ""))
            for item in getattr(node, "checklist", [])
            if not _done_status(getattr(item, "status", ""))
        ]
        if pending:
            checklist_mismatches.append(
                {
                    "node_id": node_id,
                    "pending_checklist_count": len(pending),
                    "sample": pending[:8],
                }
            )
    if status_mismatches:
        findings.append(
            _finding(
                code="cockpit_completed_node_status_mismatch",
                severity="error",
                summary="Cockpit does not project every completed frontier node as completed.",
                matched_invariant="cockpit_uses_same_completion_projection",
                evidence={"nodes": status_mismatches[:12], "count": len(status_mismatches)},
                minimal_fix=(
                    "Apply execution_frontier.completed_nodes before display_plan or raw "
                    "flow.json status inside CurrentRunAdapter."
                ),
            )
        )
    if checklist_mismatches:
        findings.append(
            _finding(
                code="cockpit_completed_node_checklist_status_mismatch",
                severity="error",
                summary="Cockpit shows pending checklist items under completed nodes.",
                matched_invariant="cockpit_uses_same_completion_projection",
                evidence={"nodes": checklist_mismatches[:12], "count": len(checklist_mismatches)},
                minimal_fix=(
                    "When CurrentRunAdapter marks a node completed from frontier, "
                    "also mark that node's checklist items completed in the UI model."
                ),
            )
        )
    frontier_status = _status(getattr(snapshot, "frontier_status", ""))
    active_tasks = list(getattr(snapshot, "active_tasks", []))
    if frontier_status not in ACTIVE_STATUSES and active_tasks:
        findings.append(
            _finding(
                code="cockpit_closed_run_exposed_as_active_tab",
                severity="error",
                summary="Cockpit exposes a closed/non-active run as an active task tab.",
                matched_invariant="cockpit_uses_same_completion_projection",
                evidence={
                    "frontier_status": getattr(snapshot, "frontier_status", ""),
                    "active_task_count": len(active_tasks),
                    "run_id": run_id,
                },
                minimal_fix=(
                    "Compute active tasks from an active frontier status, not from "
                    "the mere presence of active_node_id in a closed run."
                ),
            )
        )
    try:
        sealed_check = adapter_cls(project_root, run_id).validate_no_sealed_body_reads()
    except Exception:
        sealed_check = {}
    if isinstance(sealed_check, dict) and sealed_check.get("metadata_only") is not True:
        findings.append(
            _finding(
                code="cockpit_sealed_body_boundary_unclear",
                severity="warning",
                summary="Cockpit sealed-body validation did not prove metadata-only access.",
                matched_invariant="controller_keeps_envelope_only_boundary",
                evidence={"validation": sealed_check},
                minimal_fix="Keep Cockpit body paths as metadata and expose a metadata_only validation result.",
            )
        )
    return findings


def _audit_event_taxonomy(
    *,
    project_root: Path,
    router_state: Any,
    run_root: Path,
) -> list[dict[str, object]]:
    router_events = _load_router_event_names(project_root / "skills" / "flowpilot" / "assets" / "flowpilot_router.py")
    if not router_events:
        return []
    observed = _collect_events(router_state)
    unknown_from_files: set[str] = set()
    for path in (run_root / "control_blocks").glob("*.json"):
        data, _error = _read_json(path)
        if isinstance(data, dict):
            observed.update(_collect_events(data))
            error_code = str(data.get("error_code") or "")
            if error_code.startswith("unknown_external_event_"):
                unknown_from_files.add(error_code.removeprefix("unknown_external_event_"))
    event_artifact_roots = (
        run_root / "mailbox" / "outbox" / "events",
        run_root / "role_output_status",
    )
    for root in event_artifact_roots:
        for path in root.glob("*.json"):
            data, _error = _read_json(path)
            if isinstance(data, dict):
                observed.update(_collect_events(data))
    candidate_events = {
        event
        for event in observed
        if event.startswith(
            (
                "reviewer_blocks",
                "current_node_reviewer_blocks",
                "flowguard_operator_route_scope_blocks",
                "flowguard_operator_product_scope_blocks",
            )
        )
    }.union(unknown_from_files)
    unknown = sorted(
        event
        for event in candidate_events
        if event
        and event not in router_events
        and not event.startswith("pm_records_control_blocker_repair_decision")
    )
    if not unknown:
        return []
    return [
        _finding(
            code="role_event_taxonomy_gap",
            severity="error",
            summary="Run artifacts contain reviewer blocker events not registered in router EXTERNAL_EVENTS.",
            matched_invariant="reviewer_block_events_are_known",
            evidence={"events": unknown[:20], "count": len(unknown)},
            minimal_fix=(
                "Register the reviewer block events as first-class EXTERNAL_EVENTS "
                "or normalize them to existing canonical blocker events before routing."
            ),
        )
    ]


ROLE_GATE_EVENT_PREFIXES = (
    "reviewer_",
    "current_node_reviewer_",
    "flowguard_operator_route_scope_",
    "flowguard_operator_product_scope_",
)
ROLE_GATE_PASS_MARKERS = (
    "passes",
    "passed",
    "approves",
    "allows",
    "sufficient",
)
ROLE_GATE_NON_PASS_MARKERS = (
    "blocks",
    "blocked",
    "insufficient",
    "requires_repair",
    "requests_repair",
    "protocol_dead_end",
    "repair_required",
)
STRUCTURED_REPORT_GATES = {
    "pm_startup_intake_card_delivered",
}


def _event_class(event_name: str) -> str:
    if any(marker in event_name for marker in ROLE_GATE_NON_PASS_MARKERS):
        return "non_pass"
    if any(marker in event_name for marker in ROLE_GATE_PASS_MARKERS):
        return "pass"
    return "other"


def _audit_gate_outcome_contracts(project_root: Path) -> list[dict[str, object]]:
    events = _load_router_external_events(project_root / "skills" / "flowpilot" / "assets" / "flowpilot_router.py")
    groups: dict[str, list[str]] = {}
    for event_name, meta in events.items():
        if bool(meta.get("unsupported_historical")):
            continue
        required_flag = str(meta.get("requires_flag") or "")
        if not required_flag:
            continue
        groups.setdefault(required_flag, []).append(event_name)

    pass_only: list[dict[str, object]] = []
    for required_flag, event_names in sorted(groups.items()):
        role_events = [
            event_name
            for event_name in event_names
            if event_name.startswith(ROLE_GATE_EVENT_PREFIXES)
        ]
        if not role_events or required_flag in STRUCTURED_REPORT_GATES:
            continue
        classes = {_event_class(event_name) for event_name in role_events}
        if "pass" in classes and "non_pass" not in classes:
            pass_only.append(
                {
                    "requires_flag": required_flag,
                    "events": sorted(role_events),
                    "expected": "pass plus non-pass repair outcome",
                }
            )

    if not pass_only:
        return []
    return [
        _finding(
            code="gate_outcome_contract_pass_only",
            severity="error",
            summary="Reviewer/FlowGuard operator gate event groups have pass outcomes without non-pass repair outcomes.",
            matched_invariant="gate_outcome_contracts_have_non_pass_paths",
            evidence={"groups": pass_only[:40], "count": len(pass_only)},
            minimal_fix=(
                "Add a Gate Outcome Contract for each role gate so pass, block, "
                "repair, and controlled-stop outcomes are all routable."
            ),
        )
    ]


def _audit_source_policy(project_root: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    audit_path = project_root / "scripts" / "audit_local_install_sync.py"
    audit_text = audit_path.read_text(encoding="utf-8") if audit_path.exists() else ""
    cockpit_present = (project_root / "flowpilot_cockpit").exists()
    if cockpit_present and (
        "unsupported_cockpit_source_absent_from_main_tree" in audit_text
        or '"flowpilot_cockpit"' in audit_text
        and "RETIRED_COCKPIT_SOURCE_PATHS" in audit_text
    ):
        findings.append(
            _finding(
                code="install_audit_layout_policy_conflict",
                severity="error",
                summary="Install sync audit still rejects flowpilot_cockpit even though Cockpit source exists in-tree.",
                matched_invariant="install_policy_matches_first_class_sources",
                evidence={
                    "cockpit_source_present": True,
                    "audit_path": _rel(project_root, audit_path),
                },
                minimal_fix=(
                    "Choose a single source-layout policy: either make flowpilot_cockpit "
                    "a first-class package checked by install audit, or move it to a "
                    "generated/ignored location. Do not keep an audit that expects it absent."
                ),
            )
        )
    repo_router = project_root / "skills" / "flowpilot" / "assets" / "flowpilot_router.py"
    installed_router = Path.home() / ".codex" / "skills" / "flowpilot" / "assets" / "flowpilot_router.py"
    if repo_router.exists() and installed_router.exists():
        try:
            if repo_router.read_bytes() != installed_router.read_bytes():
                findings.append(
                    _finding(
                        code="installed_skill_source_drift",
                        severity="error",
                        summary="Installed FlowPilot router differs from repository router.",
                        matched_invariant="install_policy_matches_first_class_sources",
                        evidence={
                            "repo_router": _rel(project_root, repo_router),
                            "installed_router": installed_router.as_posix(),
                        },
                        minimal_fix=(
                            "Run the official install/sync script after source changes and "
                            "make audit_local_install_sync verify the installed router hash."
                        ),
                    )
                )
        except OSError:
            pass
    return findings


def _audit_router_source(project_root: Path) -> list[dict[str, object]]:
    router_path = project_root / "skills" / "flowpilot" / "assets" / "flowpilot_router.py"
    if not router_path.exists():
        return []
    owner_paths = [
        router_path,
        project_root
        / "skills"
        / "flowpilot"
        / "assets"
        / "flowpilot_router_route_completion_support.py",
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in owner_paths if path.exists())
    findings: list[dict[str, object]] = []
    if "_active_node_completion_write_missing" not in text:
        findings.append(
            _finding(
                code="node_completion_idempotency_global_only",
                severity="error",
                summary="Router source lacks active-node-scoped completion idempotency helper.",
                matched_invariant="node_completion_is_idempotent_per_active_node",
                evidence={"path": _rel(project_root, router_path)},
                minimal_fix=(
                    "Gate repeated node completion by the active node completion ledger "
                    "instead of only the global node_completed_by_pm flag."
                ),
            )
        )
    return findings


def _audit_role_liveness(*, router_state: Any) -> list[dict[str, object]]:
    if not isinstance(router_state, dict):
        return []
    flags = router_state.get("flags") if isinstance(router_state.get("flags"), dict) else {}
    requested = bool(flags.get("resume_roles_restored") or flags.get("resume_roles_requested"))
    if not requested:
        return []
    ready = bool(flags.get("resume_role_bindings_rehydrated") or flags.get("resume_roles_restored"))
    blocked = bool(router_state.get("active_control_blocker"))
    if ready or blocked:
        return []
    return [
        _finding(
            code="runtime_role_liveness_unproven",
            severity="error",
            summary="Runtime-requested role binding support was requested without readiness proof or an early blocker.",
            matched_invariant="runtime_requested_roles_have_liveness_gate",
            evidence={"requested": requested, "ready": ready, "blocked": blocked},
            minimal_fix=(
                "At startup/resume, write a role readiness record for the runtime-requested roles "
                "or stop route work behind a router-visible blocker."
            ),
        )
    ]


def audit_live_run(project_root: str | Path = ".", run_id: str | None = None) -> dict[str, object]:
    """Project a live .flowpilot run into the cross-plane invariants.

    This audit is read-only and metadata-only for sealed packets. It does not
    open packet_body.md, result_body.md, report_body.md, or decision_body.md.
    """

    root = Path(project_root).resolve()
    resolved_run_id, run_root, findings = _resolve_run_root(root, run_id)
    if run_root is None or resolved_run_id is None:
        hard_failure = any(finding.get("severity") == "error" for finding in findings)
        return {
            "ok": not hard_failure,
            "skipped": True,
            "skip_reason": (
                "skipped_with_reason: no current FlowPilot run root is selected; "
                "live-run evidence is unavailable"
            ),
            "findings": findings if hard_failure else [],
            "current_run_projection": {
                "status": "missing_current_pointer" if findings else "no_current_run",
                "current_run_can_continue": False,
                "safe_to_claim_live_run_confidence": False,
                "metadata_only": True,
            },
            "projected_invariant_failures": [],
            "body_files_opened": False,
        }

    router_state, _router_error = _read_json(run_root / "router_state.json")
    frontier, _frontier_error = _read_json(run_root / "execution_frontier.json")
    snapshot, _snapshot_error = _read_json(run_root / "route_state_snapshot.json")
    packet_ledger, _packet_error = _read_json(run_root / "packet_ledger.json")
    closure, _closure_error = _read_json(run_root / "closure" / "terminal_closure_suite.json")
    lifecycle, _lifecycle_error = _read_json(run_root / "lifecycle" / "run_lifecycle.json")

    findings.extend(
        _retired_material_protocol_findings(
            project_root=root,
            run_root=run_root,
            router_state=router_state,
            frontier=frontier,
            packet_ledger=packet_ledger,
        )
    )
    findings.extend(
        _audit_terminal(
            project_root=root,
            run_root=run_root,
            router_state=router_state,
            frontier=frontier,
            closure=closure,
            lifecycle=lifecycle,
        )
    )
    findings.extend(_audit_route_snapshot(frontier=frontier, snapshot=snapshot))
    findings.extend(
        _audit_cockpit_projection(
            project_root=root,
            run_id=resolved_run_id,
            frontier=frontier,
        )
    )
    findings.extend(
        _audit_event_taxonomy(
            project_root=root,
            router_state=router_state,
            run_root=run_root,
        )
    )
    findings.extend(_audit_gate_outcome_contracts(root))
    findings.extend(_audit_source_policy(root))
    findings.extend(_audit_router_source(root))
    findings.extend(_audit_role_liveness(router_state=router_state))

    projected_state = state_from_findings(findings)
    return {
        "ok": not findings,
        "skipped": False,
        "run_id": resolved_run_id,
        "run_root": _rel(root, run_root),
        "findings": findings,
        "finding_count": len(findings),
        "projected_invariant_failures": invariant_failures(projected_state),
        "body_files_opened": False,
        "sealed_body_names_blocked": sorted(BODY_PATH_NAMES),
    }


def state_from_findings(findings: list[dict[str, object]]) -> State:
    state = _safe_base()
    codes = {str(finding.get("code") or "") for finding in findings}
    if codes.intersection(
        {
            "retired_material_protocol_authority_present",
            "retired_material_protocol_still_active",
        }
    ):
        state = replace(state, retired_material_protocol_absent=False)
    if "shallow_skill_inventory_contract_missing" in codes:
        state = replace(state, shallow_skill_inventory_preserved=False)
    if "ordinary_resource_work_became_mandatory_gate" in codes:
        state = replace(state, ordinary_resource_work_optional=False)
    if "complete_workstream_role_contract_missing" in codes:
        state = replace(state, complete_workstream_report_contract_preserved=False)
    if "terminal_authority_mismatch" in codes:
        state = replace(
            state,
            run_lifecycle_record_written=False,
            router_frontier_lifecycle_terminal_consistent=False,
        )
    if "terminal_control_blocker_not_cleared" in codes:
        state = replace(state, terminal_control_blocker_cleared=False)
    if "terminal_manual_resume_binding_still_active" in codes:
        state = replace(state, manual_resume_binding_inactive_after_terminal=False)
    if "route_state_snapshot_status_mismatch" in codes:
        state = replace(state, route_snapshot_status_derived_from_frontier=False)
    if "route_state_snapshot_completed_checklists_pending" in codes:
        state = replace(state, route_snapshot_checklists_complete_for_completed_nodes=False)
    if "selected_state_conflated_with_completed_state" in codes:
        state = replace(state, selected_status_separate_from_completion=False)
    if "cockpit_completed_node_status_mismatch" in codes:
        state = replace(state, cockpit_status_derived_from_frontier=False)
    if "cockpit_completed_node_checklist_status_mismatch" in codes:
        state = replace(state, cockpit_checklists_complete_for_completed_nodes=False)
    if "cockpit_closed_run_exposed_as_active_tab" in codes:
        state = replace(state, cockpit_closed_runs_hidden_from_active_tabs=False)
    if "role_event_taxonomy_gap" in codes:
        state = replace(state, reviewer_block_events_registered=False)
    if "role_output_event_artifact_scan_missing" in codes:
        state = replace(state, role_event_artifacts_scanned=False)
    if "gate_outcome_contract_pass_only" in codes:
        state = replace(state, gate_outcome_contracts_complete=False)
    if "node_completion_idempotency_global_only" in codes:
        state = replace(state, node_completion_idempotency_scoped_to_active_node=False)
    if "install_audit_layout_policy_conflict" in codes:
        state = replace(state, install_audit_policy_accepts_first_class_cockpit=False)
    if "installed_skill_source_drift" in codes:
        state = replace(state, installed_skill_matches_repository_source=False)
    if "runtime_role_liveness_unproven" in codes:
        state = replace(state, role_liveness_ready_or_blocked=False)
    return state


__all__ = [
    "CURRENT_ROLE_CARD_PATHS",
    "ROLE_GATE_EVENT_PREFIXES",
    "ROLE_GATE_NON_PASS_MARKERS",
    "ROLE_GATE_PASS_MARKERS",
    "RETIRED_MATERIAL_CARD_IDS",
    "RETIRED_MATERIAL_EVENTS",
    "RETIRED_MATERIAL_FIELDS",
    "RETIRED_MATERIAL_PACKET_FAMILIES",
    "STRUCTURED_REPORT_GATES",
    "audit_current_prework_sources",
    "audit_live_run",
    "state_from_findings",
]

