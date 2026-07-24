"""Read-only verification of current V5 selective test-tier evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from flowguard import proof_artifact_gap_codes, test_result_reuse_gap_codes

from .background import (
    _read_background_meta,
    _read_exit_code,
    artifact_paths,
    background_supervisor_name,
)
from .background_supervisor import supervisor_control_paths
from .definitions import TierCommand
from .evidence_v5 import (
    BACKGROUND_OWNER_INDEX_SCHEMA_VERSION,
    BACKGROUND_SUPERVISOR_META_SCHEMA_VERSION,
    BACKGROUND_SUPERVISOR_PROGRESS_SCHEMA_VERSION,
    bounded_failure_excerpt,
    load_json_object,
    resolve_artifact_path,
    sha256_file,
    sha256_json,
)
from .impact_resolution import (
    IMPACT_PLAN_SCHEMA_VERSION,
    _current_reuse_ticket,
    build_owner_contracts,
    owner_identity,
    validate_owner_reference,
)


ROOT = Path(__file__).resolve().parents[2]


def _load_exact_ref(
    value: object,
    *,
    expected_path: Path,
) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(value, Mapping):
        return None, "artifact_ref_missing"
    path_value = str(value.get("path") or "")
    if not path_value:
        return None, "artifact_ref_path_missing"
    path = resolve_artifact_path(ROOT, path_value)
    if path != expected_path.resolve():
        return None, "artifact_ref_path_mismatch"
    if not path.is_file():
        return None, "artifact_ref_target_missing"
    if str(value.get("sha256") or "") != sha256_file(path):
        return None, "artifact_ref_sha256_mismatch"
    if int(value.get("bytes") or -1) != path.stat().st_size:
        return None, "artifact_ref_bytes_mismatch"
    try:
        return load_json_object(path), None
    except ValueError as exc:
        return None, str(exc)


def verify_background_tier(
    tier: str,
    commands: Sequence[TierCommand],
    *,
    log_root: Path,
) -> dict[str, Any]:
    """Verify one immutable V5 run root without launching or rewriting it."""

    failures: list[str] = []
    supervisor_paths = artifact_paths(log_root, background_supervisor_name(tier))
    control_paths = supervisor_control_paths(log_root, tier)
    missing_supervisor = [
        key for key, path in supervisor_paths.items() if not path.is_file()
    ]
    if missing_supervisor:
        failures.append(
            "supervisor_missing_artifacts:" + ",".join(sorted(missing_supervisor))
        )
    meta, meta_error = _read_background_meta(supervisor_paths["meta"])
    exit_code = _read_exit_code(supervisor_paths["exit"])
    if meta_error:
        failures.append(f"supervisor_{meta_error}")
    meta = meta or {}
    if meta.get("schema_version") != BACKGROUND_SUPERVISOR_META_SCHEMA_VERSION:
        failures.append("supervisor_meta_not_v2")
    if meta.get("status") != "passed" or exit_code != 0:
        failures.append("supervisor_not_passed")
    if int(meta.get("command_count") or -1) != len(commands):
        failures.append("supervisor_command_count_mismatch")
    if int(meta.get("running_owner_count") or 0) != 0:
        failures.append("supervisor_still_running")

    impact_plan, plan_error = _load_exact_ref(
        meta.get("impact_plan_ref"),
        expected_path=control_paths["impact_plan"],
    )
    if plan_error:
        failures.append("impact_plan_" + plan_error)
    impact_plan = impact_plan or {}
    if impact_plan.get("schema_version") != IMPACT_PLAN_SCHEMA_VERSION:
        failures.append("current_impact_plan_missing")
    if impact_plan.get("blockers"):
        failures.append("impact_plan_blocked")

    owner_index, owner_index_error = _load_exact_ref(
        meta.get("owner_index_ref"),
        expected_path=control_paths["owner_index"],
    )
    if owner_index_error:
        failures.append("owner_index_" + owner_index_error)
    owner_index = owner_index or {}
    if owner_index.get("schema_version") != BACKGROUND_OWNER_INDEX_SCHEMA_VERSION:
        failures.append("owner_index_not_current")
    if owner_index.get("impact_plan_id") != impact_plan.get("plan_id"):
        failures.append("owner_index_plan_id_mismatch")
    impact_ref = meta.get("impact_plan_ref")
    if (
        isinstance(impact_ref, Mapping)
        and owner_index.get("impact_plan_sha256") != impact_ref.get("sha256")
    ):
        failures.append("owner_index_plan_sha256_mismatch")

    progress, progress_error = _load_exact_ref(
        meta.get("progress_ref"),
        expected_path=control_paths["progress"],
    )
    if progress_error:
        failures.append("progress_" + progress_error)
    progress = progress or {}
    if (
        progress.get("schema_version")
        != BACKGROUND_SUPERVISOR_PROGRESS_SCHEMA_VERSION
    ):
        failures.append("progress_not_current")
    if progress.get("status") != "passed":
        failures.append("progress_not_terminal_pass")

    expected_names = {command.name for command in commands}
    owner_rows = owner_index.get("owners")
    if not isinstance(owner_rows, list):
        failures.append("owner_evidence_rows_missing")
        owner_rows = []
    owner_ids = [
        str(row.get("owner_id") or "")
        for row in owner_rows
        if isinstance(row, Mapping)
    ]
    if len(owner_ids) != len(set(owner_ids)):
        failures.append("duplicate_owner_ref")
    owners = {
        str(row.get("owner_id") or ""): row
        for row in owner_rows
        if isinstance(row, Mapping)
    }
    if set(owners) != expected_names:
        failures.append("owner_evidence_set_mismatch")
    if set(owner_index.get("expected_owner_ids") or ()) != expected_names:
        failures.append("owner_inventory_mismatch")

    decisions = {
        str(row.get("owner_id") or ""): row
        for row in impact_plan.get("decisions") or ()
        if isinstance(row, Mapping)
    }
    if set(decisions) != expected_names:
        failures.append("impact_decision_set_mismatch")

    contracts = {
        contract.owner_id: contract for contract in build_owner_contracts(commands)
    }
    child_reports: list[dict[str, Any]] = []
    fingerprint_cache: dict[str, str] = {}
    for owner_id in sorted(expected_names):
        row_failures: list[str] = []
        row = owners.get(owner_id)
        decision = decisions.get(owner_id)
        if not isinstance(row, Mapping):
            row_failures.append("owner_evidence_missing")
            row = {}
        if not isinstance(decision, Mapping):
            row_failures.append("owner_decision_missing")
            decision = {}
        expected_identity = owner_identity(
            contracts[owner_id],
            fingerprint_cache=fingerprint_cache,
        )
        if row.get("identity_sha256") != sha256_json(expected_identity.to_dict()):
            row_failures.append("owner_applicability_identity_stale")

        try:
            resolved = validate_owner_reference(
                row,
                expected_owner_id=owner_id,
            )
        except (TypeError, ValueError) as exc:
            resolved = None
            row_failures.append(str(exc))
        if resolved is not None:
            row_failures.extend(
                code
                for code, _ in proof_artifact_gap_codes(
                    resolved.proof,
                    declared_status=str(row.get("result_status") or ""),
                    required_obligation_ids=contracts[
                        owner_id
                    ].covered_obligation_ids,
                    require_result_path=True,
                    require_fingerprints=True,
                )
            )

        action = str(decision.get("action") or "")
        if row.get("action") != action:
            row_failures.append("owner_action_mismatch")
        reused = row.get("result_reused") is True
        if action == "reuse":
            if not reused:
                row_failures.append("reuse_decision_missing_reused_row")
            ticket = (
                _current_reuse_ticket(
                    owner_id,
                    resolved,
                    expected_identity,
                )
                if resolved is not None
                else None
            )
            row_failures.extend(
                code
                for code, _ in test_result_reuse_gap_codes(
                    ticket,
                    expected_evidence_id=owner_id,
                    required_obligation_ids=contracts[
                        owner_id
                    ].covered_obligation_ids,
                )
            )
            ticket_ref = row.get("reuse_ticket_ref")
            if not isinstance(ticket_ref, Mapping):
                row_failures.append("reuse_ticket_ref_missing")
            elif ticket is not None and ticket_ref.get("identity") != sha256_json(
                ticket.to_dict()
            ):
                row_failures.append("reuse_ticket_ref_stale")
        elif action == "execute":
            if reused:
                row_failures.append("executed_owner_marked_reused")
            if row.get("reuse_ticket_ref") is not None:
                row_failures.append("executed_owner_has_reuse_ticket_ref")
            child_paths = artifact_paths(log_root, owner_id)
            missing = [
                key for key, path in child_paths.items() if not path.is_file()
            ]
            if missing:
                row_failures.append(
                    "executed_owner_missing_artifacts:" + ",".join(sorted(missing))
                )
            child_meta, child_error = _read_background_meta(child_paths["meta"])
            if child_error:
                row_failures.append(child_error)
            child_meta = child_meta or {}
            if child_meta.get("inputs_current") is not True:
                row_failures.append("executed_owner_inputs_stale")
            if child_meta.get("descendant_zero_confirmed") is not True:
                row_failures.append("executed_owner_cleanup_unconfirmed")
            if child_meta.get("status") != "passed":
                row_failures.append("executed_owner_not_passed")
        else:
            row_failures.append(f"unsupported_owner_action:{action}")

        failures.extend(f"{owner_id}:{reason}" for reason in row_failures)
        child_reports.append(
            {
                "name": owner_id,
                "ok": not row_failures,
                "action": action,
                "status": row.get("result_status"),
                "failures": row_failures,
            }
        )

    excerpt = (
        bounded_failure_excerpt(
            (
                ("stderr", supervisor_paths["err"]),
                ("stdout", supervisor_paths["out"]),
            )
        )
        if failures
        else None
    )
    return {
        "ok": not failures,
        "tier": tier,
        "log_root": str(log_root),
        "impact_plan_id": impact_plan.get("plan_id"),
        "impact_plan_ref": meta.get("impact_plan_ref"),
        "owner_index_ref": meta.get("owner_index_ref"),
        "snapshot_fingerprint": (
            impact_plan.get("snapshot", {}).get("fingerprint")
            if isinstance(impact_plan.get("snapshot"), Mapping)
            else None
        ),
        "selected_count": len(commands),
        "executed_count": sum(
            1 for row in child_reports if row["action"] == "execute"
        ),
        "reused_count": sum(
            1 for row in child_reports if row["action"] == "reuse"
        ),
        "verified_count": sum(1 for row in child_reports if row["ok"]),
        "failures": sorted(set(failures)),
        "failure_excerpt": excerpt,
        "children": child_reports,
    }


__all__ = ["verify_background_tier"]
