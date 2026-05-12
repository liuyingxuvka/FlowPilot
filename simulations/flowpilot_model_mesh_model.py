"""FlowGuard model mesh for FlowPilot model-level authority.

This model sits above the existing deep FlowPilot models. It does not
re-simulate every child model. Instead, it models when a child model result,
live audit, conformance replay, packet authority record, or repair transaction
can be treated as enough authority to continue a FlowPilot run.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, NamedTuple, Sequence, Tuple

try:
    from flowguard import FunctionResult, Invariant, InvariantResult, Workflow
except Exception:  # pragma: no cover - runner performs the explicit preflight.
    FunctionResult = Invariant = InvariantResult = Workflow = None  # type: ignore[assignment]


SAFE_DECISIONS = {"mesh_green_can_continue"}
BLOCKING_DECISIONS = {
    "blocked_by_cross_model_contradiction",
    "blocked_by_live_evidence",
    "blocked_by_missing_conformance",
    "blocked_by_stale_model_result",
    "model_coverage_insufficient",
}

EVIDENCE_ORDER = {
    "none": 0,
    "abstract_green": 1,
    "hazard_green": 2,
    "live_current_green": 3,
    "conformance_green": 4,
}

REPAIR_OUTCOME_KEYS = ("success", "blocker", "protocol_blocker")
LEAF_ONLY_REPAIR_EVENTS = {"pm_registers_current_node_packet"}


@dataclass(frozen=True)
class State:
    scenario: str = "new"
    status: str = "new"
    decision: str = "none"
    model_registered: bool = False
    model_result_ok: bool = False
    model_result_run_matches_current: bool = False
    model_result_fresh: bool = False
    evidence_tier: str = "none"
    required_tier: str = "live_current_green"
    live_required: bool = True
    live_audit_skipped: bool = False
    conformance_required: bool = False
    conformance_skipped: bool = False
    current_state_classified: bool = False
    active_blocker_present: bool = False
    safe_to_continue_claimed: bool = False
    current_authorities_agree: bool = True
    status_summary_reports_blocked: bool = False
    collapsed_repair_outcome_events: bool = False
    repair_event_node_compatible: bool = True
    parent_repair_reuses_leaf_event: bool = False
    role_origin_checked: bool = True
    completed_agent_id_belongs_to_role: bool = True
    packet_evidence_accepted: bool = False
    known_hazard_live_projection_available: bool = True
    missing_conformance_adapter: bool = False
    sealed_body_opened_by_mesh: bool = False
    coverage_parse_errors_ignored: bool = False
    install_requires_safe_to_continue: bool = False
    installed_skill_matches_repo: bool = True
    local_sync_required: bool = False
    control_transaction_registry_registered: bool = True
    control_transaction_registry_valid: bool = True
    control_transaction_commit_scope_complete: bool = True


@dataclass(frozen=True)
class Tick:
    """One model mesh decision step."""


@dataclass(frozen=True)
class Action:
    name: str


class Transition(NamedTuple):
    label: str
    state: State


def _valid_live_state(name: str) -> State:
    return State(
        scenario=name,
        status="selected",
        decision="mesh_green_can_continue",
        model_registered=True,
        model_result_ok=True,
        model_result_run_matches_current=True,
        model_result_fresh=True,
        evidence_tier="live_current_green",
        required_tier="live_current_green",
        current_state_classified=True,
        current_authorities_agree=True,
        role_origin_checked=True,
        completed_agent_id_belongs_to_role=True,
        known_hazard_live_projection_available=True,
        installed_skill_matches_repo=True,
    )


SCENARIOS: Dict[str, State] = {
    "valid_live_can_continue": _valid_live_state("valid_live_can_continue"),
    "valid_conformance_can_continue": replace(
        _valid_live_state("valid_conformance_can_continue"),
        evidence_tier="conformance_green",
        required_tier="conformance_green",
        conformance_required=True,
        conformance_skipped=False,
    ),
    "valid_blocked_current_state": replace(
        _valid_live_state("valid_blocked_current_state"),
        decision="blocked_by_live_evidence",
        active_blocker_present=True,
        safe_to_continue_claimed=False,
        status_summary_reports_blocked=True,
    ),
    "valid_missing_conformance_boundary": replace(
        _valid_live_state("valid_missing_conformance_boundary"),
        decision="blocked_by_missing_conformance",
        evidence_tier="live_current_green",
        required_tier="conformance_green",
        conformance_required=True,
        missing_conformance_adapter=True,
    ),
    "abstract_green_used_to_continue": replace(
        _valid_live_state("abstract_green_used_to_continue"),
        evidence_tier="abstract_green",
        current_state_classified=False,
    ),
    "skipped_live_audit_used_to_continue": replace(
        _valid_live_state("skipped_live_audit_used_to_continue"),
        live_audit_skipped=True,
        current_state_classified=False,
    ),
    "stale_run_result_used": replace(
        _valid_live_state("stale_run_result_used"),
        model_result_run_matches_current=False,
        model_result_fresh=False,
    ),
    "unregistered_model_authoritative": replace(
        _valid_live_state("unregistered_model_authoritative"),
        model_registered=False,
    ),
    "hidden_active_blocker": replace(
        _valid_live_state("hidden_active_blocker"),
        active_blocker_present=True,
        safe_to_continue_claimed=True,
        status_summary_reports_blocked=True,
    ),
    "current_authority_mismatch": replace(
        _valid_live_state("current_authority_mismatch"),
        current_authorities_agree=False,
    ),
    "collapsed_repair_outcomes": replace(
        _valid_live_state("collapsed_repair_outcomes"),
        collapsed_repair_outcome_events=True,
    ),
    "parent_repair_leaf_event": replace(
        _valid_live_state("parent_repair_leaf_event"),
        repair_event_node_compatible=False,
        parent_repair_reuses_leaf_event=True,
    ),
    "packet_role_origin_unchecked": replace(
        _valid_live_state("packet_role_origin_unchecked"),
        role_origin_checked=False,
        completed_agent_id_belongs_to_role=False,
        packet_evidence_accepted=True,
    ),
    "known_hazard_without_live_projection": replace(
        _valid_live_state("known_hazard_without_live_projection"),
        known_hazard_live_projection_available=False,
    ),
    "sealed_body_opened_by_mesh": replace(
        _valid_live_state("sealed_body_opened_by_mesh"),
        sealed_body_opened_by_mesh=True,
    ),
    "coverage_parse_errors_ignored": replace(
        _valid_live_state("coverage_parse_errors_ignored"),
        coverage_parse_errors_ignored=True,
    ),
    "install_requires_safe_continue": replace(
        _valid_live_state("install_requires_safe_continue"),
        decision="blocked_by_live_evidence",
        active_blocker_present=True,
        status_summary_reports_blocked=True,
        safe_to_continue_claimed=False,
        install_requires_safe_to_continue=True,
    ),
    "installed_skill_stale_accepted": replace(
        _valid_live_state("installed_skill_stale_accepted"),
        installed_skill_matches_repo=False,
        local_sync_required=True,
    ),
    "missing_conformance_claims_runtime": replace(
        _valid_live_state("missing_conformance_claims_runtime"),
        conformance_required=True,
        missing_conformance_adapter=True,
        required_tier="conformance_green",
        evidence_tier="live_current_green",
    ),
    "control_transaction_registry_missing": replace(
        _valid_live_state("control_transaction_registry_missing"),
        control_transaction_registry_registered=False,
        control_transaction_registry_valid=False,
    ),
    "control_transaction_partial_commit_accepted": replace(
        _valid_live_state("control_transaction_partial_commit_accepted"),
        control_transaction_commit_scope_complete=False,
    ),
}

VALID_SCENARIOS = {
    "valid_live_can_continue",
    "valid_conformance_can_continue",
    "valid_blocked_current_state",
    "valid_missing_conformance_boundary",
}

NEGATIVE_SCENARIOS = set(SCENARIOS) - VALID_SCENARIOS


def input_alphabet() -> List[str]:
    return [f"select_{name}" for name in SCENARIOS] + [
        f"accept_{name}" for name in sorted(VALID_SCENARIOS)
    ] + [f"reject_{name}" for name in sorted(NEGATIVE_SCENARIOS)]


def initial_state() -> State:
    return State()


def mesh_failures(state: State) -> List[str]:
    failures: List[str] = []
    if state.decision in SAFE_DECISIONS:
        if not state.model_registered:
            failures.append("unregistered_model_result_cannot_authorize_continue")
        if not state.model_result_ok:
            failures.append("failed_model_result_cannot_authorize_continue")
        if not state.model_result_run_matches_current or not state.model_result_fresh:
            failures.append("stale_or_foreign_model_result_cannot_authorize_continue")
        if EVIDENCE_ORDER.get(state.evidence_tier, 0) < EVIDENCE_ORDER.get(state.required_tier, 0):
            failures.append("evidence_tier_below_required_runtime_confidence")
        if state.live_required and state.live_audit_skipped:
            failures.append("live_required_but_audit_skipped")
        if state.conformance_required and state.conformance_skipped:
            failures.append("conformance_required_but_replay_skipped")
        if state.active_blocker_present or state.safe_to_continue_claimed and state.status_summary_reports_blocked:
            failures.append("active_blocker_cannot_be_safe_to_continue")
        if not state.current_authorities_agree:
            failures.append("current_authorities_disagree")
        if state.collapsed_repair_outcome_events:
            failures.append("repair_outcome_events_collapsed")
        if not state.repair_event_node_compatible or state.parent_repair_reuses_leaf_event:
            failures.append("repair_event_not_compatible_with_active_node")
        if state.packet_evidence_accepted and (
            not state.role_origin_checked or not state.completed_agent_id_belongs_to_role
        ):
            failures.append("packet_authority_not_verified_before_acceptance")
        if not state.known_hazard_live_projection_available:
            failures.append("known_hazard_lacks_live_projection")
        if state.missing_conformance_adapter and state.required_tier == "conformance_green":
            failures.append("missing_conformance_adapter_cannot_claim_runtime_conformance")
        if not state.current_state_classified:
            failures.append("current_state_not_classified")
        if not state.installed_skill_matches_repo or state.local_sync_required:
            failures.append("installed_skill_not_synced_with_repo_model")
        if not state.control_transaction_registry_registered or not state.control_transaction_registry_valid:
            failures.append("control_transaction_registry_not_authoritative")
        if not state.control_transaction_commit_scope_complete:
            failures.append("control_transaction_commit_scope_incomplete")

    if state.decision in BLOCKING_DECISIONS:
        if state.safe_to_continue_claimed:
            failures.append("blocking_decision_must_not_claim_safe_to_continue")
        if not state.current_state_classified:
            failures.append("blocking_decision_must_classify_current_state")
        if state.install_requires_safe_to_continue:
            failures.append("install_check_must_accept_classified_blocked_state")

    if state.sealed_body_opened_by_mesh:
        failures.append("mesh_must_not_open_sealed_bodies")
    if state.coverage_parse_errors_ignored:
        failures.append("coverage_parse_errors_must_block_green_result")

    return sorted(set(failures))


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        for name, scenario in sorted(SCENARIOS.items()):
            yield Transition(f"select_{name}", scenario)
        return
    if state.status == "selected":
        failures = mesh_failures(state)
        terminal = "rejected" if failures else "accepted"
        yield Transition(f"{terminal.removesuffix('ed')}_{state.scenario}", replace(state, status=terminal))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted"


def terminal_predicate(_input_symbol: str, state: State, _trace: Sequence[Any]) -> bool:
    return is_terminal(state)


class ModelMeshStep:
    """Model one FlowPilot model-mesh authority transition.

    Input x State -> Set(Output x State)
    reads: child model result metadata, current run metadata, packet authority,
    repair transaction table, coverage and install status
    writes: one mesh authority decision or one classified blocking decision
    idempotency: model decisions are pure classifications of immutable evidence
    """

    name = "ModelMeshStep"
    input_description = "model mesh tick"
    output_description = "one model-mesh authority transition"
    reads = (
        "model_result_metadata",
        "current_run_metadata",
        "packet_authority_metadata",
        "repair_transaction_metadata",
        "control_transaction_registry_status",
        "coverage_status",
        "install_status",
    )
    writes = ("mesh_authority_decision", "classified_blocking_decision")
    idempotency = "pure evidence classification keyed by run_id and model fingerprint"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def accepted_states_are_safe(state: State, _trace: Sequence[Any]) -> InvariantResult:
    if state.status == "accepted":
        failures = mesh_failures(state)
        if failures:
            return InvariantResult.fail(f"accepted unsafe mesh decision: {failures}")
    if state.status == "rejected":
        failures = mesh_failures(state)
        if not failures:
            return InvariantResult.fail("rejected a safe mesh decision")
    return InvariantResult.pass_()


def continue_requires_live_or_conformance_authority(state: State, _trace: Sequence[Any]) -> InvariantResult:
    if state.status == "accepted" and state.decision in SAFE_DECISIONS:
        if EVIDENCE_ORDER[state.evidence_tier] < EVIDENCE_ORDER[state.required_tier]:
            return InvariantResult.fail("continue decision below required evidence tier")
    return InvariantResult.pass_()


def active_blocker_requires_blocking_decision(state: State, _trace: Sequence[Any]) -> InvariantResult:
    if state.status == "accepted" and state.active_blocker_present and state.decision in SAFE_DECISIONS:
        return InvariantResult.fail("active blocker accepted as safe to continue")
    return InvariantResult.pass_()


def repair_and_packet_authority_must_be_distinct(state: State, _trace: Sequence[Any]) -> InvariantResult:
    if state.status == "accepted" and state.decision in SAFE_DECISIONS:
        if state.collapsed_repair_outcome_events:
            return InvariantResult.fail("repair outcome events collapsed")
        if state.packet_evidence_accepted and (
            not state.role_origin_checked or not state.completed_agent_id_belongs_to_role
        ):
            return InvariantResult.fail("packet evidence accepted without role authority")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "accepted_states_are_safe",
        "Accepted mesh decisions cannot contain known model-mesh failures.",
        accepted_states_are_safe,
    ),
    Invariant(
        "continue_requires_live_or_conformance_authority",
        "Continue decisions require live-current or conformance authority.",
        continue_requires_live_or_conformance_authority,
    ),
    Invariant(
        "active_blocker_requires_blocking_decision",
        "Active blockers must produce a blocking decision, not safe-to-continue.",
        active_blocker_requires_blocking_decision,
    ),
    Invariant(
        "repair_and_packet_authority_must_be_distinct",
        "Repair outcomes and packet authority must be distinct before acceptance.",
        repair_and_packet_authority_must_be_distinct,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 2


def build_workflow() -> Workflow:
    return Workflow((ModelMeshStep(),), name="flowpilot_model_mesh")


def invariant_failures(state: State) -> List[str]:
    failures: List[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(str(result.message))
    return failures


def hazard_states() -> Dict[str, State]:
    return {name: SCENARIOS[name] for name in sorted(NEGATIVE_SCENARIOS)}


def expected_failures_by_hazard() -> Dict[str, List[str]]:
    return {name: mesh_failures(state) for name, state in hazard_states().items()}


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        return {"__parse_error__": str(exc)}


def _resolve_run_root(project_root: Path, run_id: str | None) -> Tuple[Path | None, str | None, List[str]]:
    reasons: List[str] = []
    current = _read_json(project_root / ".flowpilot" / "current.json")
    if run_id is None and isinstance(current, Mapping):
        run_id = str(current.get("current_run_id") or current.get("run_id") or "")
    if not run_id:
        reasons.append("no_current_run_id")
        return None, None, reasons
    run_root = project_root / ".flowpilot" / "runs" / run_id
    if not run_root.exists():
        reasons.append("current_run_root_missing")
        return None, run_id, reasons
    return run_root, run_id, reasons


def _dict_get(data: Any, path: Sequence[Any], default: Any = None) -> Any:
    cursor = data
    for key in path:
        if isinstance(cursor, Mapping):
            cursor = cursor.get(key)
            continue
        if isinstance(cursor, list) and isinstance(key, int) and 0 <= key < len(cursor):
            cursor = cursor[key]
            continue
        else:
            return default
    return cursor


def _iter_dicts(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, Mapping):
                yield item


def _collapsed_repair_events(repair_index: Any) -> bool:
    transactions: List[Any] = []
    active_transaction = _dict_get(repair_index, ["active_transaction"])
    if isinstance(active_transaction, Mapping):
        transactions.append(active_transaction)
    raw_transactions = _dict_get(repair_index, ["transactions"], [])
    if isinstance(raw_transactions, Mapping):
        transactions.extend(raw_transactions.values())
    elif isinstance(raw_transactions, list):
        transactions.extend(raw_transactions)
    for tx in transactions:
        table = _dict_get(tx, ["outcome_table"], {})
        if not isinstance(table, Mapping):
            continue
        events = []
        for key in REPAIR_OUTCOME_KEYS:
            event = _dict_get(table, [key, "event"])
            if isinstance(event, str) and event:
                events.append(event)
        if len(events) >= 2 and len(set(events)) < len(events):
            return True
    return False


def _parent_repair_uses_leaf_event(repair_index: Any, frontier: Any) -> bool:
    active_node_kind = _dict_get(frontier, ["active_path", 0, "node_kind"])
    if active_node_kind != "parent":
        return False
    transactions: List[Any] = []
    active_transaction = _dict_get(repair_index, ["active_transaction"])
    if isinstance(active_transaction, Mapping):
        transactions.append(active_transaction)
    raw_transactions = _dict_get(repair_index, ["transactions"], [])
    if isinstance(raw_transactions, Mapping):
        transactions.extend(raw_transactions.values())
    elif isinstance(raw_transactions, list):
        transactions.extend(raw_transactions)
    for tx in transactions:
        if _dict_get(tx, ["status"]) not in {"active", "committed"}:
            continue
        table = _dict_get(tx, ["outcome_table"], {})
        for key in REPAIR_OUTCOME_KEYS:
            event = _dict_get(table, [key, "event"])
            if event in LEAF_ONLY_REPAIR_EVENTS:
                return True
    return False


def _packet_authority_unchecked(packet_ledger: Any) -> bool:
    packets = _dict_get(packet_ledger, ["packets"], {})
    for packet in _iter_dicts(packets.values() if isinstance(packets, Mapping) else packets):
        has_body = bool(
            _dict_get(packet, ["body_hash"])
            or _dict_get(packet, ["packet_body_hash"])
            or _dict_get(packet, ["result_body_hash"])
            or _dict_get(packet, ["result_envelope", "body_hash"])
            or _dict_get(packet, ["decision_body_hash"])
        )
        if not has_body:
            continue
        if _dict_get(packet, ["result_envelope", "completed_agent_id_belongs_to_role"], True) is False:
            return True
        if _dict_get(packet, ["role_origin_audit", "result_envelope_completed_by_role_checked"], True) is False:
            return True
    return False


def _authorities_agree(frontier: Any, packet_ledger: Any, status_summary: Any) -> bool:
    active_node = _dict_get(frontier, ["execution_frontier", "active_node_id"]) or _dict_get(
        frontier, ["active_node_id"]
    )
    status_node = _dict_get(status_summary, ["route", "active_node_id"]) or _dict_get(
        status_summary, ["active_node_id"]
    )
    if active_node and status_node and active_node != status_node:
        return False

    blocker_active = bool(
        _dict_get(status_summary, ["current_blocker", "active"], False)
        or _dict_get(status_summary, ["blocker", "active"], False)
    )
    status_kind = _dict_get(status_summary, ["state_kind"])
    if blocker_active and status_kind not in {"blocked", "protocol_blocked", "needs_repair"}:
        return False

    active_packets = _dict_get(packet_ledger, ["active_packets"], [])
    if isinstance(active_packets, list):
        for packet in active_packets:
            packet_node = _dict_get(packet, ["node_id"])
            if active_node and packet_node and packet_node != active_node and not blocker_active:
                return False
    return True


def _live_projection_findings(
    *,
    run_id: str | None,
    decision: str,
    current_run_can_continue: bool,
    blocking_reasons: Sequence[str],
    projected_failures: Sequence[str],
) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for reason in sorted(set(blocking_reasons)):
        findings.append(
            {
                "id": f"flowpilot_model_mesh.{reason}",
                "severity": "blocking",
                "message": f"Current FlowPilot run is not permitted to continue: {reason}",
                "run_id": run_id,
                "decision": decision,
                "reason": reason,
                "current_run_can_continue": current_run_can_continue,
            }
        )
    for failure in sorted(set(projected_failures)):
        findings.append(
            {
                "id": f"flowpilot_model_mesh.projected_failure.{failure}",
                "severity": "error",
                "message": f"Model mesh projection is internally unsafe: {failure}",
                "run_id": run_id,
                "decision": decision,
                "reason": failure,
                "current_run_can_continue": current_run_can_continue,
            }
        )
    if decision != "mesh_green_can_continue" and not findings:
        findings.append(
            {
                "id": "flowpilot_model_mesh.not_green",
                "severity": "blocking",
                "message": f"Current FlowPilot run is classified as {decision}, not mesh_green_can_continue.",
                "run_id": run_id,
                "decision": decision,
                "reason": "not_mesh_green_can_continue",
                "current_run_can_continue": current_run_can_continue,
            }
        )
    return findings


def project_live_run(project_root: str | Path = ".", run_id: str | None = None) -> Dict[str, Any]:
    """Project metadata-only live run facts into the model mesh.

    The projection deliberately reads only structured metadata files. Packet,
    report, result, and decision body files remain sealed.
    """

    root = Path(project_root)
    run_root, resolved_run_id, reasons = _resolve_run_root(root, run_id)
    if run_root is None:
        state = State(
            scenario="live_run_projection",
            status="selected",
            decision="model_coverage_insufficient",
            current_state_classified=True,
            evidence_tier="none",
            required_tier="live_current_green",
        )
        projected_failures = mesh_failures(state)
        classification_ok = not projected_failures
        current_run_can_continue = False
        findings = _live_projection_findings(
            run_id=resolved_run_id,
            decision=state.decision,
            current_run_can_continue=current_run_can_continue,
            blocking_reasons=reasons,
            projected_failures=projected_failures,
        )
        return {
            "ok": classification_ok,
            "classification_ok": classification_ok,
            "current_run_can_continue": current_run_can_continue,
            "permission": "blocked_or_insufficient",
            "run_id": resolved_run_id,
            "decision": state.decision,
            "blocking_reasons": reasons,
            "findings": findings,
            "metadata_only": True,
            "sealed_body_opened_by_mesh": False,
            "projected_state": state.__dict__,
            "projected_failures": projected_failures,
        }

    frontier = _read_json(run_root / "execution_frontier.json")
    packet_ledger = _read_json(run_root / "packet_ledger.json")
    status_summary = _read_json(run_root / "display" / "current_status_summary.json")
    repair_index = _read_json(run_root / "control_blocks" / "repair_transactions" / "repair_transaction_index.json")
    control_transaction_registry = _read_json(
        root / "skills" / "flowpilot" / "assets" / "runtime_kit" / "control_transaction_registry.json"
    )

    parse_errors = [
        name
        for name, data in {
            "execution_frontier": frontier,
            "packet_ledger": packet_ledger,
            "current_status_summary": status_summary,
            "repair_transaction_index": repair_index,
            "control_transaction_registry": control_transaction_registry,
        }.items()
        if isinstance(data, Mapping) and "__parse_error__" in data
    ]

    status_reports_blocked = _dict_get(status_summary, ["state_kind"]) in {
        "blocked",
        "protocol_blocked",
        "needs_repair",
    }
    active_blocker = bool(
        _dict_get(status_summary, ["current_blocker", "active"], False)
        or _dict_get(status_summary, ["blocker", "active"], False)
        or status_reports_blocked
    )
    collapsed_repair = _collapsed_repair_events(repair_index)
    parent_leaf_event = _parent_repair_uses_leaf_event(repair_index, frontier)
    packet_authority_unchecked = _packet_authority_unchecked(packet_ledger)
    authorities_agree = _authorities_agree(frontier, packet_ledger, status_summary)
    control_registry_registered = isinstance(control_transaction_registry, Mapping)
    control_registry_rows = (
        control_transaction_registry.get("transaction_types")
        if isinstance(control_transaction_registry, Mapping)
        else None
    )
    control_registry_valid = (
        isinstance(control_transaction_registry, Mapping)
        and control_transaction_registry.get("schema_version") == "flowpilot.control_transaction_registry.v1"
        and control_transaction_registry.get("authority") == "router"
        and control_transaction_registry.get("controller_may_invent_transactions") is False
        and isinstance(control_registry_rows, list)
        and bool(control_registry_rows)
    )
    control_commit_scope_complete = bool(
        control_registry_valid
        and all(
            isinstance(row, Mapping)
            and row.get("transaction_type")
            and isinstance(row.get("commit_targets"), list)
            and bool(row.get("commit_targets"))
            for row in control_registry_rows
        )
    )

    blocking_reasons = list(reasons)
    if parse_errors:
        blocking_reasons.append("metadata_parse_errors:" + ",".join(sorted(parse_errors)))
    if active_blocker:
        blocking_reasons.append("active_blocker_present")
    if collapsed_repair:
        blocking_reasons.append("repair_outcome_events_collapsed")
    if parent_leaf_event:
        blocking_reasons.append("parent_repair_reuses_leaf_event")
    if packet_authority_unchecked:
        blocking_reasons.append("packet_authority_unchecked")
    if not authorities_agree:
        blocking_reasons.append("current_authorities_disagree")
    if not control_registry_registered:
        blocking_reasons.append("control_transaction_registry_missing")
    elif not control_registry_valid:
        blocking_reasons.append("control_transaction_registry_invalid")
    elif not control_commit_scope_complete:
        blocking_reasons.append("control_transaction_commit_scope_incomplete")

    if parse_errors:
        decision = "model_coverage_insufficient"
    elif (
        collapsed_repair
        or parent_leaf_event
        or packet_authority_unchecked
        or not authorities_agree
        or not control_registry_registered
        or not control_registry_valid
        or not control_commit_scope_complete
    ):
        decision = "blocked_by_cross_model_contradiction"
    elif active_blocker:
        decision = "blocked_by_live_evidence"
    else:
        decision = "mesh_green_can_continue"

    state = State(
        scenario="live_run_projection",
        status="selected",
        decision=decision,
        model_registered=True,
        model_result_ok=True,
        model_result_run_matches_current=True,
        model_result_fresh=True,
        evidence_tier="live_current_green",
        required_tier="live_current_green",
        live_required=True,
        live_audit_skipped=False,
        current_state_classified=True,
        active_blocker_present=active_blocker,
        safe_to_continue_claimed=decision == "mesh_green_can_continue",
        current_authorities_agree=authorities_agree,
        status_summary_reports_blocked=status_reports_blocked,
        collapsed_repair_outcome_events=collapsed_repair,
        repair_event_node_compatible=not parent_leaf_event,
        parent_repair_reuses_leaf_event=parent_leaf_event,
        role_origin_checked=not packet_authority_unchecked,
        completed_agent_id_belongs_to_role=not packet_authority_unchecked,
        packet_evidence_accepted=packet_authority_unchecked,
        known_hazard_live_projection_available=True,
        sealed_body_opened_by_mesh=False,
        coverage_parse_errors_ignored=False,
        install_requires_safe_to_continue=False,
        installed_skill_matches_repo=True,
        local_sync_required=False,
        control_transaction_registry_registered=control_registry_registered,
        control_transaction_registry_valid=control_registry_valid,
        control_transaction_commit_scope_complete=control_commit_scope_complete,
    )

    projected_failures = mesh_failures(state)
    classification_ok = not projected_failures
    current_run_can_continue = classification_ok and decision == "mesh_green_can_continue"
    sorted_blocking_reasons = sorted(set(blocking_reasons))
    findings = _live_projection_findings(
        run_id=resolved_run_id,
        decision=decision,
        current_run_can_continue=current_run_can_continue,
        blocking_reasons=sorted_blocking_reasons,
        projected_failures=projected_failures,
    )
    return {
        "ok": classification_ok,
        "classification_ok": classification_ok,
        "current_run_can_continue": current_run_can_continue,
        "permission": "can_continue" if current_run_can_continue else "blocked_or_insufficient",
        "run_id": resolved_run_id,
        "run_root": str(run_root),
        "decision": decision,
        "blocking_reasons": sorted_blocking_reasons,
        "findings": findings,
        "metadata_only": True,
        "sealed_body_opened_by_mesh": False,
        "projected_state": state.__dict__,
        "projected_failures": projected_failures,
    }


__all__ = [
    "BLOCKING_DECISIONS",
    "EVIDENCE_ORDER",
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEGATIVE_SCENARIOS",
    "SAFE_DECISIONS",
    "SCENARIOS",
    "Action",
    "State",
    "Tick",
    "Transition",
    "VALID_SCENARIOS",
    "build_workflow",
    "expected_failures_by_hazard",
    "hazard_states",
    "initial_state",
    "input_alphabet",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "mesh_failures",
    "next_safe_states",
    "project_live_run",
    "terminal_predicate",
]
