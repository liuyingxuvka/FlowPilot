"""FlowGuard model for bounded FlowPilot control-plane resource use.

The model does not impose a small-task shortcut on FlowPilot. It preserves the
full opt-in PM/Worker/FlowGuard/Reviewer workflow and models whether repeated
observation, reconciliation, progress, validation evidence, and retention stay
proportional to semantic work.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Mapping

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_control_plane_resource_boundedness"

VALID_SCENARIOS = (
    "unchanged_tick_is_write_free",
    "one_semantic_delta_commits_once",
    "same_receipt_reconciles_once",
    "progress_status_change_is_recorded",
    "repeated_progress_is_coalesced",
    "v5_evidence_uses_bounded_references",
    "explicit_retention_archives_eligible_entry",
)

NEGATIVE_SCENARIOS = (
    "unchanged_tick_rewrites_state",
    "same_receipt_duplicates_effects",
    "legacy_action_observation_fields_return",
    "wait_reminder_body_is_copied",
    "repeated_progress_appends_events",
    "combined_stream_copies_raw_output",
    "v5_owner_proof_reference_missing",
    "daemon_result_accumulates_ticks",
    "retention_selects_protected_entry",
    "retention_applies_without_frozen_plan",
)

SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS

FINITE_PROGRESS_STATUSES = frozenset(
    {
        "started",
        "working",
        "waiting_external",
        "verifying",
        "repairing",
        "blocked",
        "ready_to_submit",
    }
)
MAX_COMBINED_INDEX_BYTES = 32 * 1024
MAX_DAEMON_ANOMALIES = 16

RESOURCE_OBLIGATION_ROWS = (
    {
        "obligation_id": "resource.no_change_persistence",
        "primary_code_owner": "skills/flowpilot/assets/flowpilot_router_runtime_state_persistence_save.py",
        "testmesh_owner_id": "flowguard_control_plane_resource_boundedness",
        "ordinary_test_evidence": "tests/test_flowpilot_control_plane_resource_boundedness_model.py",
    },
    {
        "obligation_id": "resource.receipt_effect_idempotency",
        "primary_code_owner": "skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_writes.py",
        "testmesh_owner_id": "control_plane_resource_boundedness_contract_tests",
        "ordinary_test_evidence": "tests/test_flowpilot_control_plane_resource_boundedness_model.py",
    },
    {
        "obligation_id": "resource.bounded_daemon_terminal_evidence",
        "primary_code_owner": "skills/flowpilot/assets/flowpilot_router_daemon_runtime.py",
        "testmesh_owner_id": "control_plane_resource_boundedness_contract_tests",
        "ordinary_test_evidence": "tests/test_flowpilot_control_plane_resource_boundedness_model.py",
    },
    {
        "obligation_id": "resource.progress_coalescing",
        "primary_code_owner": "skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
        "testmesh_owner_id": "control_plane_resource_boundedness_contract_tests",
        "ordinary_test_evidence": "tests/test_flowpilot_control_plane_resource_boundedness_model.py",
    },
    {
        "obligation_id": "resource.v5_reference_evidence",
        "primary_code_owner": "scripts/test_tier/background_child.py",
        "testmesh_owner_id": "flowguard_control_plane_resource_boundedness",
        "ordinary_test_evidence": "tests/test_flowpilot_control_plane_resource_boundedness_model.py",
    },
    {
        "obligation_id": "resource.fail_closed_retention",
        "primary_code_owner": "scripts/flowpilot_runtime_retention.py",
        "testmesh_owner_id": "control_plane_resource_boundedness_contract_tests",
        "ordinary_test_evidence": "tests/test_flowpilot_control_plane_resource_boundedness_model.py",
    },
)


@dataclass(frozen=True)
class Tick:
    scenario: str


@dataclass(frozen=True)
class ResourceSignal:
    scenario: str


@dataclass(frozen=True)
class State:
    scenario: str = "unset"
    stage: str = "new"
    status: str = "running"  # running | accepted | rejected
    semantic_delta: bool = False
    state_commit_count: int = 0
    action_count: int = 0
    scheduler_effect_count: int = 0
    semantic_history_fact_count: int = 0
    receipt_reconciliation_count: int = 0
    legacy_action_observation_fields_present: bool = False
    copied_wait_reminder_body_present: bool = False
    progress_status: str = "working"
    progress_semantic_change: bool = False
    progress_due_reminder: bool = False
    progress_write_count: int = 0
    progress_event_count: int = 0
    stdout_is_raw_authority: bool = True
    stderr_is_raw_authority: bool = True
    combined_kind: str = "terminal_stream_index"
    combined_bytes: int = 0
    v5_owner_proof_refs_complete: bool = True
    daemon_terminal_tick_count: int = 1
    daemon_anomaly_count: int = 0
    retention_plan_frozen: bool = True
    retention_plan_sha_present: bool = True
    retention_apply_explicit: bool = True
    retention_entry_eligible: bool = True
    retention_entry_protected: bool = False
    retention_archive_readback_verified: bool = True
    rejection_reasons: tuple[str, ...] = ()


def initial_state() -> State:
    return State()


def _scenario_defaults(scenario: str) -> Mapping[str, object]:
    defaults: dict[str, object] = {
        "scenario": scenario,
        "semantic_delta": scenario != "unchanged_tick_is_write_free",
    }
    if scenario == "unchanged_tick_rewrites_state":
        defaults.update(semantic_delta=False)
    if scenario == "same_receipt_duplicates_effects":
        defaults.update(
            action_count=2,
            scheduler_effect_count=2,
            semantic_history_fact_count=2,
            receipt_reconciliation_count=2,
        )
    if scenario == "legacy_action_observation_fields_return":
        defaults.update(legacy_action_observation_fields_present=True)
    if scenario == "wait_reminder_body_is_copied":
        defaults.update(copied_wait_reminder_body_present=True)
    if scenario in {"progress_status_change_is_recorded"}:
        defaults.update(progress_status="verifying", progress_semantic_change=True)
    if scenario in {"repeated_progress_is_coalesced", "repeated_progress_appends_events"}:
        defaults.update(progress_status="working")
    if scenario == "combined_stream_copies_raw_output":
        defaults.update(combined_kind="raw_copy", combined_bytes=4 * MAX_COMBINED_INDEX_BYTES)
    if scenario == "v5_owner_proof_reference_missing":
        defaults.update(v5_owner_proof_refs_complete=False)
    if scenario == "daemon_result_accumulates_ticks":
        defaults.update(daemon_terminal_tick_count=10_000, daemon_anomaly_count=10_000)
    if scenario == "retention_selects_protected_entry":
        defaults.update(retention_entry_eligible=False, retention_entry_protected=True)
    if scenario == "retention_applies_without_frozen_plan":
        defaults.update(retention_plan_frozen=False, retention_plan_sha_present=False)
    return defaults


class Observe:
    """Observe Input x State -> Set(Output x State) without persisting."""

    name = "Observe"
    reads = ("relevant_file_fingerprints", "current_run", "current_projection")
    writes = ("in_memory_delta_classification",)
    idempotency = "observation alone never mutates durable state"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        if input_obj.scenario not in SCENARIOS:
            return
        next_state = replace(state, stage="observed", **_scenario_defaults(input_obj.scenario))
        yield FunctionResult(
            output=ResourceSignal(input_obj.scenario),
            new_state=next_state,
            label=f"observe:{input_obj.scenario}",
        )


class Reconcile:
    """Reconcile Input x State -> Set(Output x State) exactly once."""

    name = "Reconcile"
    reads = ("receipt_sha", "action_state", "scheduler_effect", "semantic_history")
    writes = ("current_action_effect", "semantic_history_fact")
    idempotency = "same receipt/action/effect is already-current, not a new observation"

    def apply(self, input_obj: ResourceSignal, state: State) -> Iterable[FunctionResult]:
        changes: dict[str, object] = {"stage": "reconciled"}
        if input_obj.scenario == "same_receipt_reconciles_once":
            changes.update(
                action_count=1,
                scheduler_effect_count=1,
                semantic_history_fact_count=1,
                receipt_reconciliation_count=1,
            )
        elif input_obj.scenario != "same_receipt_duplicates_effects":
            changes.update(
                action_count=min(state.action_count, 1),
                scheduler_effect_count=min(state.scheduler_effect_count, 1),
                semantic_history_fact_count=min(state.semantic_history_fact_count, 1),
                receipt_reconciliation_count=min(state.receipt_reconciliation_count, 1),
            )
        yield FunctionResult(
            output=input_obj,
            new_state=replace(state, **changes),
            label=f"reconcile:{input_obj.scenario}",
        )


class Persist:
    """Persist Input x State -> Set(Output x State) only for semantic change."""

    name = "Persist"
    reads = ("canonical_public_state", "in_memory_delta_classification")
    writes = ("atomic_run_state_commit",)
    idempotency = "canonical equality returns no-write and preserves mtime/hash/size"

    def apply(self, input_obj: ResourceSignal, state: State) -> Iterable[FunctionResult]:
        commit_count = 1 if state.semantic_delta else 0
        if input_obj.scenario == "unchanged_tick_rewrites_state":
            commit_count = 1
        yield FunctionResult(
            output=input_obj,
            new_state=replace(state, stage="persisted", state_commit_count=commit_count),
            label=f"persist:{input_obj.scenario}",
        )


class RecordProgress:
    """RecordProgress Input x State -> Set(Output x State) for meaningful progress."""

    name = "RecordProgress"
    reads = ("current_progress_status", "last_progress_time", "reminder_due")
    writes = ("progress_event", "progress_projection")
    idempotency = "same status inside the liveness window coalesces to zero writes"

    def apply(self, input_obj: ResourceSignal, state: State) -> Iterable[FunctionResult]:
        writes = int(state.progress_semantic_change or state.progress_due_reminder)
        if input_obj.scenario == "repeated_progress_appends_events":
            writes = 2
        yield FunctionResult(
            output=input_obj,
            new_state=replace(
                state,
                stage="progress_recorded",
                progress_write_count=writes,
                progress_event_count=writes,
            ),
            label=f"record_progress:{input_obj.scenario}",
        )


class StoreEvidence:
    """StoreEvidence Input x State -> Set(Output x State) by immutable reference."""

    name = "StoreEvidence"
    reads = ("stdout", "stderr", "terminal_meta", "impact_plan")
    writes = ("bounded_combined_index", "owner_proof_reference", "terminal_index")
    idempotency = "raw streams have one owner and parents keep bounded references"

    def apply(self, input_obj: ResourceSignal, state: State) -> Iterable[FunctionResult]:
        yield FunctionResult(
            output=input_obj,
            new_state=replace(state, stage="evidence_stored"),
            label=f"store_evidence:{input_obj.scenario}",
        )


class Retain:
    """Retain Input x State -> Set(Output x State) through a frozen explicit plan."""

    name = "Retain"
    reads = ("retention_plan", "current_live_reference_index", "archive_index")
    writes = ("verified_archive", "archive_index", "eligible_source_disposition")
    idempotency = "plan SHA and live revalidation make apply deterministic and fail-closed"

    def apply(self, input_obj: ResourceSignal, state: State) -> Iterable[FunctionResult]:
        retained_state = replace(state, stage="retained")
        failures = contract_failures(retained_state)
        status = "rejected" if failures else "accepted"
        yield FunctionResult(
            output=input_obj,
            new_state=replace(
                retained_state,
                status=status,
                rejection_reasons=tuple(failures),
            ),
            label=f"retain:{input_obj.scenario}:{status}",
        )


def contract_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.stage in {"new", "observed", "reconciled"}:
        return failures
    expected_commits = 1 if state.semantic_delta else 0
    if state.state_commit_count != expected_commits:
        failures.append("durable state commit count does not match semantic delta")
    if max(
        state.action_count,
        state.scheduler_effect_count,
        state.semantic_history_fact_count,
        state.receipt_reconciliation_count,
    ) > 1:
        failures.append("same receipt produced duplicate control-plane effects")
    if state.legacy_action_observation_fields_present:
        failures.append("retired action observation fields regained current authority")
    if state.copied_wait_reminder_body_present:
        failures.append("wait reminder body was copied into a second authority")
    if state.stage in {"progress_recorded", "evidence_stored", "retained"}:
        if state.progress_status not in FINITE_PROGRESS_STATUSES:
            failures.append("progress status is outside the finite vocabulary")
        expected_progress_writes = int(
            state.progress_semantic_change or state.progress_due_reminder
        )
        if state.progress_write_count != expected_progress_writes:
            failures.append("repeated unchanged progress was persisted")
        if state.progress_event_count != state.progress_write_count:
            failures.append("progress event and projection write counts diverged")
    if state.stage in {"evidence_stored", "retained"}:
        if not state.stdout_is_raw_authority or not state.stderr_is_raw_authority:
            failures.append("stdout/stderr lost sole raw-stream authority")
        if state.combined_kind != "terminal_stream_index":
            failures.append("combined evidence copied raw output")
        if state.combined_bytes > MAX_COMBINED_INDEX_BYTES:
            failures.append("combined terminal index exceeded its byte bound")
        if not state.v5_owner_proof_refs_complete:
            failures.append("V5 owner proof reference is incomplete")
        if state.daemon_terminal_tick_count > 1:
            failures.append("daemon terminal evidence accumulated per-tick bodies")
        if state.daemon_anomaly_count > MAX_DAEMON_ANOMALIES:
            failures.append("daemon anomaly evidence exceeded its bound")
    if state.stage == "retained":
        if not state.retention_plan_frozen or not state.retention_plan_sha_present:
            failures.append("retention apply lacks a frozen plan identity")
        if not state.retention_apply_explicit:
            failures.append("retention was applied implicitly")
        if state.retention_entry_protected or not state.retention_entry_eligible:
            failures.append("retention selected an ineligible or protected entry")
        if not state.retention_archive_readback_verified:
            failures.append("retention archive was not read back and verified")
    return failures


def resource_bound_invariant(state: State, trace: object) -> InvariantResult:
    del trace
    failures = contract_failures(state)
    if state.status == "accepted" and failures:
        return InvariantResult.fail("; ".join(failures))
    if state.status == "rejected" and not failures:
        return InvariantResult.fail("resource-bounded state was rejected without a contract failure")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_control_plane_resource_bound",
        description=(
            "No-change observation is write-free; receipts, progress, and evidence are "
            "idempotent and bounded; retention is explicit and fail-closed."
        ),
        predicate=resource_bound_invariant,
    ),
)

EXTERNAL_INPUTS = tuple(Tick(scenario) for scenario in SCENARIOS)
REQUIRED_LABELS = tuple(
    f"{stage}:{scenario}"
    for scenario in SCENARIOS
    for stage in ("observe", "reconcile", "persist", "record_progress", "store_evidence")
) + tuple(
    f"retain:{scenario}:{'accepted' if scenario in VALID_SCENARIOS else 'rejected'}"
    for scenario in SCENARIOS
)
MAX_SEQUENCE_LENGTH = 1


def build_workflow() -> Workflow:
    return Workflow(
        (Observe(), Reconcile(), Persist(), RecordProgress(), StoreEvidence(), Retain()),
        name=MODEL_ID,
    )


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return is_terminal(state)


def known_bad_states() -> dict[str, State]:
    bad: dict[str, State] = {}
    workflow = build_workflow()
    for scenario in NEGATIVE_SCENARIOS:
        run = workflow.execute(initial_state(), Tick(scenario))
        state = run.completed_paths[0].state
        bad[scenario] = replace(state, status="accepted")
    return bad


__all__ = [
    "EXTERNAL_INPUTS",
    "FINITE_PROGRESS_STATUSES",
    "INVARIANTS",
    "MAX_COMBINED_INDEX_BYTES",
    "MAX_DAEMON_ANOMALIES",
    "MAX_SEQUENCE_LENGTH",
    "MODEL_ID",
    "NEGATIVE_SCENARIOS",
    "REQUIRED_LABELS",
    "RESOURCE_OBLIGATION_ROWS",
    "SCENARIOS",
    "VALID_SCENARIOS",
    "State",
    "Tick",
    "build_workflow",
    "contract_failures",
    "initial_state",
    "is_success",
    "is_terminal",
    "known_bad_states",
]
