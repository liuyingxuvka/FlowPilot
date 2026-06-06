"""Internal router owner helpers extracted from flowpilot_router.

The public router names stay in flowpilot_router. This module is bound to
that facade before moved helpers execute so private helper lookups remain
stable while the implementation body lives outside the facade.
"""
from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any, Iterable

from flowpilot_router_protocol_catalog import *

_DEFAULT_SENTINEL = object()
_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router facade is not bound")
    return _BOUND_ROUTER
OWNER_MODULE = "flowpilot_router_self_interrogation"
def _self_interrogation_index_path(run_root: Path) -> Path:
    return run_root / "self_interrogation_index.json"
def _self_interrogation_issue(
    message: str,
    *,
    record_id: str = "",
    record_path: str = "",
    scope: str = "",
) -> dict[str, str]:
    issue = {"message": message}
    if record_id:
        issue["record_id"] = record_id
    if record_path:
        issue["record_path"] = record_path
    if scope:
        issue["scope"] = scope
    return issue
def _self_interrogation_entry_path(entry: dict[str, Any]) -> str:
    return str(entry.get("record_path") or entry.get("path") or "")
def _self_interrogation_final_status(status: str) -> bool:
    return status in SELF_INTERROGATION_FINAL_DISPOSITIONS
def _self_interrogation_record_issues(
    project_root: Path,
    run_root: Path,
    record_path: Path,
    record: dict[str, Any],
    *,
    expected_scope: str | None = None,
    expected_node_id: str | None = None,
    expected_route_version: int | None = None,
) -> tuple[list[dict[str, str]], int]:
    record_rel = project_relative(project_root, record_path)
    record_id = str(record.get("record_id") or record_path.stem)
    scope = str(record.get("scope") or "")
    issues: list[dict[str, str]] = []
    unresolved_hard_count = 0

    def add(message: str) -> None:
        issues.append(_self_interrogation_issue(message, record_id=record_id, record_path=record_rel, scope=scope))

    if record.get("schema_version") != SELF_INTERROGATION_RECORD_SCHEMA:
        add(f"schema_version must be {SELF_INTERROGATION_RECORD_SCHEMA}")
    if not record.get("record_id"):
        add("record_id is required")
    if scope not in SELF_INTERROGATION_SCOPES:
        add("scope must be a supported self-interrogation scope")
    if expected_scope and scope != expected_scope:
        add(f"scope must be {expected_scope}")
    if not record.get("owner_role"):
        add("owner_role is required")
    if not record.get("source_event"):
        add("source_event is required")
    raw_source_path = str(record.get("source_artifact_path") or "")
    if not raw_source_path:
        add("source_artifact_path is required")
    else:
        source_path = resolve_project_path(project_root, raw_source_path)
        if not source_path.exists():
            add(f"source_artifact_path does not exist: {raw_source_path}")
    if expected_node_id and scope in {"node_entry", "repair", "role_result"}:
        if str(record.get("node_id") or "") != expected_node_id:
            add(f"node_id must match active node {expected_node_id}")
    if expected_route_version is not None and record.get("route_version") is not None:
        try:
            record_route_version = int(record.get("route_version"))
        except (TypeError, ValueError):
            add("route_version must be an integer when present")
        else:
            if record_route_version != expected_route_version:
                add(f"route_version must match active route version {expected_route_version}")

    findings = record.get("findings")
    if not isinstance(findings, list):
        add("findings must be a list")
        findings = []
    for index, finding in enumerate(findings, start=1):
        if not isinstance(finding, dict):
            add(f"findings[{index}] must be an object")
            continue
        finding_id = str(finding.get("finding_id") or f"finding-{index}")
        severity = str(finding.get("severity") or "")
        disposition = finding.get("disposition") if isinstance(finding.get("disposition"), dict) else {}
        disposition_status = str(disposition.get("status") or "")
        for field in ("finding_id", "severity", "category", "summary"):
            if not finding.get(field):
                add(f"finding {finding_id} missing {field}")
        if not disposition_status:
            add(f"finding {finding_id} missing disposition.status")
        hard_or_current = severity in SELF_INTERROGATION_HARD_SEVERITIES or finding.get("blocks_current_gate_until_disposition") is True
        if hard_or_current and not _self_interrogation_final_status(disposition_status):
            unresolved_hard_count += 1
            add(f"finding {finding_id} is unresolved for a hard/current self-interrogation finding")
        if disposition_status == "reject_with_reason" and not disposition.get("reason"):
            add(f"finding {finding_id} reject_with_reason requires reason")
        if disposition_status == "waive_with_authority" and (
            not disposition.get("reason") or not disposition.get("waiver_authority_role")
        ):
            add(f"finding {finding_id} waive_with_authority requires reason and waiver_authority_role")
        if disposition_status == "defer_to_named_node" and not disposition.get("target_node_or_gate_id"):
            add(f"finding {finding_id} defer_to_named_node requires target_node_or_gate_id")
        if disposition_status == "entered_pm_suggestion_ledger" and not (
            disposition.get("suggestion_id") or record.get("pm_suggestion_ledger_ids")
        ):
            add(f"finding {finding_id} entered_pm_suggestion_ledger requires a suggestion id")
        if disposition_status == "incorporated_into_artifact" and not (
            disposition.get("artifact_path") or record.get("downstream_artifact_paths")
        ):
            add(f"finding {finding_id} incorporated_into_artifact requires downstream artifact evidence")

    try:
        declared_unresolved = int(record.get("unresolved_hard_finding_count", 0) or 0)
    except (TypeError, ValueError):
        declared_unresolved = -1
        add("unresolved_hard_finding_count must be an integer")
    if declared_unresolved > 0:
        unresolved_hard_count = max(unresolved_hard_count, declared_unresolved)
        add("record declares unresolved hard/current self-interrogation findings")
    disposition_summary = record.get("pm_disposition_summary")
    if not isinstance(disposition_summary, dict):
        add("pm_disposition_summary must be an object")
    for field in ("downstream_artifact_paths", "pm_suggestion_ledger_ids"):
        if not isinstance(record.get(field), list):
            add(f"{field} must be a list")
    if run_root.name and record.get("run_id") and str(record.get("run_id")) != run_root.name:
        add("run_id must match current run")

    return issues, unresolved_hard_count
def _self_interrogation_status(
    project_root: Path,
    run_root: Path,
    *,
    scopes: Iterable[str] | None = None,
    node_id: str | None = None,
    route_version: int | None = None,
    require_index: bool = True,
    require_records: bool = True,
) -> dict[str, Any]:
    index_path = _self_interrogation_index_path(run_root)
    index_rel = project_relative(project_root, index_path)
    issues: list[dict[str, str]] = []
    scope_filter = {str(scope) for scope in scopes} if scopes is not None else None
    records: list[dict[str, Any]] = []
    matched_scopes: set[str] = set()
    unresolved_hard_count = 0

    if not index_path.exists():
        if require_index:
            issues.append(_self_interrogation_issue("self-interrogation index is missing", record_path=index_rel))
        return {
            "path": str(index_path),
            "exists": False,
            "record_count": 0,
            "unresolved_hard_finding_count": unresolved_hard_count,
            "issue_count": len(issues),
            "clean": not issues,
            "issues": issues,
        }

    index = read_json(index_path)
    if index.get("schema_version") != SELF_INTERROGATION_INDEX_SCHEMA:
        issues.append(_self_interrogation_issue(f"index schema_version must be {SELF_INTERROGATION_INDEX_SCHEMA}", record_path=index_rel))
    raw_entries = index.get("records")
    if raw_entries is None:
        raw_entries = index.get("entries")
    if not isinstance(raw_entries, list):
        issues.append(_self_interrogation_issue("self-interrogation index records must be a list", record_path=index_rel))
        raw_entries = []

    for entry in raw_entries:
        if not isinstance(entry, dict):
            issues.append(_self_interrogation_issue("self-interrogation index entry must be an object", record_path=index_rel))
            continue
        entry_scope = str(entry.get("scope") or "")
        if scope_filter is not None and entry_scope and entry_scope not in scope_filter:
            continue
        raw_record_path = _self_interrogation_entry_path(entry)
        if not raw_record_path:
            issues.append(_self_interrogation_issue("self-interrogation index entry requires record_path", record_path=index_rel, scope=entry_scope))
            continue
        record_path = resolve_project_path(project_root, raw_record_path)
        record_rel = project_relative(project_root, record_path)
        if not record_path.exists():
            issues.append(_self_interrogation_issue("self-interrogation record path is missing", record_path=record_rel, scope=entry_scope))
            continue
        record = read_json(record_path)
        record_scope = str(record.get("scope") or entry_scope)
        if scope_filter is not None and record_scope not in scope_filter:
            continue
        if node_id and record_scope in {"node_entry", "repair", "role_result"}:
            entry_node_id = str(entry.get("node_id") or "")
            record_node_id = str(record.get("node_id") or entry_node_id)
            if record_node_id != node_id:
                continue
        if route_version is not None:
            raw_route_version = record.get("route_version", entry.get("route_version"))
            if raw_route_version is not None:
                try:
                    if int(raw_route_version) != route_version:
                        continue
                except (TypeError, ValueError):
                    issues.append(_self_interrogation_issue("route_version must be an integer", record_path=record_rel, scope=record_scope))
                    continue
        matched_scopes.add(record_scope)
        record_issues, record_unresolved = _self_interrogation_record_issues(
            project_root,
            run_root,
            record_path,
            record,
            expected_scope=record_scope,
            expected_node_id=node_id,
            expected_route_version=route_version,
        )
        issues.extend(record_issues)
        unresolved_hard_count += record_unresolved
        records.append(
            {
                "record_id": str(record.get("record_id") or record_path.stem),
                "scope": record_scope,
                "path": record_rel,
                "unresolved_hard_finding_count": record_unresolved,
            }
        )

    if require_records and not records:
        if scope_filter:
            issues.append(
                _self_interrogation_issue(
                    "missing required self-interrogation record scope(s): " + ", ".join(sorted(scope_filter)),
                    record_path=index_rel,
                )
            )
        else:
            issues.append(_self_interrogation_issue("self-interrogation index has no records", record_path=index_rel))
    if scope_filter:
        missing_scopes = sorted(scope_filter - matched_scopes)
        if missing_scopes:
            issues.append(
                _self_interrogation_issue(
                    "missing required self-interrogation record scope(s): " + ", ".join(missing_scopes),
                    record_path=index_rel,
                )
            )

    return {
        "path": str(index_path),
        "exists": True,
        "record_count": len(records),
        "unresolved_hard_finding_count": unresolved_hard_count,
        "issue_count": len(issues),
        "clean": not issues and unresolved_hard_count == 0,
        "issues": issues,
        "records": records,
    }
from flowpilot_router_self_interrogation_records_requirements import (
    _format_self_interrogation_status_issue,
    _require_clean_self_interrogation,
    resolve_project_path,
)

__all__ = (
    "_self_interrogation_index_path",
    "_self_interrogation_issue",
    "_self_interrogation_entry_path",
    "_self_interrogation_final_status",
    "_self_interrogation_record_issues",
    "_self_interrogation_status",
    "_format_self_interrogation_status_issue",
    "_require_clean_self_interrogation",
    "resolve_project_path",
)
_LOCAL_NAMES = set(globals())
