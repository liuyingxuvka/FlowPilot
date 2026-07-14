"""FlowGuard singleton-identity authority model and live audit for FlowPilot.

The model separates intended plurality from illegal duplicate authority. The
live audit is read-only: it inspects current FlowPilot state and reports gaps
without mutating active runs.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
from typing import Any, Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = "simulations/flowpilot_singleton_identity_results.json"
MODEL_ID = "flowpilot_singleton_identity_authority"

LIVE_SINGLETON_REQUIRED_EVIDENCE_FILES = (
    {
        "surface": "parallel_flow_blocks",
        "relative_path": "route_state_snapshot.json",
    },
    {
        "surface": "router_daemon_writer",
        "relative_path": "runtime/router_daemon.lock",
    },
    {
        "surface": "packet_active_holder",
        "relative_path": "packet_ledger.json",
    },
    {
        "surface": "route_frontier_current_authority",
        "relative_path": "execution_frontier.json",
    },
)

LEGAL_PARALLEL_RUNS = "legal_parallel_runs"
DUPLICATE_DAEMON_WRITER = "duplicate_daemon_writer"
ACTIVE_PACKET_REPLAY = "active_packet_same_identity_replay"
ACTIVE_PACKET_CONFLICT = "active_packet_conflicting_holder"
PM_PACKAGE_SAME_BODY_REPLAY = "pm_package_same_body_replay"
PM_PACKAGE_DIFFERENT_BODY_CONFLICT = "pm_package_different_body_conflict"
ROUTE_REPLACEMENT_DISPOSED = "route_replacement_old_packet_disposed"
ROUTE_REPLACEMENT_UNDISPOSED = "route_replacement_old_packet_undisposed"
PACKET_BATCH_REPLACEMENT_STALE_REF = "packet_batch_replacement_stale_active_ref"
RETIRED_MATERIAL_SINGLETON_AUTHORITY_PRESENT = "retired_material_singleton_authority_present"
ACK_ONLY_OUTPUT_CLOSURE = "ack_only_output_closure"
FINAL_PROGRESS_ONLY_CLOSURE = "final_progress_only_closure"
MISSING_LEDGER_EVIDENCE = "missing_ledger_evidence"

SCENARIOS = (
    LEGAL_PARALLEL_RUNS,
    DUPLICATE_DAEMON_WRITER,
    ACTIVE_PACKET_REPLAY,
    ACTIVE_PACKET_CONFLICT,
    PM_PACKAGE_SAME_BODY_REPLAY,
    PM_PACKAGE_DIFFERENT_BODY_CONFLICT,
    ROUTE_REPLACEMENT_DISPOSED,
    ROUTE_REPLACEMENT_UNDISPOSED,
    PACKET_BATCH_REPLACEMENT_STALE_REF,
    RETIRED_MATERIAL_SINGLETON_AUTHORITY_PRESENT,
    ACK_ONLY_OUTPUT_CLOSURE,
    FINAL_PROGRESS_ONLY_CLOSURE,
    MISSING_LEDGER_EVIDENCE,
)

SAFE_SCENARIOS = {
    LEGAL_PARALLEL_RUNS,
    ACTIVE_PACKET_REPLAY,
    PM_PACKAGE_SAME_BODY_REPLAY,
    ROUTE_REPLACEMENT_DISPOSED,
}

RISK_SCENARIOS = {
    DUPLICATE_DAEMON_WRITER,
    ACTIVE_PACKET_CONFLICT,
    PM_PACKAGE_DIFFERENT_BODY_CONFLICT,
    ROUTE_REPLACEMENT_UNDISPOSED,
    PACKET_BATCH_REPLACEMENT_STALE_REF,
    RETIRED_MATERIAL_SINGLETON_AUTHORITY_PRESENT,
    ACK_ONLY_OUTPUT_CLOSURE,
    FINAL_PROGRESS_ONLY_CLOSURE,
}

EVIDENCE_INSUFFICIENT_SCENARIOS = {MISSING_LEDGER_EVIDENCE}


@dataclass(frozen=True)
class AuthorityRow:
    object_family: str
    legal_plurality: str
    singleton_scope: str
    canonical_owner: str
    identity_key: str
    generation_key: str
    legal_replay: str
    conflict_behavior: str
    old_object_disposition: str
    code_surfaces: tuple[str, ...]
    model_surfaces: tuple[str, ...]
    test_surfaces: tuple[str, ...]


def authority_matrix() -> tuple[AuthorityRow, ...]:
    return (
        AuthorityRow(
            object_family="parallel_flowpilot_runs",
            legal_plurality="multiple runs and Flow blocks are allowed",
            singleton_scope="per run operation target",
            canonical_owner="Router/Controller target selection",
            identity_key="run_id or run_root",
            generation_key="current pointer is UI focus only",
            legal_replay="background runs remain active when explicitly targeted",
            conflict_behavior="untargeted operation is authority risk",
            old_object_disposition="historical runs remain history/background, not current authority",
            code_surfaces=("skills/flowpilot/SKILL.md", "flowpilot_router_route_frontier_status_summary.py"),
            model_surfaces=("parallel-flowpilot-run-isolation",),
            test_surfaces=("flowpilot_persistent_router_daemon",),
        ),
        AuthorityRow(
            object_family="router_daemon_writer",
            legal_plurality="one writer per run",
            singleton_scope="run_root",
            canonical_owner="router daemon lock",
            identity_key="run_id + run_root + owner pid",
            generation_key="lock status + last_tick_at",
            legal_replay="attach to existing live daemon",
            conflict_behavior="reject second writer or require stale-lock recovery",
            old_object_disposition="released/error/stale lock requires explicit recovery evidence",
            code_surfaces=("skills/flowpilot/assets/flowpilot_router_daemon_runtime.py",),
            model_surfaces=("flowpilot_persistent_router_daemon",),
            test_surfaces=("tests/test_flowpilot_router_runtime_startup_daemon.py",),
        ),
        AuthorityRow(
            object_family="packet_active_holder",
            legal_plurality="one holder per packet lease",
            singleton_scope="run_id + packet_id + route/frontier version",
            canonical_owner="packet runtime active-holder lease",
            identity_key="packet_id + holder_role + holder_agent_id",
            generation_key="route_version + frontier_version",
            legal_replay="same holder/action lease replay is idempotent",
            conflict_behavior="wrong role, wrong agent, or stale route/frontier is rejected",
            old_object_disposition="superseded packet loses active holder authority",
            code_surfaces=("packet_runtime_active_holder_lease.py", "packet_runtime_active_holder_results.py"),
            model_surfaces=("flowpilot_packet_lifecycle", "flowpilot_persistent_router_daemon"),
            test_surfaces=("tests/test_flowpilot_router_runtime.py",),
        ),
        AuthorityRow(
            object_family="pm_package_disposition",
            legal_plurality="one semantic disposition per package identity",
            singleton_scope="router event + batch_id + packet_ids + packet_generation_id",
            canonical_owner="PM role-output package disposition writer",
            identity_key="batch_id + packet_ids + packet_generation_id",
            generation_key="packet_generation_id",
            legal_replay="same semantic identity and same body hash is idempotent",
            conflict_behavior="same identity with different body hash blocks or enters repair ownership",
            old_object_disposition="repair/reissue creates a new batch or packet generation",
            code_surfaces=("flowpilot_router_work_packets_pm_role_writes_decisions_package_disposition.py",),
            model_surfaces=("flowpilot_event_idempotency",),
            test_surfaces=("tests/test_flowpilot_router_runtime.py",),
        ),
        AuthorityRow(
            object_family="route_replacement_current_authority",
            legal_plurality="one current route/frontier after activation",
            singleton_scope="run_id + route_version + active node/sibling scope",
            canonical_owner="route mutation activation",
            identity_key="route_version + affected sibling nodes + repair_transaction_id",
            generation_key="route_version",
            legal_replay="same mutation transaction replay is idempotent",
            conflict_behavior="new branch cannot become current while old active work remains undisposed",
            old_object_disposition="old packet/evidence/node is superseded, stale, quarantined, migrated, or blocking",
            code_surfaces=("flowpilot_router_route.py", "flowpilot_router_route_frontier_context_drafts.py"),
            model_surfaces=("flowpilot_route_mutation_activation",),
            test_surfaces=("tests/router_runtime/route_mutation_sibling_replacement.py",),
        ),
        AuthorityRow(
            object_family="ordinary_packet_batch_generation",
            legal_plurality="one active batch reference per ordinary packet family",
            singleton_scope="run_id + batch_kind (research/current_node/pm_role_work)",
            canonical_owner="parallel packet-batch lifecycle",
            identity_key="batch_kind + active_batch_id + packet_ids",
            generation_key="batch_id + packet_generation_id",
            legal_replay="same batch identity and member set replay is idempotent",
            conflict_behavior="a stale active-batch reference cannot authorize current work",
            old_object_disposition="replaced batch reference is superseded, terminal, or removed",
            code_surfaces=(
                "flowpilot_router_work_packets_parallel.py",
                "flowpilot_router_work_packets_parallel_reconciliation.py",
            ),
            model_surfaces=("parallel-packet-batch-reconciliation",),
            test_surfaces=("tests/test_flowpilot_high_standard_control_flow.py",),
        ),
        AuthorityRow(
            object_family="ack_vs_output_completion",
            legal_plurality="ACK and output are separate surfaces",
            singleton_scope="wait_id + packet_id + output_contract_id",
            canonical_owner="wait reconciliation + role-output runtime",
            identity_key="ack id for receipt; result body hash for output",
            generation_key="packet/result generation",
            legal_replay="duplicate ACK settlement is idempotent",
            conflict_behavior="ACK-only semantic completion is a closure hazard",
            old_object_disposition="ACK rows close receipt waits only; output waits stay pending",
            code_surfaces=("flowpilot_router_card_returns.py", "role_output_runtime.py"),
            model_surfaces=("flowpilot_role_output_runtime", "wait-reconciliation"),
            test_surfaces=("tests/test_flowpilot_role_output_runtime.py",),
        ),
        AuthorityRow(
            object_family="final_closure_evidence",
            legal_plurality="many evidence rows, one closure claim boundary",
            singleton_scope="run_id + final route-wide gate ledger",
            canonical_owner="terminal ledger and PM closure approval",
            identity_key="effective route nodes + gate ids + evidence ids",
            generation_key="route_version + closure suite version",
            legal_replay="same proof artifact can be consumed once for its declared scope",
            conflict_behavior="progress-only, stale, or superseded evidence cannot close final ledger",
            old_object_disposition="stale/superseded evidence is explained or blocked",
            code_surfaces=("flowpilot_router_terminal_ledger.py",),
            model_surfaces=("flowpilot_model_maturation", "flowpilot_recursive_closure_reconciliation"),
            test_surfaces=("tests/test_flowpilot_router_runtime_terminal.py",),
        ),
    )


@dataclass(frozen=True)
class Tick:
    """One singleton authority classification step."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | safe | risk | evidence_insufficient
    scenario: str = "unset"
    object_family: str = ""
    intended_plurality: bool = False
    explicit_target_required: bool = False
    singleton_scope_named: bool = True
    canonical_owner_named: bool = True
    identity_key_named: bool = True
    generation_key_named: bool = True
    duplicate_authority_count: int = 0
    same_identity_replay: bool = False
    same_body_hash: bool = True
    authorized_reissue_or_repair: bool = False
    old_object_disposed: bool = True
    stale_evidence_consumed_as_current: bool = False
    retired_material_authority_present: bool = False
    progress_only_evidence_consumed_as_completion: bool = False
    ack_settled: bool = False
    output_completed: bool = False
    required_ledger_present: bool = True
    classification: str = ""


class Transition(NamedTuple):
    label: str
    state: State


class SingletonAuthorityStep:
    """Input x State -> Set(Output x State) for singleton authority checks."""

    name = "SingletonAuthorityStep"
    reads = (
        "object_family",
        "singleton_scope",
        "identity_key",
        "generation_key",
        "old_object_disposition",
    )
    writes = ("singleton_classification",)
    input_description = "one object-family singleton authority observation"
    output_description = "safe/risk/evidence-insufficient classification"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def initial_state() -> State:
    return State()


def _selected_state(scenario: str) -> State:
    if scenario == LEGAL_PARALLEL_RUNS:
        return State(
            status="running",
            scenario=scenario,
            object_family="parallel_flowpilot_runs",
            intended_plurality=True,
            explicit_target_required=True,
            duplicate_authority_count=3,
        )
    if scenario == DUPLICATE_DAEMON_WRITER:
        return State(
            status="running",
            scenario=scenario,
            object_family="router_daemon_writer",
            duplicate_authority_count=2,
        )
    if scenario == ACTIVE_PACKET_REPLAY:
        return State(
            status="running",
            scenario=scenario,
            object_family="packet_active_holder",
            duplicate_authority_count=1,
            same_identity_replay=True,
            same_body_hash=True,
        )
    if scenario == ACTIVE_PACKET_CONFLICT:
        return State(
            status="running",
            scenario=scenario,
            object_family="packet_active_holder",
            duplicate_authority_count=2,
            same_identity_replay=False,
        )
    if scenario == PM_PACKAGE_SAME_BODY_REPLAY:
        return State(
            status="running",
            scenario=scenario,
            object_family="pm_package_disposition",
            duplicate_authority_count=1,
            same_identity_replay=True,
            same_body_hash=True,
        )
    if scenario == PM_PACKAGE_DIFFERENT_BODY_CONFLICT:
        return State(
            status="running",
            scenario=scenario,
            object_family="pm_package_disposition",
            duplicate_authority_count=2,
            same_identity_replay=True,
            same_body_hash=False,
        )
    if scenario == ROUTE_REPLACEMENT_DISPOSED:
        return State(
            status="running",
            scenario=scenario,
            object_family="route_replacement_current_authority",
            duplicate_authority_count=1,
            old_object_disposed=True,
            authorized_reissue_or_repair=True,
        )
    if scenario == ROUTE_REPLACEMENT_UNDISPOSED:
        return State(
            status="running",
            scenario=scenario,
            object_family="route_replacement_current_authority",
            duplicate_authority_count=2,
            old_object_disposed=False,
            authorized_reissue_or_repair=True,
        )
    if scenario == PACKET_BATCH_REPLACEMENT_STALE_REF:
        return State(
            status="running",
            scenario=scenario,
            object_family="ordinary_packet_batch_generation",
            duplicate_authority_count=2,
            authorized_reissue_or_repair=True,
            old_object_disposed=False,
            stale_evidence_consumed_as_current=True,
        )
    if scenario == RETIRED_MATERIAL_SINGLETON_AUTHORITY_PRESENT:
        return State(
            status="running",
            scenario=scenario,
            object_family="retired_material_protocol",
            duplicate_authority_count=1,
            retired_material_authority_present=True,
        )
    if scenario == ACK_ONLY_OUTPUT_CLOSURE:
        return State(
            status="running",
            scenario=scenario,
            object_family="ack_vs_output_completion",
            duplicate_authority_count=1,
            ack_settled=True,
            output_completed=True,
        )
    if scenario == FINAL_PROGRESS_ONLY_CLOSURE:
        return State(
            status="running",
            scenario=scenario,
            object_family="final_closure_evidence",
            duplicate_authority_count=1,
            progress_only_evidence_consumed_as_completion=True,
        )
    if scenario == MISSING_LEDGER_EVIDENCE:
        return State(
            status="running",
            scenario=scenario,
            object_family="live_singleton_audit",
            required_ledger_present=False,
        )
    raise ValueError(f"unknown scenario: {scenario}")


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _selected_state(scenario))
        return
    if state.status != "running":
        return
    if not (
        state.singleton_scope_named
        and state.canonical_owner_named
        and state.identity_key_named
        and state.generation_key_named
    ):
        yield Transition(
            "classify_missing_authority_metadata",
            replace(state, status="evidence_insufficient", classification="evidence_insufficient"),
        )
        return
    if not state.required_ledger_present:
        yield Transition(
            "classify_missing_ledger_evidence",
            replace(state, status="evidence_insufficient", classification="evidence_insufficient"),
        )
        return
    if state.intended_plurality:
        label = (
            "classify_intended_plurality_with_explicit_target"
            if state.explicit_target_required
            else "classify_plurality_without_target_risk"
        )
        status = "safe" if state.explicit_target_required else "risk"
        yield Transition(label, replace(state, status=status, classification=status))
        return
    if state.same_identity_replay and not state.same_body_hash:
        yield Transition(
            "classify_same_identity_different_body_conflict",
            replace(state, status="risk", classification="risk"),
        )
        return
    if state.retired_material_authority_present:
        yield Transition(
            "classify_retired_material_authority_risk",
            replace(state, status="risk", classification="risk"),
        )
        return
    if state.stale_evidence_consumed_as_current:
        yield Transition(
            "classify_stale_evidence_current_authority_risk",
            replace(state, status="risk", classification="risk"),
        )
        return
    if state.same_identity_replay and state.same_body_hash:
        yield Transition(
            "classify_same_identity_replay_idempotent",
            replace(state, status="safe", classification="safe"),
        )
        return
    if state.duplicate_authority_count > 1:
        yield Transition(
            "classify_duplicate_authority_without_disposition",
            replace(state, status="risk", classification="risk"),
        )
        return
    if state.ack_settled and state.output_completed:
        yield Transition(
            "classify_ack_only_output_completion_risk",
            replace(state, status="risk", classification="risk"),
        )
        return
    if state.progress_only_evidence_consumed_as_completion:
        yield Transition(
            "classify_progress_only_completion_risk",
            replace(state, status="risk", classification="risk"),
        )
        return
    yield Transition("classify_singleton_safe", replace(state, status="safe", classification="safe"))


def is_terminal(state: State) -> bool:
    return state.status in {"safe", "risk", "evidence_insufficient"}


def is_success(state: State) -> bool:
    return is_terminal(state)


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return is_terminal(state)


def _hard_check_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "safe" and state.intended_plurality and not state.explicit_target_required:
        failures.append("intended plurality was marked safe without explicit operation target")
    if state.status == "safe" and state.duplicate_authority_count > 1 and not state.intended_plurality:
        if not state.same_identity_replay or not state.same_body_hash:
            failures.append("duplicate singleton authority was marked safe")
    if state.status == "safe" and state.same_identity_replay and not state.same_body_hash:
        failures.append("same singleton identity with different body hash was treated as replay")
    if state.status == "safe" and not state.old_object_disposed and state.authorized_reissue_or_repair:
        failures.append("replacement or reissue was safe without old-object disposition")
    if state.status == "safe" and state.stale_evidence_consumed_as_current:
        failures.append("stale singleton evidence was consumed as current")
    if state.status == "safe" and state.retired_material_authority_present:
        failures.append("retired material_scan/material_sufficiency/material_understanding authority was marked safe")
    if state.status == "safe" and state.progress_only_evidence_consumed_as_completion:
        failures.append("progress-only singleton evidence was consumed as completion")
    if state.status == "safe" and state.ack_settled and state.output_completed:
        failures.append("ACK settlement completed semantic output")
    if state.status == "safe" and not state.required_ledger_present:
        failures.append("missing singleton ledger evidence was treated as safe")
    if state.status == "risk" and state.same_identity_replay and state.same_body_hash and state.duplicate_authority_count <= 1:
        failures.append("idempotent singleton replay was overblocked as risk")
    return failures


def invariant_failures(state: State) -> list[str]:
    return _hard_check_failures(state)


def hard_invariant(state: State, trace: object) -> InvariantResult:
    del trace
    failures = _hard_check_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "flowpilot_singleton_identity_contract",
        "Singleton-scoped authority must be unique unless replay, repair, or disposition makes duplication legal.",
        hard_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


def build_workflow() -> Workflow:
    return Workflow((SingletonAuthorityStep(),), name=MODEL_ID)


def hazard_states() -> dict[str, State]:
    return {
        "plurality_without_target_marked_safe": replace(
            _selected_state(LEGAL_PARALLEL_RUNS),
            status="safe",
            explicit_target_required=False,
        ),
        "duplicate_daemon_writer_marked_safe": replace(
            _selected_state(DUPLICATE_DAEMON_WRITER),
            status="safe",
        ),
        "package_conflict_marked_replay": replace(
            _selected_state(PM_PACKAGE_DIFFERENT_BODY_CONFLICT),
            status="safe",
        ),
        "replacement_without_disposition_marked_safe": replace(
            _selected_state(ROUTE_REPLACEMENT_UNDISPOSED),
            status="safe",
        ),
        "stale_packet_batch_ref_marked_current": replace(
            _selected_state(PACKET_BATCH_REPLACEMENT_STALE_REF),
            status="safe",
        ),
        "retired_material_authority_marked_safe": replace(
            _selected_state(RETIRED_MATERIAL_SINGLETON_AUTHORITY_PRESENT),
            status="safe",
        ),
        "ack_only_output_marked_complete": replace(
            _selected_state(ACK_ONLY_OUTPUT_CLOSURE),
            status="safe",
        ),
        "progress_only_final_marked_complete": replace(
            _selected_state(FINAL_PROGRESS_ONLY_CLOSURE),
            status="safe",
        ),
        "missing_ledger_marked_safe": replace(
            _selected_state(MISSING_LEDGER_EVIDENCE),
            status="safe",
        ),
        "idempotent_replay_overblocked": replace(
            _selected_state(PM_PACKAGE_SAME_BODY_REPLAY),
            status="risk",
        ),
    }


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return None, "not_object"
        return payload, ""
    except FileNotFoundError:
        return None, "missing"
    except Exception as exc:
        return None, repr(exc)


def live_singleton_required_evidence_files() -> tuple[dict[str, str], ...]:
    return tuple(dict(row) for row in LIVE_SINGLETON_REQUIRED_EVIDENCE_FILES)


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return f"<external>/{path.name}"


def _surface(name: str, status: str, detail: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "surface": name,
        "status": status,
        "detail": detail,
        "evidence": evidence or {},
    }


def _active_packet_records(packet_ledger: dict[str, Any]) -> list[dict[str, Any]]:
    terminal_statuses = {
        "absorbed",
        "cancelled",
        "completed",
        "done",
        "quarantined",
        "superseded",
        "superseded-by-replacement",
        "terminal",
    }
    records = packet_ledger.get("packets", [])
    active = []
    for record in records if isinstance(records, list) else []:
        status = str(record.get("active_packet_status") or record.get("status") or "")
        if status and status not in terminal_statuses:
            active.append(record)
    return active


ORDINARY_PACKET_BATCH_KINDS = frozenset({"research", "current_node", "pm_role_work"})


def _ordinary_packet_batch_generation_surface(run_root: Path, root: Path) -> dict[str, Any]:
    batch_root = run_root / "packet_batches"
    if not batch_root.exists():
        return _surface(
            "ordinary_packet_batch_generation",
            "safe",
            "no ordinary packet batch currently claims active generation authority",
            {"path": _rel(batch_root, root), "active_ref_count": 0},
        )

    active_refs = sorted(batch_root.glob("active_*.json"))
    invalid_refs: list[dict[str, str]] = []
    retired_refs: list[str] = []
    unexpected_kinds: list[str] = []
    active_rows: list[dict[str, str]] = []
    active_ids_by_kind: dict[str, set[str]] = {}
    for ref_path in active_refs:
        implied_kind = ref_path.stem.removeprefix("active_")
        ref, ref_error = _read_json(ref_path)
        if implied_kind == "material_scan":
            retired_refs.append(_rel(ref_path, root))
            continue
        if ref is None:
            invalid_refs.append({"path": _rel(ref_path, root), "error": ref_error})
            continue
        batch_kind = str(ref.get("batch_kind") or implied_kind)
        if batch_kind == "material_scan":
            retired_refs.append(_rel(ref_path, root))
            continue
        if batch_kind not in ORDINARY_PACKET_BATCH_KINDS:
            unexpected_kinds.append(batch_kind)
            continue
        active_batch_id = str(ref.get("active_batch_id") or "")
        batch_path_value = str(ref.get("batch_path") or "")
        if not active_batch_id or not batch_path_value:
            invalid_refs.append(
                {
                    "path": _rel(ref_path, root),
                    "error": "missing active_batch_id or batch_path",
                }
            )
            continue
        batch_path = root / batch_path_value
        batch, batch_error = _read_json(batch_path)
        if batch is None:
            invalid_refs.append({"path": _rel(batch_path, root), "error": batch_error})
            continue
        if (
            str(batch.get("batch_id") or "") != active_batch_id
            or str(batch.get("batch_kind") or "") != batch_kind
        ):
            invalid_refs.append(
                {
                    "path": _rel(batch_path, root),
                    "error": "active reference identity does not match batch payload",
                }
            )
            continue
        active_ids_by_kind.setdefault(batch_kind, set()).add(active_batch_id)
        active_rows.append(
            {
                "batch_kind": batch_kind,
                "active_batch_id": active_batch_id,
                "ref_path": _rel(ref_path, root),
                "batch_path": _rel(batch_path, root),
            }
        )

    duplicate_family_authority = sorted(
        batch_kind
        for batch_kind, batch_ids in active_ids_by_kind.items()
        if len(batch_ids) > 1
    )
    if retired_refs or unexpected_kinds or duplicate_family_authority:
        return _surface(
            "ordinary_packet_batch_generation",
            "risk",
            "active packet-batch references expose retired, unknown, or duplicate family authority",
            {
                "retired_material_refs": retired_refs,
                "unexpected_batch_kinds": sorted(set(unexpected_kinds)),
                "duplicate_family_authority": duplicate_family_authority,
                "active_rows": active_rows,
                "invalid_refs": invalid_refs,
            },
        )
    if invalid_refs:
        return _surface(
            "ordinary_packet_batch_generation",
            "evidence_insufficient",
            "ordinary packet-batch active reference could not be verified",
            {"invalid_refs": invalid_refs, "active_rows": active_rows},
        )
    return _surface(
        "ordinary_packet_batch_generation",
        "safe",
        "each active ordinary packet family has one identity-matched batch reference",
        {"active_rows": active_rows, "active_ref_count": len(active_rows)},
    )


def build_live_singleton_audit(repo_root: Path | str = ROOT) -> dict[str, Any]:
    root = Path(repo_root)
    current, current_error = _read_json(root / ".flowpilot" / "current.json")
    surfaces: list[dict[str, Any]] = []
    if current is None:
        surfaces.append(_surface("current_run_pointer", "evidence_insufficient", current_error))
        return _live_summary(surfaces)

    run_id = str(current.get("run_id") or "")
    run_root_value = str(current.get("run_root") or "")
    run_root = root / run_root_value if run_root_value else root / ".flowpilot" / "runs" / run_id
    if run_id and run_root_value:
        surfaces.append(
            _surface(
                "current_run_pointer",
                "safe",
                "current pointer is present and treated as UI focus/default target",
                {"run_id": run_id, "run_root": _rel(run_root, root)},
            )
        )
    else:
        surfaces.append(_surface("current_run_pointer", "evidence_insufficient", "missing run id or run root", current))

    snapshot, snapshot_error = _read_json(run_root / "route_state_snapshot.json")
    if snapshot is None:
        surfaces.append(_surface("parallel_flow_blocks", "evidence_insufficient", snapshot_error, {"path": _rel(run_root / "route_state_snapshot.json", root)}))
    else:
        catalog = snapshot.get("active_ui_task_catalog", {})
        tasks = catalog.get("active_tasks", []) if isinstance(catalog, dict) else []
        active_count = len(tasks) if isinstance(tasks, list) else 0
        untargeted = [
            item.get("target_id")
            for item in tasks
            if isinstance(item, dict) and not item.get("operation_target_allowed", False)
        ]
        status = "risk" if untargeted else "safe"
        surfaces.append(
            _surface(
                "parallel_flow_blocks",
                status,
                "parallel Flow blocks are legal when each operation has a target surface",
                {"active_task_count": active_count, "untargeted": untargeted[:10]},
            )
        )

    daemon_lock, daemon_lock_error = _read_json(run_root / "runtime" / "router_daemon.lock")
    daemon_status, daemon_status_error = _read_json(run_root / "runtime" / "router_daemon_status.json")
    if daemon_lock is None:
        surfaces.append(_surface("router_daemon_writer", "evidence_insufficient", daemon_lock_error, {"path": _rel(run_root / "runtime" / "router_daemon.lock", root)}))
    else:
        lock_status = str(daemon_lock.get("status") or "")
        single_writer = daemon_lock.get("single_writer_lock") is True
        lock_run = str(daemon_lock.get("run_id") or "")
        status_error = ""
        if isinstance(daemon_status, dict):
            status_error = str(daemon_status.get("error") or "")
        elif daemon_status_error and daemon_status_error != "missing":
            status_error = daemon_status_error
        if lock_status == "active" and single_writer and lock_run == run_id and not status_error:
            status = "safe"
            detail = "one active run-scoped daemon writer lock is present"
        elif lock_status in {"released", "terminal", "stopped"}:
            status = "safe"
            detail = "daemon lock is non-active"
        else:
            status = "risk"
            detail = "daemon lock/status does not prove one active writer"
        surfaces.append(
            _surface(
                "router_daemon_writer",
                status,
                detail,
                {
                    "lock_status": lock_status,
                    "single_writer_lock": single_writer,
                    "lock_run_id": lock_run,
                    "status_error": status_error,
                },
            )
        )

    packet_ledger, packet_error = _read_json(run_root / "packet_ledger.json")
    if packet_ledger is None:
        surfaces.append(_surface("packet_active_holder", "evidence_insufficient", packet_error, {"path": _rel(run_root / "packet_ledger.json", root)}))
    else:
        packet_ids: dict[str, list[dict[str, Any]]] = {}
        for record in _active_packet_records(packet_ledger):
            packet_id = str(record.get("packet_id") or "")
            if packet_id:
                packet_ids.setdefault(packet_id, []).append(record)
        duplicate_packet_ids = {
            packet_id: records
            for packet_id, records in packet_ids.items()
            if len(
                {
                    (
                        str(record.get("active_packet_holder") or ""),
                        str(record.get("active_packet_status") or record.get("status") or ""),
                    )
                    for record in records
                }
            )
            > 1
        }
        status = "risk" if duplicate_packet_ids else "safe"
        surfaces.append(
            _surface(
                "packet_active_holder",
                status,
                "active packet records have no conflicting holder/status pairs for the same packet id",
                {
                    "active_packet_id": packet_ledger.get("active_packet_id"),
                    "active_record_count": sum(len(records) for records in packet_ids.values()),
                    "duplicate_packet_ids": sorted(duplicate_packet_ids.keys()),
                },
            )
        )

    frontier, frontier_error = _read_json(run_root / "execution_frontier.json")
    if frontier is None:
        surfaces.append(_surface("route_frontier_current_authority", "evidence_insufficient", frontier_error, {"path": _rel(run_root / "execution_frontier.json", root)}))
    else:
        pending = frontier.get("pending_route_mutation") if isinstance(frontier, dict) else None
        old_packet_status = ""
        if isinstance(packet_ledger, dict):
            old_packet_status = str(packet_ledger.get("active_packet_status") or "")
        if pending and "superseded" not in old_packet_status and old_packet_status:
            status = "risk"
            detail = "pending route mutation exists while active packet status is not superseded"
        else:
            status = "safe"
            detail = "frontier does not expose an undisposed replacement route conflict"
        surfaces.append(
            _surface(
                "route_frontier_current_authority",
                status,
                detail,
                {
                    "frontier_status": frontier.get("status"),
                    "phase": frontier.get("phase"),
                    "pending_route_mutation": bool(pending),
                    "active_packet_status": old_packet_status,
                },
            )
        )

    surfaces.append(_ordinary_packet_batch_generation_surface(run_root, root))

    return _live_summary(surfaces)


def _live_summary(surfaces: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for surface in surfaces:
        status = str(surface.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return {
        "ok": counts.get("risk", 0) == 0,
        "result_type": "flowpilot_live_singleton_audit",
        "surface_count": len(surfaces),
        "status_counts": dict(sorted(counts.items())),
        "risk_count": counts.get("risk", 0),
        "evidence_insufficient_count": counts.get("evidence_insufficient", 0),
        "surfaces": surfaces,
        "mutation_performed": False,
    }


def matrix_rows_as_dicts() -> list[dict[str, Any]]:
    return [
        {
            "object_family": row.object_family,
            "legal_plurality": row.legal_plurality,
            "singleton_scope": row.singleton_scope,
            "canonical_owner": row.canonical_owner,
            "identity_key": row.identity_key,
            "generation_key": row.generation_key,
            "legal_replay": row.legal_replay,
            "conflict_behavior": row.conflict_behavior,
            "old_object_disposition": row.old_object_disposition,
            "code_surfaces": list(row.code_surfaces),
            "model_surfaces": list(row.model_surfaces),
            "test_surfaces": list(row.test_surfaces),
        }
        for row in authority_matrix()
    ]
