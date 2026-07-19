"""Run focused checks for the FlowPilot unified repair integrity model.

The runner owns the executable model, generated same-class cases, conservative
source audit, and child/parent receipt projection.  It never executes native
runtime tests.  Current product conformance is fail-closed unless one explicit
evidence manifest supplies exact immutable terminal-success receipts from the
frozen native runtime and native-test owners.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from flowguard import CompositeHandoffAcceptance, ModelContractCoverageReceipt
from flowguard.explorer import Explorer

try:  # pragma: no cover - package execution
    from . import flowpilot_unified_repair_integrity_model as model
except ImportError:  # pragma: no cover - direct script execution
    import flowpilot_unified_repair_integrity_model as model


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
MODEL_PATH = ROOT / "flowpilot_unified_repair_integrity_model.py"
RUNNER_PATH = Path(__file__).resolve()
RESULTS_PATH = ROOT / "flowpilot_unified_repair_integrity_results.json"
RUNTIME_ROOT = (
    REPO_ROOT
    / "skills"
    / "flowpilot"
    / "assets"
    / "flowpilot_core_runtime"
)
CORE_RUNTIME_PATH = RUNTIME_ROOT / "runtime.py"
RUN_SHELL_PATH = RUNTIME_ROOT / "run_shell.py"
MIGRATION_PATH = RUNTIME_ROOT / "migration.py"
POINTER_STORE_PATH = RUNTIME_ROOT / "pointer_store.py"
CONTROL_SURFACE_PATH = RUNTIME_ROOT / "control_surface.py"
UNIFIED_RUNTIME_SOURCE_PATHS = (
    CORE_RUNTIME_PATH,
    RUN_SHELL_PATH,
    MIGRATION_PATH,
    POINTER_STORE_PATH,
    CONTROL_SURFACE_PATH,
)
NATIVE_RUNTIME_OWNER_PATH = (
    ROOT / "run_flowpilot_unified_repair_native_runtime_conformance.py"
)
NATIVE_RUNTIME_FIXTURE_PATH = (
    REPO_ROOT / "tests" / "flowpilot_repair_test_helpers.py"
)
EXACT_NATIVE_TEST_OWNER_PATH = (
    ROOT / "run_flowpilot_unified_repair_exact_native_test_owner.py"
)
EXACT_RELEVANT_TEST_PATHS = (
    REPO_ROOT / "tests" / "test_flowpilot_unified_repair_runtime.py",
    REPO_ROOT / "tests" / "test_flowpilot_core_runtime.py",
    REPO_ROOT / "tests" / "test_flowpilot_high_standard_control_flow.py",
    REPO_ROOT / "tests" / "test_flowpilot_complete_system_runtime.py",
    REPO_ROOT / "tests" / "test_flowpilot_terminal_ledger_source_entries.py",
    REPO_ROOT / "tests" / "router_runtime" / "route_mutation_transactions.py",
    REPO_ROOT / "tests" / "router_runtime" / "route_mutation_parent_backward.py",
    REPO_ROOT / "tests" / "router_runtime" / "route_mutation_sibling_replacement.py",
)

SOURCE_FINGERPRINT_INPUTS = (MODEL_PATH, RUNNER_PATH)
SOURCE_FINGERPRINT_ALGORITHM = "sha256(path_utf8+nul+raw_bytes+nul), ordered:model,runner"
NATIVE_EVIDENCE_MANIFEST_SCHEMA = (
    "flowpilot.unified_repair_native_evidence_manifest.v1"
)
UNIFIED_REPAIR_OBLIGATION_IDS = (
    "unified_repair.pm_historical_direct_entry_no_blocker",
    "unified_repair.same_slot_replacement_single_authority",
    "unified_repair.repair_child_under_active_replacement",
    "unified_repair.worker_flowguard_reviewer_chain",
    "unified_repair.contract_evidence_generation",
    "unified_repair.decision_gate_before_effect_commit",
    "unified_repair.unaffected_sibling_rebind_conservation",
    "unified_repair.affected_downstream_replay",
    "unified_repair.repeated_lineage_generation",
    "unified_repair.terminal_shared_engine",
    "unified_repair.terminal_round_cap_three",
    "unified_repair.completed_run_distinct_current_import",
    "unified_repair.action_runtime_refinement",
)
REQUIRED_NATIVE_RECEIPTS = {
    "native_runtime_conformance": {
        "receipt_id": "receipt.unified_repair.native_runtime_conformance",
        "execution_owner": "native.unified_repair.runtime_conformance",
        "required_input_groups": (
            "unified_runtime_sources",
            "native_runtime_owner",
            "native_runtime_fixture",
        ),
        "covered_obligation_ids": UNIFIED_REPAIR_OBLIGATION_IDS,
    },
    "exact_native_test_conformance": {
        "receipt_id": "receipt.unified_repair.exact_native_tests",
        "execution_owner": "native.unified_repair.exact_runtime_tests",
        "required_input_groups": (
            "unified_runtime_sources",
            "exact_relevant_tests",
            "exact_native_test_owner",
        ),
        "covered_obligation_ids": UNIFIED_REPAIR_OBLIGATION_IDS,
    },
}
WAIVER_TYPED_EVIDENCE_ID = "evidence.unified_repair.authorized_waiver_semantics"
REQUIRED_CONSUMER_IDS = (
    "flowguard-contract-exhaustion-mesh",
    "flowguard-model-test-alignment",
    "flowguard-test-mesh",
    "flowguard-model-mesh",
    "flowguard-development-process-flow",
    "meta.terminal_ledger",
    "capability.child_skill_capability",
    "capability.terminal_ledger",
    "flowpilot-model-maturation",
    "flowpilot-final-confidence",
    "flowguard-behavior-commitment-ledger",
)
NATIVE_EXECUTION_OWNER_INVENTORY = (
    {
        "check_id": "unified_repair.model_runner",
        "check_kind": "model_runner",
        "execution_owner": "runner.unified_repair.integrity",
        "dependencies": (),
    },
    {
        "check_id": "unified_repair.source_audit",
        "check_kind": "source_audit",
        "execution_owner": "runner.unified_repair.integrity",
        "dependencies": ("unified_repair.model_runner",),
    },
    {
        "check_id": "unified_repair.synthetic_replay",
        "check_kind": "synthetic_replay",
        "execution_owner": "runner.unified_repair.integrity",
        "dependencies": ("unified_repair.model_runner",),
    },
    {
        "check_id": "native_runtime_conformance",
        "check_kind": "native_runtime",
        "execution_owner": "native.unified_repair.runtime_conformance",
        "dependencies": ("unified_repair.source_audit",),
    },
    {
        "check_id": "exact_native_test_conformance",
        "check_kind": "ordinary_test",
        "execution_owner": "native.unified_repair.exact_runtime_tests",
        "dependencies": ("native_runtime_conformance",),
    },
    {
        "check_id": "unified_repair.parent_receipt",
        "check_kind": "parent_receipt",
        "execution_owner": "runner.unified_repair.integrity",
        "dependencies": (
            "unified_repair.model_runner",
            "unified_repair.source_audit",
            "native_runtime_conformance",
            "exact_native_test_conformance",
        ),
    },
)


def _relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def _file_fingerprint(path: Path) -> dict[str, object]:
    exists = path.is_file()
    data = path.read_bytes() if exists else b""
    return {
        "path": _relative(path),
        "exists": exists,
        "sha256": hashlib.sha256(data).hexdigest() if exists else "",
        "size_bytes": len(data),
    }


def _combined_source_fingerprint(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        relative = _relative(path)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _source_fingerprints() -> dict[str, object]:
    return {
        "model": _file_fingerprint(MODEL_PATH),
        "runner": _file_fingerprint(RUNNER_PATH),
        "unified_runtime_sources": [
            _file_fingerprint(path)
            for path in UNIFIED_RUNTIME_SOURCE_PATHS
        ],
        "native_runtime_owner": _file_fingerprint(
            NATIVE_RUNTIME_OWNER_PATH
        ),
        "native_runtime_fixture": _file_fingerprint(
            NATIVE_RUNTIME_FIXTURE_PATH
        ),
        "exact_native_test_owner": _file_fingerprint(
            EXACT_NATIVE_TEST_OWNER_PATH
        ),
        "exact_relevant_tests": [_file_fingerprint(path) for path in EXACT_RELEVANT_TEST_PATHS],
    }


def _flatten_fingerprint_groups(
    source_fingerprints: Mapping[str, object],
    groups: Sequence[str],
) -> dict[str, str]:
    rows: list[Mapping[str, object]] = []
    for group in groups:
        value = source_fingerprints.get(group)
        if isinstance(value, Mapping):
            rows.append(value)
        elif isinstance(value, list):
            rows.extend(item for item in value if isinstance(item, Mapping))
    return {
        str(row.get("path") or ""): str(row.get("sha256") or "")
        for row in rows
        if row.get("exists") is True
        and str(row.get("path") or "")
        and str(row.get("sha256") or "")
    }


def _string_sequence(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple, set, frozenset)):
        return ()
    return tuple(str(item) for item in value if str(item))


def native_receipt_request_identity(receipt: Mapping[str, object]) -> str:
    """Return the frozen request identity expected from a native owner."""

    payload = {
        "check_id": str(receipt.get("check_id") or ""),
        "execution_owner": str(receipt.get("execution_owner") or ""),
        "command": str(receipt.get("command") or ""),
        "covered_obligation_ids": sorted(
            _string_sequence(receipt.get("covered_obligation_ids"))
        ),
        "input_fingerprints": dict(
            sorted(
                (
                    str(path),
                    str(fingerprint),
                )
                for path, fingerprint in (
                    receipt.get("input_fingerprints", {}).items()
                    if isinstance(
                        receipt.get("input_fingerprints"), Mapping
                    )
                    else ()
                )
            )
        ),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _artifact_path(value: object) -> Path | None:
    text = str(value or "")
    if not text:
        return None
    path = Path(text)
    candidate = path if path.is_absolute() else REPO_ROOT / path
    try:
        resolved = candidate.resolve()
        resolved.relative_to(REPO_ROOT.resolve())
    except (OSError, ValueError):
        return None
    return resolved


def _native_evidence_report(
    evidence_manifest: Mapping[str, object] | None,
    source_fingerprints: Mapping[str, object],
) -> dict[str, object]:
    failures: list[str] = []
    manifest = evidence_manifest if isinstance(evidence_manifest, Mapping) else {}
    if not manifest:
        failures.append("native_evidence_manifest_missing")
    if manifest.get("schema_version") != NATIVE_EVIDENCE_MANIFEST_SCHEMA:
        failures.append("native_evidence_manifest_schema_mismatch")
    if manifest.get("model_id") != model.MODEL_ID:
        failures.append("native_evidence_manifest_model_id_mismatch")

    receipt_rows = manifest.get("receipts")
    receipts = (
        [row for row in receipt_rows if isinstance(row, Mapping)]
        if isinstance(receipt_rows, list)
        else []
    )
    receipt_by_check: dict[str, list[Mapping[str, object]]] = {}
    for row in receipts:
        receipt_by_check.setdefault(str(row.get("check_id") or ""), []).append(
            row
        )

    validated_rows: list[dict[str, object]] = []
    covered_obligations: set[str] = set()
    evidence_ids_by_check: dict[str, list[str]] = {}
    current_receipt_ids: set[str] = set()
    for check_id, requirement in REQUIRED_NATIVE_RECEIPTS.items():
        candidates = receipt_by_check.get(check_id, [])
        row_failures: list[str] = []
        if len(candidates) != 1:
            row_failures.append(
                f"{check_id}:receipt_cardinality_{len(candidates)}"
            )
            row: Mapping[str, object] = {}
        else:
            row = candidates[0]

        expected_input_fingerprints = _flatten_fingerprint_groups(
            source_fingerprints,
            requirement["required_input_groups"],
        )
        missing_required_input_paths: list[str] = []
        for group in requirement["required_input_groups"]:
            group_value = source_fingerprints.get(group)
            group_rows = (
                [group_value]
                if isinstance(group_value, Mapping)
                else (
                    [
                        item
                        for item in group_value
                        if isinstance(item, Mapping)
                    ]
                    if isinstance(group_value, list)
                    else []
                )
            )
            missing_required_input_paths.extend(
                str(item.get("path") or group)
                for item in group_rows
                if item.get("exists") is not True
            )
        actual_input_fingerprints = (
            {
                str(path): str(value)
                for path, value in row.get("input_fingerprints", {}).items()
            }
            if isinstance(row.get("input_fingerprints"), Mapping)
            else {}
        )
        actual_covered = {
            *(_string_sequence(row.get("covered_obligation_ids")))
        }
        required_covered = set(requirement["covered_obligation_ids"])
        result_path = _artifact_path(row.get("result_path"))
        expected_artifact_sha = str(row.get("result_sha256") or "")

        checks = (
            (
                "receipt_id_mismatch",
                row.get("receipt_id") != requirement["receipt_id"],
            ),
            (
                "execution_owner_mismatch",
                row.get("execution_owner") != requirement["execution_owner"],
            ),
            ("terminal_status_not_passed", row.get("terminal_status") != "passed"),
            ("exit_code_not_zero", row.get("exit_code") != 0),
            ("receipt_not_current", row.get("current") is not True),
            ("receipt_not_immutable", row.get("immutable") is not True),
            ("command_missing", not str(row.get("command") or "")),
            (
                "request_identity_mismatch",
                row.get("request_identity")
                != native_receipt_request_identity(row),
            ),
            (
                "input_fingerprints_mismatch",
                actual_input_fingerprints != expected_input_fingerprints,
            ),
            (
                "required_input_missing:"
                + ",".join(sorted(missing_required_input_paths)),
                bool(missing_required_input_paths),
            ),
            (
                "covered_obligation_ids_incomplete",
                not required_covered.issubset(actual_covered),
            ),
            ("result_artifact_missing_or_external", result_path is None),
            (
                "result_artifact_hash_mismatch",
                result_path is not None
                and (
                    not result_path.is_file()
                    or not expected_artifact_sha
                    or hashlib.sha256(result_path.read_bytes()).hexdigest()
                    != expected_artifact_sha
                ),
            ),
        )
        row_failures.extend(
            f"{check_id}:{code}" for code, active in checks if active
        )
        failures.extend(row_failures)
        current = not row_failures
        receipt_id = str(row.get("receipt_id") or "")
        if current:
            current_receipt_ids.add(receipt_id)
            covered_obligations.update(actual_covered)
            evidence_ids_by_check.setdefault(check_id, []).append(receipt_id)
        validated_rows.append(
            {
                "check_id": check_id,
                "receipt_id": receipt_id,
                "execution_owner": str(row.get("execution_owner") or ""),
                "current": current,
                "failures": row_failures,
                "covered_obligation_ids": sorted(actual_covered),
                "input_fingerprints": actual_input_fingerprints,
                "result_path": str(row.get("result_path") or ""),
                "result_sha256": expected_artifact_sha,
                "request_identity": str(row.get("request_identity") or ""),
            }
        )

    typed_rows = manifest.get("typed_runtime_evidence")
    typed_evidence = (
        [row for row in typed_rows if isinstance(row, Mapping)]
        if isinstance(typed_rows, list)
        else []
    )
    waiver_rows = [
        row
        for row in typed_evidence
        if row.get("evidence_id") == WAIVER_TYPED_EVIDENCE_ID
    ]
    waiver_failures: list[str] = []
    if len(waiver_rows) != 1:
        waiver_failures.append(
            f"authorized_waiver_semantics:evidence_cardinality_{len(waiver_rows)}"
        )
        waiver_row: Mapping[str, object] = {}
    else:
        waiver_row = waiver_rows[0]
    runtime_receipt_id = str(
        REQUIRED_NATIVE_RECEIPTS["native_runtime_conformance"]["receipt_id"]
    )
    waiver_checks = (
        (
            "native_receipt_not_current",
            waiver_row.get("native_receipt_id") not in current_receipt_ids
            or waiver_row.get("native_receipt_id") != runtime_receipt_id,
        ),
        ("status_not_passed", waiver_row.get("status") != "passed"),
        ("model_action_mismatch", waiver_row.get("model_action") != "authorized_waiver"),
        ("runtime_action_mismatch", waiver_row.get("runtime_action") != "waive_with_authority"),
        ("authority_ref_not_required", waiver_row.get("authority_ref_required") is not True),
        ("not_terminal_disposition", waiver_row.get("terminal_disposition") is not True),
        ("repair_packet_allowed", waiver_row.get("repair_packet_allowed") is not False),
        (
            "action_refinement_obligation_missing",
            "unified_repair.action_runtime_refinement"
            not in {
                *(
                    _string_sequence(
                        waiver_row.get("covered_obligation_ids")
                    )
                )
            },
        ),
    )
    waiver_failures.extend(
        f"authorized_waiver_semantics:{code}"
        for code, active in waiver_checks
        if active
    )
    failures.extend(waiver_failures)
    waiver_ok = not waiver_failures
    if waiver_ok:
        covered_obligations.add("unified_repair.action_runtime_refinement")

    return {
        "ok": not failures,
        "schema_version": str(manifest.get("schema_version") or ""),
        "model_id": str(manifest.get("model_id") or ""),
        "failures": sorted(set(failures)),
        "receipts": validated_rows,
        "current_receipt_ids": sorted(current_receipt_ids),
        "covered_obligation_ids": sorted(covered_obligations),
        "runtime_evidence_ids": evidence_ids_by_check.get(
            "native_runtime_conformance", []
        ),
        "test_evidence_ids": evidence_ids_by_check.get(
            "exact_native_test_conformance", []
        ),
        "waiver_semantics": {
            "ok": waiver_ok,
            "evidence_id": str(waiver_row.get("evidence_id") or ""),
            "native_receipt_id": str(waiver_row.get("native_receipt_id") or ""),
            "failures": waiver_failures,
        },
        "claim_boundary": (
            "This is a read-only exact receipt audit. The unified model runner "
            "does not execute, wrap, copy, or relabel either native owner command."
        ),
    }


def _native_owner_inventory_report() -> dict[str, object]:
    by_check: dict[str, list[str]] = {}
    for row in NATIVE_EXECUTION_OWNER_INVENTORY:
        by_check.setdefault(str(row["check_id"]), []).append(
            str(row["execution_owner"])
        )
    duplicate_or_missing = {
        check_id: owners
        for check_id, owners in by_check.items()
        if len(owners) != 1 or not owners[0]
    }
    expected_kinds = {
        "model_runner",
        "source_audit",
        "ordinary_test",
        "synthetic_replay",
        "parent_receipt",
    }
    actual_kinds = {
        str(row["check_kind"]) for row in NATIVE_EXECUTION_OWNER_INVENTORY
    }
    return {
        "ok": not duplicate_or_missing
        and expected_kinds.issubset(actual_kinds),
        "rows": [
            {
                **row,
                "dependencies": list(row["dependencies"]),
            }
            for row in NATIVE_EXECUTION_OWNER_INVENTORY
        ],
        "duplicate_or_missing_owner_checks": duplicate_or_missing,
        "missing_check_kinds": sorted(expected_kinds - actual_kinds),
        "execution_rule": (
            "Each check has one frozen native execution owner; consumers may "
            "verify its immutable receipt but never rerun or relabel its command."
        ),
    }


def _native_execution_projection(
    native_evidence: Mapping[str, object],
) -> dict[str, list[dict[str, object]]]:
    """Separate consumed owner receipts from genuinely skipped native checks."""

    rows = (
        (
            "native_runtime_conformance",
            list(native_evidence.get("runtime_evidence_ids") or []),
            "No current exact native runtime owner receipt was supplied.",
        ),
        (
            "exact_native_test_conformance",
            list(native_evidence.get("test_evidence_ids") or []),
            "No current exact native test owner receipt was supplied.",
        ),
    )
    return {
        "consumed_native_owner_receipts": [
            {
                "check_id": check_id,
                "status": "consumed",
                "receipt_ids": receipt_ids,
            }
            for check_id, receipt_ids, _missing_reason in rows
            if receipt_ids
        ],
        "skipped_checks": [
            {
                "check_id": check_id,
                "status": "missing_current_receipt",
                "reason": missing_reason,
            }
            for check_id, receipt_ids, missing_reason in rows
            if not receipt_ids
        ],
    }


def _flowguard_report() -> dict[str, object]:
    # One trigger per Explorer shard prevents irrelevant cross-input sequence
    # products while preserving the complete six-transition state graph and
    # the accepted/rejected branch for that exact repair identity.
    reports = []
    for trigger in model.EXTERNAL_INPUTS:
        required_labels = tuple(
            label
            for label in model.REQUIRED_SAFE_LABELS
            if label.endswith(f".{trigger.case_id}")
        )
        reports.append(
            Explorer(
                workflow=model.build_workflow(),
                initial_states=(model.initial_state(),),
                external_inputs=(trigger,),
                invariants=model.INVARIANTS,
                max_sequence_length=model.MAX_SEQUENCE_LENGTH,
                terminal_predicate=model.terminal_predicate,
                success_predicate=lambda state, _trace: model.is_success(state),
                required_labels=required_labels,
            ).explore()
        )
    reachability_failures = [
        failure.message
        for report in reports
        for failure in report.reachability_failures
    ]
    return {
        "ok": all(report.ok for report in reports),
        "summary": f"{len(reports)} exact-input Explorer shards",
        "shard_count": len(reports),
        "explored_sequence_count": sum(len(report.explored_sequences) for report in reports),
        "trace_count": sum(len(report.traces) for report in reports),
        "violation_count": sum(len(report.violations) for report in reports),
        "dead_branch_count": sum(len(report.dead_branches) for report in reports),
        "exception_branch_count": sum(len(report.exception_branches) for report in reports),
        "reachability_failure_count": len(reachability_failures),
        "reachability_failures": reachability_failures,
    }


def _trace_state_projection(state: model.State) -> dict[str, object]:
    return {
        "status": state.status,
        "trigger_origin": state.trigger_origin,
        "repair_action": state.repair_action,
        "terminal_disposition": {
            "selected": state.terminal_disposition,
            "authority_ref": state.authority_ref,
            "repair_packet_created": state.repair_packet_created,
            "run_terminated": state.run_terminated,
            "run_status": state.run_status,
        },
        "run_bridge": {
            "old_run_id": state.old_run_id,
            "old_run_status": state.old_run_status,
            "old_run_immutable": state.old_run_immutable,
            "old_output_ids": list(state.old_output_ids),
            "new_run_id": state.new_run_id,
            "new_run_status": state.new_run_status,
            "read_only_imported_output_ids": list(state.read_only_imported_output_ids),
        },
        "logical_anchor": {
            "repairs_node_id": state.repairs_node_id,
            "repair_node_id": state.repair_node_id,
            "logical_parent_id": state.logical_parent_id,
        },
        "repair_children": {
            "current_repair_generation": state.current_repair_generation,
            "child_ids": list(state.repair_child_ids),
            "parent_ids": list(state.repair_child_parent_ids),
            "generations": list(state.repair_child_generations),
            "executed": list(state.executed_repair_child_ids),
            "accepted": list(state.accepted_repair_child_ids),
            "execution_acceptance_inventory": list(state.execution_acceptance_inventory),
            "terminal_targets": list(state.terminal_target_node_ids),
        },
        "execution": {
            "frontier_appended": state.execution_frontier_appended,
            "historical_index_inserted": state.historical_index_inserted,
            "packet_owner": state.packet_owner,
            "route_node_id": state.route_node_id,
            "role_sequence": list(state.role_sequence),
        },
        "decision_gate": {
            "sequence": list(state.decision_gate_sequence),
            "current": state.decision_gate_current,
            "accepted": state.decision_gate_accepted,
            "rejected": state.decision_gate_rejected,
            "staged_effect_id": state.staged_effect_id,
            "staged_effect_status": state.staged_effect_status,
            "effect_committed_before_worker": state.effect_committed_before_worker,
            "worker_opened_after_effect_commit": state.worker_opened_after_effect_commit,
            "decision_reviewer_result_id": state.decision_reviewer_result_id,
            "post_work_reviewer_result_id": state.post_work_reviewer_result_id,
            "orphan_staged_effect": state.orphan_staged_effect,
            "terminal_round_consumed_on_rejected_gate": state.terminal_round_consumed_on_rejected_gate,
            "rejected_gate_exit_options": list(state.rejected_gate_exit_options),
        },
        "generations": {
            "current": state.current_generation,
            "contract": state.repair_contract_generation,
            "worker": state.worker_result_generation,
            "flowguard": state.flowguard_evidence_generation,
            "reviewer": state.reviewer_evidence_generation,
            "terminal_contract": state.terminal_contract_generation,
        },
        "membership": {
            "before": list(state.active_members_before),
            "after": list(state.active_members_after),
            "unaffected_rebound": list(state.unaffected_rebound_ids),
            "final_ledger": list(state.final_ledger_active_member_ids),
            "active_route_node_order": list(state.active_route_node_order),
        },
        "lineage": {
            "repair_root_id": state.repair_root_id,
            "previous_repair_node_id": state.previous_repair_node_id,
            "previous_repair_root_id": state.previous_repair_root_id,
            "previous_repair_generation": state.previous_repair_generation,
            "repair_attempt": state.repair_attempt,
            "repair_ancestors": list(state.repair_ancestor_node_ids),
        },
        "dependency_replay": {
            "edges": [list(edge) for edge in state.dependency_edges],
            "stale": list(state.downstream_stale_ids),
            "replayed": list(state.downstream_replayed_ids),
            "affected_parents": list(state.affected_parent_node_ids),
            "replayed_parents": list(state.parent_replayed_node_ids),
        },
        "terminal": {
            "contract_id": state.terminal_contract_id,
            "round": state.terminal_round,
            "replay_completed": state.terminal_replay_completed,
            "parallel_shortcut": state.parallel_terminal_shortcut,
        },
    }


def _single_result(trigger: model.RepairTrigger) -> Any:
    results = list(model.UnifiedRepairIntegrityBlock().apply(trigger, model.initial_state()))
    if len(results) != 1:
        raise RuntimeError(f"expected one repair result for {trigger.case_id}, got {len(results)}")
    return results[0]


def _execute_forward_trace(
    trigger: model.RepairTrigger,
) -> tuple[model.State, list[str], list[dict[str, object]], list[str]]:
    state = model.initial_state()
    labels: list[str] = []
    stage_receipts: list[dict[str, object]] = []
    failure_ids: list[str] = []
    for _step in range(model.MAX_SEQUENCE_LENGTH):
        results = list(model.UnifiedRepairIntegrityBlock().apply(trigger, state))
        forward = [
            result
            for result in results
            if not result.label.startswith(f"{model.REJECTED_GATE_STATUS}.")
        ]
        if len(forward) != 1:
            failure_ids.append(f"transition_count:{state.status}:{len(forward)}")
            break
        result = forward[0]
        state = result.new_state
        labels.append(result.label)
        findings = model.invariant_findings(state)
        stage_receipts.append(
            {
                "status": state.status,
                "label": result.label,
                "finding_ids": [item.finding_id for item in findings],
            }
        )
        if findings:
            failure_ids.extend(item.finding_id for item in findings)
            break
        if state.status == "complete":
            break
    return state, labels, stage_receipts, failure_ids


def _accepted_traces() -> tuple[list[dict[str, object]], list[str]]:
    traces: list[dict[str, object]] = []
    failures: list[str] = []
    for trigger in model.GOOD_INPUTS:
        state, labels, stage_receipts, stage_failure_ids = _execute_forward_trace(trigger)
        findings = model.invariant_findings(state)
        accepted = model.is_success(state) and not findings and not stage_failure_ids
        if not accepted:
            failures.append(trigger.case_id)
        traces.append(
            {
                "case_id": trigger.case_id,
                "input": {
                    "origin": trigger.origin,
                    "requested_action": trigger.requested_action,
                    "repair_attempt": trigger.repair_attempt,
                    "terminal_round": trigger.terminal_round,
                },
                "labels": labels,
                "stage_receipts": stage_receipts,
                "output_action_id": model.action_id_for_scope(trigger.requested_action),
                "accepted": accepted,
                "finding_ids": sorted(set(stage_failure_ids) | {item.finding_id for item in findings}),
                "state": _trace_state_projection(state),
            }
        )
    return traces, failures


def _safe_rejected_gate_report() -> dict[str, object]:
    traces: list[dict[str, object]] = []
    failures: list[str] = []
    triggers = [
        trigger
        for trigger in model.GOOD_INPUTS
        if trigger.requested_action in model.SUBSTANTIVE_REPAIR_ACTIONS
    ]
    for trigger in triggers:
        state = model.initial_state()
        labels: list[str] = []
        for expected_status in ("triggered", "decision_staged"):
            results = list(model.UnifiedRepairIntegrityBlock().apply(trigger, state))
            candidates = [result for result in results if result.new_state.status == expected_status]
            if len(candidates) != 1:
                failures.append(trigger.case_id)
                break
            state = candidates[0].new_state
            labels.append(candidates[0].label)
        else:
            results = list(model.UnifiedRepairIntegrityBlock().apply(trigger, state))
            rejected = [
                result
                for result in results
                if result.new_state.status == model.REJECTED_GATE_STATUS
            ]
            if len(rejected) != 1:
                failures.append(trigger.case_id)
                continue
            state = rejected[0].new_state
            labels.append(rejected[0].label)
            findings = model.invariant_findings(state)
            accepted = model.is_success(state) and not findings
            if not accepted:
                failures.append(trigger.case_id)
            traces.append(
                {
                    "case_id": trigger.case_id,
                    "labels": labels,
                    "accepted_disposal": accepted,
                    "finding_ids": [item.finding_id for item in findings],
                    "state": _trace_state_projection(state),
                }
            )
    return {
        "ok": not failures and len(traces) == len(triggers),
        "expected_count": len(triggers),
        "accepted_count": len(traces) - len(failures),
        "failed_cases": sorted(set(failures)),
        "traces": traces,
    }


def _known_bad_report() -> dict[str, object]:
    expected_cases = model.known_bad_cases()
    rejected_traces: list[dict[str, object]] = []
    detected: list[str] = []
    missing: list[dict[str, object]] = []
    finding_counts: Counter[str] = Counter()
    for case_id, (_state, expected_finding_ids) in expected_cases.items():
        trigger = model.bad_trigger(case_id)
        result = _single_result(trigger)
        findings = model.invariant_findings(result.new_state)
        actual_ids = tuple(item.finding_id for item in findings)
        actual_set = set(actual_ids)
        expected_set = set(expected_finding_ids)
        rejected = bool(findings) and not model.is_success(result.new_state)
        caught = rejected and expected_set.issubset(actual_set)
        if caught:
            detected.append(case_id)
        else:
            missing.append(
                {
                    "case_id": case_id,
                    "expected_finding_ids": list(expected_finding_ids),
                    "actual_finding_ids": list(actual_ids),
                    "rejected": rejected,
                }
            )
        finding_counts.update(actual_ids)
        rejected_traces.append(
            {
                "case_id": case_id,
                "input": {
                    "origin": trigger.origin,
                    "requested_action": trigger.requested_action,
                    "fault_case_id": trigger.fault_case_id,
                },
                "labels": [result.label],
                "rejected": rejected,
                "expected_finding_ids": list(expected_finding_ids),
                "finding_ids": list(actual_ids),
                "action_ids": sorted({item.action_id for item in findings}),
                "state": _trace_state_projection(result.new_state),
            }
        )
    return {
        "ok": not missing and len(expected_cases) >= 56,
        "expected_count": len(expected_cases),
        "detected_count": len(detected),
        "expected": sorted(expected_cases),
        "detected": sorted(detected),
        "missing": missing,
        "finding_counts": dict(sorted(finding_counts.items())),
        "rejected_traces": rejected_traces,
    }


def _runtime_gap_rows(
    runtime_text: str,
    run_shell_text: str,
    migration_text: str,
    pointer_store_text: str,
    native_evidence: Mapping[str, object],
) -> list[dict[str, object]]:
    separate_terminal_path = (
        "_terminal_supplemental_repair_required" in runtime_text
        and "_terminal_supplemental_repair_contract" in runtime_text
    )
    terminal_route_node_fallback = (
        "if route_node_id and route_node_id in ledger.get(\"route_nodes\", {})" in runtime_text
        and "fresh_packet_id = _issue_current_scope_repair_packet" in runtime_text
    )
    covered_obligations = {
        str(value)
        for value in native_evidence.get("covered_obligation_ids", [])
        if str(value)
    }
    waiver_semantics = (
        native_evidence.get("waiver_semantics")
        if isinstance(native_evidence.get("waiver_semantics"), Mapping)
        else {}
    )
    definitions = (
        (
            "GAP-URI-001",
            "PM proactive historical-defect entry is not first-class",
            "ACT-URI-002",
            "unified_repair.pm_historical_direct_entry_no_blocker",
            "pm_historical_defect" not in runtime_text,
            "No pm_historical_defect runtime marker; PM repair decisions are blocker-subject based.",
        ),
        (
            "GAP-URI-002",
            "Terminal substantive repair can lose Worker/route-node ownership",
            "ACT-URI-004",
            "unified_repair.worker_flowguard_reviewer_chain",
            terminal_route_node_fallback and "terminal_substantive_repair_worker" not in runtime_text,
            "Terminal repair shares a route_node_id-dependent branch with a current-scope fallback and has no dedicated Worker marker.",
        ),
        (
            "GAP-URI-003",
            "Terminal closure has no explicit contract-generation freshness binding",
            "ACT-URI-005",
            "unified_repair.contract_evidence_generation",
            "terminal_contract_generation" not in runtime_text and "repair_contract_generation" not in runtime_text,
            "No explicit terminal/repair contract generation marker is present in core runtime.",
        ),
        (
            "GAP-URI-004",
            "Repeated repair lineage is not represented as root plus previous repair link",
            "ACT-URI-006",
            "unified_repair.repeated_lineage_generation",
            "repair_root_id" not in runtime_text or "previous_repair_node_id" not in runtime_text,
            "Core runtime has no explicit repair_root_id + previous_repair_node_id pair.",
        ),
        (
            "GAP-URI-005",
            "Replacement does not expose unaffected-sibling membership conservation",
            "ACT-URI-007",
            "unified_repair.unaffected_sibling_rebind_conservation",
            "unaffected_rebound_ids" not in runtime_text,
            "No explicit unaffected_rebound_ids membership receipt is present.",
        ),
        (
            "GAP-URI-006",
            "Discovery phases do not converge on one typed repair trigger",
            "ACT-URI-001",
            "unified_repair.terminal_shared_engine",
            separate_terminal_path and "repair_trigger_origin" not in runtime_text,
            "Terminal supplemental repair is a separate named path and no repair_trigger_origin marker exists.",
        ),
        (
            "GAP-URI-007",
            "Repair does not expose a complete affected dependency cone receipt",
            "ACT-URI-008",
            "unified_repair.affected_downstream_replay",
            "dependency_cone" not in runtime_text and "impact_cone" not in runtime_text,
            "No dependency_cone or impact_cone marker is present in core runtime.",
        ),
        (
            "GAP-URI-008",
            "Logical repair anchoring and current-frontier execution are not separate explicit facts",
            "ACT-URI-003",
            "unified_repair.same_slot_replacement_single_authority",
            "repairs_node_id" not in runtime_text or "execution_frontier_appended" not in runtime_text,
            "Core runtime lacks the explicit repairs_node_id + execution_frontier_appended pair.",
        ),
        (
            "GAP-URI-009",
            "Modeled subtree repair has no explicit runtime action refinement",
            "ACT-URI-003",
            "unified_repair.action_runtime_refinement",
            "repair_subtree" not in runtime_text,
            "ACTION_REFINEMENT_MAP has no runtime action for repair_subtree; no repair_subtree marker is present in core runtime.",
        ),
        (
            "GAP-URI-010",
            "Authorized-waiver refinement to waive_with_authority remains semantically unverified",
            "ACT-URI-011",
            "unified_repair.action_runtime_refinement",
            waiver_semantics.get("ok") is not True,
            (
                "The model's authorized_waiver maps to waive_with_authority; "
                "only current typed runtime evidence bound to the native "
                "runtime receipt proves authority and terminal-disposition semantics."
            ),
        ),
        (
            "GAP-URI-011",
            "Current-scope and parent-scope repair lack one explicit staged-effect decision identity",
            "ACT-URI-004",
            "unified_repair.decision_gate_before_effect_commit",
            "staged_effect_id" not in runtime_text or "decision_gate_sequence" not in runtime_text,
            "Core runtime does not expose both staged_effect_id and decision_gate_sequence markers for pre-worker current/parent repair decisions.",
        ),
        (
            "GAP-URI-012",
            (
                "Completed or stopped source-run repair lacks a distinct "
                "current run with read-only imported outputs"
            ),
            "ACT-URI-010",
            "unified_repair.completed_run_distinct_current_import",
            not (
                "create_run_shell" in run_shell_text
                and "imported_read_only" in migration_text
                and "current_payload_from_ledger" in pointer_store_text
                and (
                    "source_run_id" in run_shell_text
                    or "historical_source_run_id" in run_shell_text
                )
                and (
                    "read_only" in run_shell_text
                    or "imported_read_only" in run_shell_text
                )
            ),
            (
                "The distinct-run owner spans run_shell.py, migration.py, "
                "and pointer_store.py; a non-empty new run id alone does not "
                "prove source-run immutability or read-only imported output."
            ),
        ),
    )
    rows: list[dict[str, object]] = []
    for (
        gap_id,
        title,
        action_id,
        obligation_id,
        source_marker_open,
        observation,
    ) in definitions:
        native_receipt_covers = (
            obligation_id in covered_obligations
            and native_evidence.get("ok") is True
        )
        status = (
            "resolved_by_native_receipt"
            if native_receipt_covers
            else "expected_open"
            if source_marker_open
            else "source_marker_present_unverified"
        )
        rows.append(
            {
                "gap_id": gap_id,
                "title": title,
                "required_action_id": action_id,
                "obligation_id": obligation_id,
                "expected_open": True,
                "status": status,
                "source_observation_id": f"SRC-{gap_id}",
                "observation": observation,
                "evidence_paths": (
                    [
                        _relative(RUN_SHELL_PATH),
                        _relative(MIGRATION_PATH),
                        _relative(POINTER_STORE_PATH),
                    ]
                    if gap_id == "GAP-URI-012"
                    else [_relative(CORE_RUNTIME_PATH)]
                ),
                "native_receipt_covers": native_receipt_covers,
                "claim_boundary": (
                    "The source-marker observation is retained as diagnosis-generation "
                    "evidence. Current closure requires the exact native owner receipt."
                ),
            }
        )
    return rows


def _conformance_report(
    source_fingerprint: str,
    native_evidence: Mapping[str, object],
) -> dict[str, object]:
    runtime_text = CORE_RUNTIME_PATH.read_text(encoding="utf-8")
    run_shell_text = RUN_SHELL_PATH.read_text(encoding="utf-8")
    migration_text = MIGRATION_PATH.read_text(encoding="utf-8")
    pointer_store_text = POINTER_STORE_PATH.read_text(encoding="utf-8")
    gap_rows = _runtime_gap_rows(
        runtime_text,
        run_shell_text,
        migration_text,
        pointer_store_text,
        native_evidence,
    )
    expected_open_gap_ids = [
        str(row["gap_id"])
        for row in gap_rows
        if row["status"] == "expected_open"
    ]
    runtime_evidence_ids = list(native_evidence.get("runtime_evidence_ids", []))
    test_evidence_ids = list(native_evidence.get("test_evidence_ids", []))
    missing = [
        *(
            str(value)
            for value in native_evidence.get("failures", [])
            if str(value)
        ),
        *expected_open_gap_ids,
    ]
    ok = native_evidence.get("ok") is True and not missing
    return {
        "required": True,
        "ok": ok,
        "skipped": False,
        "source_fingerprint": source_fingerprint,
        "model_contract_ok": True,
        "runtime_evidence_ids": runtime_evidence_ids,
        "test_evidence_ids": test_evidence_ids,
        "missing": missing,
        "runtime_gap_rows": gap_rows,
        "expected_open_gap_ids": expected_open_gap_ids,
        "resolved_expected_gap_ids": [
            str(row["gap_id"])
            for row in gap_rows
            if row["status"] != "expected_open"
        ],
        "unexpected_gap_ids": [],
        "native_evidence": dict(native_evidence),
        "claim_boundary": (
            "Historical diagnosis rows remain immutable. Current runtime/test "
            "conformance is green only when exact native owner receipts match "
            "the frozen runtime/test fingerprints and cover every obligation."
        ),
    }


def _catalog_projection() -> tuple[dict[str, object], dict[str, object]]:
    finding_catalog = {
        finding_id: {
            "message": spec.message,
            "action_id": spec.action_id,
        }
        for finding_id, spec in model.FINDING_CATALOG.items()
    }
    action_catalog = {
        action_id: {"description": description}
        for action_id, description in model.ACTION_CATALOG.items()
    }
    return finding_catalog, action_catalog


def _action_refinement_projection() -> dict[str, object]:
    return {
        action: {
            "runtime_action": row["runtime_action"],
            "status": row["status"],
            "claim_boundary": "name/intent refinement declaration only; runtime parity requires native evidence",
        }
        for action, row in model.ACTION_REFINEMENT_MAP.items()
    }


def _coverage_receipt_report(
    *,
    accepted_traces: Sequence[Mapping[str, object]],
    known_bad: Mapping[str, object],
    model_contract_ok: bool,
    file_inventory_ok: bool,
    conformance: Mapping[str, object],
    native_evidence: Mapping[str, object],
) -> dict[str, object]:
    accepted_by_origin: dict[str, list[str]] = {}
    for row in accepted_traces:
        input_row = row.get("input")
        origin = (
            str(input_row.get("origin") or "")
            if isinstance(input_row, Mapping)
            else ""
        )
        case_id = str(row.get("case_id") or "")
        if origin and case_id:
            accepted_by_origin.setdefault(origin, []).append(case_id)
    rejected_rows = known_bad.get("rejected_traces")
    rejected_case_ids = sorted(
        str(row.get("case_id") or "")
        for row in (
            rejected_rows if isinstance(rejected_rows, list) else []
        )
        if isinstance(row, Mapping) and str(row.get("case_id") or "")
    )
    coverage_shards = [
        {
            "shard_id": f"shard.unified_repair.accepted.{origin}",
            "shard_kind": "canonical_good",
            "case_ids": sorted(case_ids),
            "covered_obligation_ids": list(UNIFIED_REPAIR_OBLIGATION_IDS),
            "current": model_contract_ok,
        }
        for origin, case_ids in sorted(accepted_by_origin.items())
    ]
    coverage_shards.append(
        {
            "shard_id": "shard.unified_repair.known_bad.same_class",
            "shard_kind": "canonical_bad_and_interaction",
            "case_ids": rejected_case_ids,
            "covered_obligation_ids": list(UNIFIED_REPAIR_OBLIGATION_IDS),
            "current": bool(known_bad.get("ok")),
        }
    )

    native_rows = {
        str(row.get("check_id") or ""): row
        for row in native_evidence.get("receipts", [])
        if isinstance(row, Mapping)
    }
    child_definitions = (
        (
            "receipt.unified_repair.executable_model",
            "flowpilot_unified_repair_integrity.model",
            model_contract_ok,
            tuple(
                sorted(
                    {
                        str(row.get("case_id") or "")
                        for row in accepted_traces
                        if str(row.get("case_id") or "")
                    }
                    | set(rejected_case_ids)
                )
            ),
            tuple(row["shard_id"] for row in coverage_shards),
            (),
        ),
        (
            "receipt.unified_repair.source_audit",
            "flowpilot_unified_repair_integrity.source_audit",
            file_inventory_ok
            and conformance.get("expected_open_gap_ids") in ([], ()),
            tuple(
                str(row.get("source_observation_id") or "")
                for row in conformance.get("runtime_gap_rows", [])
                if isinstance(row, Mapping)
            ),
            ("shard.unified_repair.source_audit",),
            (),
        ),
        (
            str(
                REQUIRED_NATIVE_RECEIPTS["native_runtime_conformance"][
                    "receipt_id"
                ]
            ),
            "flowpilot_unified_repair_integrity.native_runtime",
            bool(
                native_rows.get("native_runtime_conformance", {}).get(
                    "current"
                )
            ),
            tuple(UNIFIED_REPAIR_OBLIGATION_IDS),
            ("shard.unified_repair.native_runtime",),
            tuple(
                native_rows.get("native_runtime_conformance", {}).get(
                    "failures", []
                )
            ),
        ),
        (
            str(
                REQUIRED_NATIVE_RECEIPTS["exact_native_test_conformance"][
                    "receipt_id"
                ]
            ),
            "flowpilot_unified_repair_integrity.native_tests",
            bool(
                native_rows.get("exact_native_test_conformance", {}).get(
                    "current"
                )
            ),
            tuple(UNIFIED_REPAIR_OBLIGATION_IDS),
            ("shard.unified_repair.native_tests",),
            tuple(
                native_rows.get("exact_native_test_conformance", {}).get(
                    "failures", []
                )
            ),
        ),
        (
            "receipt.unified_repair.authorized_waiver_semantics",
            "flowpilot_unified_repair_integrity.waiver_semantics",
            bool(
                (
                    native_evidence.get("waiver_semantics")
                    if isinstance(
                        native_evidence.get("waiver_semantics"), Mapping
                    )
                    else {}
                ).get("ok")
            ),
            ("unified_repair.action_runtime_refinement",),
            ("shard.unified_repair.waiver_semantics",),
            tuple(
                (
                    native_evidence.get("waiver_semantics")
                    if isinstance(
                        native_evidence.get("waiver_semantics"), Mapping
                    )
                    else {}
                ).get("failures", [])
            ),
        ),
    )
    child_receipts: list[ModelContractCoverageReceipt] = []
    for (
        receipt_id,
        child_model_id,
        current,
        covered_ids,
        shard_ids,
        finding_codes,
    ) in child_definitions:
        child_receipts.append(
            ModelContractCoverageReceipt(
                receipt_id=receipt_id,
                model_id=child_model_id,
                parent_model_id=model.MODEL_ID,
                status="covered" if current else "blocked",
                confidence="full" if current else "blocked",
                current=bool(current),
                covered_case_ids=tuple(covered_ids) if current else (),
                shard_ids=tuple(shard_ids),
                interaction_group_ids=("unified_repair_integrity",),
                missing_case_ids=() if current else tuple(covered_ids),
                blocked_case_ids=() if current else tuple(covered_ids),
                finding_codes=tuple(str(value) for value in finding_codes),
            )
        )
    required_child_ids = tuple(
        receipt.receipt_id for receipt in child_receipts
    )
    consumed_child_ids = tuple(
        receipt.receipt_id for receipt in child_receipts if receipt.current
    )
    missing_child_ids = tuple(
        sorted(set(required_child_ids) - set(consumed_child_ids))
    )
    parent_current = not missing_child_ids
    parent_receipt = ModelContractCoverageReceipt(
        receipt_id="receipt.unified_repair.integrity_parent",
        model_id=model.MODEL_ID,
        status="covered" if parent_current else "blocked",
        confidence="full" if parent_current else "blocked",
        current=parent_current,
        covered_case_ids=tuple(
            sorted(
                {
                    case_id
                    for receipt in child_receipts
                    for case_id in receipt.covered_case_ids
                }
            )
        ),
        shard_ids=tuple(
            shard_id
            for receipt in child_receipts
            for shard_id in receipt.shard_ids
        ),
        interaction_group_ids=("unified_repair_integrity",),
        required_child_receipt_ids=required_child_ids,
        consumed_child_receipt_ids=consumed_child_ids,
        blocked_case_ids=missing_child_ids,
        finding_codes=(
            ("required_child_receipt_missing",) if missing_child_ids else ()
        ),
    )
    handoffs = [
        CompositeHandoffAcceptance(
            acceptance_id=(
                "handoff.unified_repair.to."
                + consumer_id.replace(".", "_").replace("-", "_")
            ),
            case_id="case.unified_repair.integrity_parent",
            route_ids=(model.MODEL_ID, consumer_id),
            description=(
                "The consumer must verify the exact current unified repair "
                "parent receipt; it cannot execute or relabel a child owner."
            ),
            metadata={
                "required_parent_receipt_id": parent_receipt.receipt_id,
                "required_child_receipt_ids": list(required_child_ids),
            },
        ).to_dict()
        for consumer_id in REQUIRED_CONSUMER_IDS
    ]
    parent_consumption_requirements = [
        {
            "consumer_id": consumer_id,
            "required_parent_receipt_id": parent_receipt.receipt_id,
            "required_child_receipt_ids": list(required_child_ids),
            "consumed_child_receipt_ids": list(consumed_child_ids),
            "missing_child_receipt_ids": list(missing_child_ids),
            "status": "current" if parent_current else "blocked",
            "execution_mode": "read_only_receipt_consumer",
        }
        for consumer_id in REQUIRED_CONSUMER_IDS
    ]
    return {
        "ok": parent_current,
        "coverage_shards": coverage_shards,
        "child_receipts": [
            receipt.to_dict() for receipt in child_receipts
        ],
        "parent_receipt": parent_receipt.to_dict(),
        "parent_consumption_requirements": parent_consumption_requirements,
        "composite_handoff_acceptances": handoffs,
        "required_consumer_ids": list(REQUIRED_CONSUMER_IDS),
        "missing_child_receipt_ids": list(missing_child_ids),
        "claim_boundary": (
            "Coverage shards and receipt identities are generated here. "
            "Each external parent must consume the current parent receipt in "
            "its own check; this projection does not execute that parent."
        ),
    }


def run_checks(
    *,
    evidence_manifest: Mapping[str, object] | None = None,
    evidence_manifest_path: str = "",
) -> dict[str, object]:
    source_fingerprints = _source_fingerprints()
    source_fingerprint = _combined_source_fingerprint(SOURCE_FINGERPRINT_INPUTS)
    native_evidence = _native_evidence_report(
        evidence_manifest,
        source_fingerprints,
    )
    native_owner_inventory = _native_owner_inventory_report()
    flowguard = _flowguard_report()
    accepted_traces, failed_good_cases = _accepted_traces()
    safe_rejected_gate = _safe_rejected_gate_report()
    known_bad = _known_bad_report()
    detailed_fingerprints = [
        source_fingerprints["model"],
        source_fingerprints["runner"],
        *source_fingerprints["unified_runtime_sources"],
        source_fingerprints["native_runtime_owner"],
        source_fingerprints["native_runtime_fixture"],
        source_fingerprints["exact_native_test_owner"],
        *source_fingerprints["exact_relevant_tests"],
    ]
    file_inventory_ok = all(bool(row["exists"]) for row in detailed_fingerprints)
    model_contract_ok = (
        bool(flowguard["ok"])
        and not failed_good_cases
        and bool(safe_rejected_gate["ok"])
        and bool(known_bad["ok"])
        and file_inventory_ok
    )
    conformance = _conformance_report(source_fingerprint, native_evidence)
    conformance["model_contract_ok"] = model_contract_ok
    finding_catalog, action_catalog = _catalog_projection()
    runtime_conformance_ok = bool(conformance["ok"])
    native_execution_projection = _native_execution_projection(native_evidence)
    coverage_receipts = _coverage_receipt_report(
        accepted_traces=accepted_traces,
        known_bad=known_bad,
        model_contract_ok=model_contract_ok,
        file_inventory_ok=file_inventory_ok,
        conformance=conformance,
        native_evidence=native_evidence,
    )
    overall_ok = (
        model_contract_ok
        and runtime_conformance_ok
        and bool(native_owner_inventory["ok"])
        and bool(coverage_receipts["ok"])
    )
    decision = (
        "fully_conformant"
        if overall_ok
        else "current_runtime_gap"
        if model_contract_ok
        else "model_contract_failed"
    )
    return {
        "result_type": "flowpilot_unified_repair_integrity_checks",
        "model_id": model.MODEL_ID,
        "ok": overall_ok,
        "model_ok": model_contract_ok,
        "runtime_conformance_ok": runtime_conformance_ok,
        "decision": decision,
        "source_fingerprint": source_fingerprint,
        "source_fingerprint_algorithm": SOURCE_FINGERPRINT_ALGORITHM,
        "source_fingerprints": source_fingerprints,
        "evidence_manifest_path": evidence_manifest_path,
        "native_evidence": native_evidence,
        "native_execution_owner_inventory": native_owner_inventory,
        "flowguard": flowguard,
        "accepted_traces": accepted_traces,
        "safe_rejected_gate": safe_rejected_gate,
        "failed_good_cases": failed_good_cases,
        "known_bad": known_bad,
        "finding_catalog": finding_catalog,
        "action_catalog": action_catalog,
        "action_refinement_map": _action_refinement_projection(),
        "conformance": conformance,
        "coverage_receipts": coverage_receipts,
        "consumed_native_owner_receipts": native_execution_projection[
            "consumed_native_owner_receipts"
        ],
        "skipped_checks": native_execution_projection["skipped_checks"],
        "diagnosis_generation": {
            "status": "preserved_immutable",
            "finding_ids": sorted(model.FINDING_CATALOG),
            "runtime_gap_ids": [
                row["gap_id"] for row in conformance["runtime_gap_rows"]
            ],
            "claim_boundary": (
                "Historical model-analysis findings remain evidence of the "
                "diagnosis generation. They are not erased by a later current "
                "runtime/test pass and cannot substitute for that pass."
            ),
        },
        "claim_boundary": {
            "proves": [
                "30 canonical trigger/action combinations satisfy the unified repair contract",
                "20 continue-repair combinations traverse a legal rejected-gate disposal exit without opening work or consuming a terminal round",
                "repair children, when present, bind to the active replacement node and current repair generation",
                "continue-repair decisions pass a distinct staged-effect gate before the post-work quality chain",
                "at least 56 audit-derived known-bad cases are rejected with stable finding/action ids",
                "model, runner, core runtime, and exact relevant test sources have current fingerprints",
                "each model/source/native-test/parent check has one frozen execution owner",
                "coverage shards, child receipts, one parent receipt, and composite handoff acceptance ids are generated",
            ],
            "does_not_prove": [
                *(
                    []
                    if runtime_conformance_ok
                    else [
                        "current FlowPilot runtime implements the unified repair contract",
                        "native runtime or test conformance",
                    ]
                ),
                "release, install, archive, or production readiness",
                "absence of bugs outside the finite declared repair boundary",
            ],
            "generation_boundary": (
                "Diagnosis-generation rows are immutable; current confidence "
                "requires exact runtime/native-test closure for the current "
                "source identities."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    parser.add_argument("--no-write-results", action="store_true")
    parser.add_argument(
        "--evidence-manifest",
        type=Path,
        default=None,
        help=(
            "Read-only flowpilot.unified_repair_native_evidence_manifest.v1 "
            "from the frozen native owners."
        ),
    )
    args = parser.parse_args()

    evidence_manifest: Mapping[str, object] | None = None
    evidence_manifest_error = ""
    if args.evidence_manifest is not None:
        try:
            loaded = json.loads(
                args.evidence_manifest.read_text(encoding="utf-8")
            )
            if isinstance(loaded, Mapping):
                evidence_manifest = loaded
            else:
                evidence_manifest_error = "evidence manifest is not a JSON object"
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            evidence_manifest_error = str(exc)
    result = run_checks(
        evidence_manifest=evidence_manifest,
        evidence_manifest_path=str(args.evidence_manifest or ""),
    )
    result["evidence_manifest_error"] = evidence_manifest_error
    if evidence_manifest_error:
        result["ok"] = False
        result["runtime_conformance_ok"] = False
        result["decision"] = "current_runtime_gap"
        result["native_evidence"]["ok"] = False
        result["native_evidence"]["failures"] = sorted(
            {
                *result["native_evidence"].get("failures", []),
                f"evidence_manifest_error:{evidence_manifest_error}",
            }
        )
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(output, end="")
    if not args.no_write_results:
        args.json_out.write_text(output, encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
