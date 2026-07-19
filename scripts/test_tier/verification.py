"""Read-only verification of current v4 selective test-tier evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from flowguard import (
    ProofArtifactRef,
    TestResultReuseTicket,
    proof_artifact_gap_codes,
    test_result_reuse_gap_codes,
)

from .background import (
    _read_background_meta,
    _read_exit_code,
    artifact_paths,
    background_supervisor_name,
)
from .definitions import TierCommand
from .impact_resolution import IMPACT_PLAN_SCHEMA_VERSION, build_owner_contracts, owner_identity


def verify_background_tier(
    tier: str,
    commands: Sequence[TierCommand],
    *,
    log_root: Path,
) -> dict[str, Any]:
    """Verify one immutable v4 run root without launching or rewriting it."""

    failures: list[str] = []
    supervisor_paths = artifact_paths(log_root, background_supervisor_name(tier))
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
    if meta.get("status") != "passed" or exit_code != 0:
        failures.append("supervisor_not_passed")
    impact_plan = meta.get("impact_plan")
    if (
        not isinstance(impact_plan, dict)
        or impact_plan.get("schema_version") != IMPACT_PLAN_SCHEMA_VERSION
    ):
        failures.append("current_impact_plan_missing")
        impact_plan = {}
    if impact_plan.get("blockers"):
        failures.append("impact_plan_blocked")
    if int(meta.get("command_count") or -1) != len(commands):
        failures.append("supervisor_command_count_mismatch")
    if meta.get("running"):
        failures.append("supervisor_still_running")

    owners = meta.get("owners")
    if not isinstance(owners, dict):
        failures.append("owner_evidence_rows_missing")
        owners = {}
    expected_names = {command.name for command in commands}
    if set(owners) != expected_names:
        failures.append("owner_evidence_set_mismatch")

    decisions = {
        str(row.get("owner_id") or ""): row
        for row in impact_plan.get("decisions") or ()
        if isinstance(row, dict)
    }
    if set(decisions) != expected_names:
        failures.append("impact_decision_set_mismatch")

    contracts = {contract.owner_id: contract for contract in build_owner_contracts(commands)}
    child_reports: list[dict[str, Any]] = []
    for owner_id in sorted(expected_names):
        row_failures: list[str] = []
        row = owners.get(owner_id)
        decision = decisions.get(owner_id)
        if not isinstance(row, dict):
            row_failures.append("owner_evidence_missing")
            row = {}
        if not isinstance(decision, dict):
            row_failures.append("owner_decision_missing")
            decision = {}
        expected_identity = owner_identity(contracts[owner_id]).to_dict()
        if row.get("identity") != expected_identity:
            row_failures.append("owner_applicability_identity_stale")

        proof_value = row.get("proof_artifact")
        try:
            proof = (
                ProofArtifactRef(**dict(proof_value))
                if isinstance(proof_value, dict)
                else None
            )
        except (TypeError, ValueError):
            proof = None
        proof_gaps = proof_artifact_gap_codes(
            proof,
            declared_status=str(row.get("result_status") or ""),
            required_obligation_ids=contracts[owner_id].covered_obligation_ids,
            require_result_path=True,
            require_fingerprints=True,
        )
        row_failures.extend(code for code, _ in proof_gaps)

        action = str(decision.get("action") or "")
        reused = row.get("result_reused") is True
        if action == "reuse":
            if not reused:
                row_failures.append("reuse_decision_missing_reused_row")
            ticket_value = row.get("reuse_ticket")
            try:
                ticket = (
                    TestResultReuseTicket(**dict(ticket_value))
                    if isinstance(ticket_value, dict)
                    else None
                )
            except (TypeError, ValueError):
                ticket = None
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
        elif action == "execute":
            if reused:
                row_failures.append("executed_owner_marked_reused")
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

    return {
        "ok": not failures,
        "tier": tier,
        "log_root": str(log_root),
        "impact_plan_id": impact_plan.get("plan_id"),
        "snapshot_fingerprint": (
            impact_plan.get("snapshot", {}).get("fingerprint")
            if isinstance(impact_plan.get("snapshot"), dict)
            else None
        ),
        "selected_count": len(commands),
        "executed_count": sum(
            1 for row in child_reports if row["action"] == "execute"
        ),
        "reused_count": sum(1 for row in child_reports if row["action"] == "reuse"),
        "verified_count": sum(1 for row in child_reports if row["ok"]),
        "failures": sorted(set(failures)),
        "children": child_reports,
    }


__all__ = ["verify_background_tier"]
