"""FlowGuard model for FlowPilot external-event idempotency.

Risk intent brief:
- Prevent global boolean flags from swallowing a later legitimate occurrence of
  the same external event when the later occurrence belongs to a different
  control blocker, repair transaction, route version, gate, node cycle, or
  retry attempt.
- Preserve true idempotency: replaying the same event identity must not create
  duplicate side effects.
- Model-critical state: event family, dedupe key, processed-key ledger, route
  version, repair transaction, retry attempt budget, reset-dependent cycle
  state, and terminal router decision.
- Adversarial branches include a second route mutation under a new repair
  transaction, same-key replay, unconditional repeatable gate decisions,
  repeated repair attempts below and above budget, and cycle-scoped events that
  rely on reset flags.
- Hard invariants: scoped events dedupe by identity, not by event name; same-key
  replay is idempotent; different-key repair attempts remain routable until a
  visible retry budget is exhausted; exceeded retry budgets escalate explicitly
  instead of being silently swallowed; reset-dependent events require an
  explicit cycle reset before a new generation can reuse the event name.
- Blindspot: this model does not judge PM/reviewer semantic quality. It models
  router control-plane idempotency and retry shape only.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


ONE_SHOT_REPLAY = "one_shot_same_key_replay"
ONE_SHOT_NEW_CONTEXT = "one_shot_new_context_rejected"
ROUTE_MUTATION_SAME_TX_REPLAY = "route_mutation_same_transaction_replay"
ROUTE_MUTATION_NEW_TX = "route_mutation_new_transaction"
CONTROL_REPAIR_NEW_TX = "control_repair_new_transaction"
GATE_DECISION_SAME_KEY_REPLAY = "gate_decision_same_key_replay"
GATE_DECISION_NEW_KEY = "gate_decision_new_key"
REPAIR_RETRY_BELOW_BUDGET = "repair_retry_below_budget"
REPAIR_RETRY_EXCEEDS_BUDGET = "repair_retry_exceeds_budget"
CYCLE_EVENT_AFTER_RESET = "cycle_scoped_event_after_reset"
CYCLE_EVENT_WITHOUT_RESET = "cycle_scoped_event_without_reset"
LIFECYCLE_REPLAY = "lifecycle_replay"
PACKAGE_DISPOSITION_SAME_BODY_REPLAY = "package_disposition_same_body_replay"
PACKAGE_DISPOSITION_DIFFERENT_BODY_CONFLICT = "package_disposition_different_body_conflict"
PACKAGE_DISPOSITION_CONTROL_BLOCKER_OWNED_CONFLICT = "package_disposition_control_blocker_owned_conflict_replay"
PACKAGE_DISPOSITION_PM_REPAIR_OWNED_CONFLICT = "package_disposition_pm_repair_owned_conflict_replay"
PACKAGE_DISPOSITION_STALE_UNOWNED_CONFLICT = "package_disposition_stale_unowned_conflict_replay"
PACKAGE_DISPOSITION_NEW_GENERATION = "package_disposition_new_generation"

SCENARIOS = (
    ONE_SHOT_REPLAY,
    ONE_SHOT_NEW_CONTEXT,
    ROUTE_MUTATION_SAME_TX_REPLAY,
    ROUTE_MUTATION_NEW_TX,
    CONTROL_REPAIR_NEW_TX,
    GATE_DECISION_SAME_KEY_REPLAY,
    GATE_DECISION_NEW_KEY,
    REPAIR_RETRY_BELOW_BUDGET,
    REPAIR_RETRY_EXCEEDS_BUDGET,
    CYCLE_EVENT_AFTER_RESET,
    CYCLE_EVENT_WITHOUT_RESET,
    LIFECYCLE_REPLAY,
    PACKAGE_DISPOSITION_SAME_BODY_REPLAY,
    PACKAGE_DISPOSITION_DIFFERENT_BODY_CONFLICT,
    PACKAGE_DISPOSITION_CONTROL_BLOCKER_OWNED_CONFLICT,
    PACKAGE_DISPOSITION_PM_REPAIR_OWNED_CONFLICT,
    PACKAGE_DISPOSITION_STALE_UNOWNED_CONFLICT,
    PACKAGE_DISPOSITION_NEW_GENERATION,
)

ACCEPTED_SCENARIOS = {
    ROUTE_MUTATION_NEW_TX,
    CONTROL_REPAIR_NEW_TX,
    GATE_DECISION_NEW_KEY,
    REPAIR_RETRY_BELOW_BUDGET,
    CYCLE_EVENT_AFTER_RESET,
    PACKAGE_DISPOSITION_NEW_GENERATION,
}

IDEMPOTENT_SCENARIOS = {
    ONE_SHOT_REPLAY,
    ROUTE_MUTATION_SAME_TX_REPLAY,
    GATE_DECISION_SAME_KEY_REPLAY,
    CYCLE_EVENT_WITHOUT_RESET,
    LIFECYCLE_REPLAY,
    PACKAGE_DISPOSITION_SAME_BODY_REPLAY,
}

ESCALATED_SCENARIOS = {
    ONE_SHOT_NEW_CONTEXT,
    REPAIR_RETRY_EXCEEDS_BUDGET,
    PACKAGE_DISPOSITION_DIFFERENT_BODY_CONFLICT,
}

REPAIR_OWNED_SCENARIOS = {
    PACKAGE_DISPOSITION_CONTROL_BLOCKER_OWNED_CONFLICT,
    PACKAGE_DISPOSITION_PM_REPAIR_OWNED_CONFLICT,
}

STALE_QUARANTINED_SCENARIOS = {
    PACKAGE_DISPOSITION_STALE_UNOWNED_CONFLICT,
}


@dataclass(frozen=True)
class Tick:
    """One external-event idempotency transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | already_recorded | escalated | repair_owned | stale_quarantined
    scenario: str = "unset"
    event_name: str = ""
    family: str = "unset"  # one_shot | transaction | gate | cycle | lifecycle

    flag_already_true: bool = False
    prior_keys: tuple[str, ...] = ()
    incoming_key: str = ""
    key_fields_present: bool = True
    key_matches_prior: bool = False
    conflict_fields_present: bool = True
    conflict_matches_prior: bool = True
    replay_source: str = "direct"  # direct | role_output_ledger | daemon_tick
    canonical_package_authority_available: bool = False
    canonical_body_preserved: bool = True
    repair_owner: str = "none"  # none | control_blocker | pm_repair_transaction | terminal_quarantine
    legal_wait_preserved: bool = True
    daemon_crashed: bool = False
    stale_conflict_accepted_as_success: bool = False
    duplicate_blocker_created: bool = False

    cycle_reset_recorded: bool = False
    route_version_advances: bool = False
    repair_transaction_advances: bool = False
    active_blocker_advances: bool = False
    retry_attempt: int = 0
    retry_budget: int = 2

    side_effect_written: bool = False
    duplicate_side_effect_written: bool = False
    explicit_escalation_written: bool = False
    no_legal_next_action: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class EventIdempotencyStep:
    """Model one router external-event dedupe decision.

    Input x State -> Set(Output x State)
    reads: event name, event family, prior processed identity keys, retry budget,
    and reset-cycle evidence.
    writes: accepted side effect, already-recorded idempotency result, explicit
    escalation, or no-legal-next-action hazard.
    idempotency: same event identity replays do not write duplicate side
    effects; different event identities are not swallowed by the old global
    event flag.
    """

    name = "EventIdempotencyStep"
    reads = ("event_name", "event_family", "dedupe_key", "processed_key_ledger", "retry_budget", "cycle_reset")
    writes = ("router_event_decision",)
    input_description = "one external event returned to router"
    output_description = "dedupe/accept/escalate decision"
    idempotency = "same dedupe key replays are idempotent; new keys are handled as new events"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(output=Action(transition.label), new_state=transition.state, label=transition.label)


def initial_state() -> State:
    return State()


def _selected_state(scenario: str) -> State:
    if scenario == ONE_SHOT_REPLAY:
        return State(
            status="running",
            scenario=scenario,
            event_name="reviewer_reports_startup_facts",
            family="one_shot",
            flag_already_true=True,
            prior_keys=("startup-review:run-1",),
            incoming_key="startup-review:run-1",
            key_matches_prior=True,
        )
    if scenario == ONE_SHOT_NEW_CONTEXT:
        return State(
            status="running",
            scenario=scenario,
            event_name="reviewer_reports_startup_facts",
            family="one_shot",
            flag_already_true=True,
            prior_keys=("startup-review:run-1",),
            incoming_key="startup-review:unexpected-run-2",
            terminal_reason="one_shot_requires_new_run_or_protocol_reset",
        )
    if scenario == ROUTE_MUTATION_SAME_TX_REPLAY:
        return State(
            status="running",
            scenario=scenario,
            event_name="pm_mutates_route_after_review_block",
            family="transaction",
            flag_already_true=True,
            prior_keys=("repair-tx-1:route-v2",),
            incoming_key="repair-tx-1:route-v2",
            key_matches_prior=True,
            retry_attempt=1,
        )
    if scenario == ROUTE_MUTATION_NEW_TX:
        return State(
            status="running",
            scenario=scenario,
            event_name="pm_mutates_route_after_review_block",
            family="transaction",
            flag_already_true=True,
            prior_keys=("repair-tx-1:route-v2",),
            incoming_key="repair-tx-2:route-v3",
            repair_transaction_advances=True,
            route_version_advances=True,
            retry_attempt=2,
        )
    if scenario == CONTROL_REPAIR_NEW_TX:
        return State(
            status="running",
            scenario=scenario,
            event_name="pm_records_control_blocker_repair_decision",
            family="transaction",
            flag_already_true=True,
            prior_keys=("control-blocker-1:repair-tx-1",),
            incoming_key="control-blocker-2:repair-tx-2",
            active_blocker_advances=True,
            repair_transaction_advances=True,
            retry_attempt=1,
        )
    if scenario == GATE_DECISION_SAME_KEY_REPLAY:
        return State(
            status="running",
            scenario=scenario,
            event_name="role_records_gate_decision",
            family="gate",
            flag_already_true=True,
            prior_keys=("gate:route-check:v1:process_officer",),
            incoming_key="gate:route-check:v1:process_officer",
            key_matches_prior=True,
        )
    if scenario == GATE_DECISION_NEW_KEY:
        return State(
            status="running",
            scenario=scenario,
            event_name="role_records_gate_decision",
            family="gate",
            flag_already_true=True,
            prior_keys=("gate:route-check:v1:process_officer",),
            incoming_key="gate:route-check:v2:process_officer",
            route_version_advances=True,
        )
    if scenario == REPAIR_RETRY_BELOW_BUDGET:
        return State(
            status="running",
            scenario=scenario,
            event_name="pm_mutates_route_after_review_block",
            family="transaction",
            flag_already_true=True,
            prior_keys=("repair-tx-1:route-v2",),
            incoming_key="repair-tx-2:route-v3",
            repair_transaction_advances=True,
            route_version_advances=True,
            retry_attempt=2,
            retry_budget=3,
        )
    if scenario == REPAIR_RETRY_EXCEEDS_BUDGET:
        return State(
            status="running",
            scenario=scenario,
            event_name="pm_mutates_route_after_review_block",
            family="transaction",
            flag_already_true=True,
            prior_keys=("repair-tx-1:route-v2", "repair-tx-2:route-v3", "repair-tx-3:route-v4"),
            incoming_key="repair-tx-4:route-v5",
            repair_transaction_advances=True,
            route_version_advances=True,
            retry_attempt=4,
            retry_budget=3,
        )
    if scenario == CYCLE_EVENT_AFTER_RESET:
        return State(
            status="running",
            scenario=scenario,
            event_name="pm_registers_current_node_packet",
            family="cycle",
            flag_already_true=True,
            prior_keys=("node-001:packet-generation-1",),
            incoming_key="node-001-repair:packet-generation-2",
            cycle_reset_recorded=True,
            route_version_advances=True,
        )
    if scenario == CYCLE_EVENT_WITHOUT_RESET:
        return State(
            status="running",
            scenario=scenario,
            event_name="pm_registers_current_node_packet",
            family="cycle",
            flag_already_true=True,
            prior_keys=("node-001:packet-generation-1",),
            incoming_key="node-001:packet-generation-1",
            key_matches_prior=True,
        )
    if scenario == LIFECYCLE_REPLAY:
        return State(
            status="running",
            scenario=scenario,
            event_name="user_requests_run_stop",
            family="lifecycle",
            flag_already_true=True,
            prior_keys=("run-1:stop",),
            incoming_key="run-1:stop",
            key_matches_prior=True,
        )
    if scenario == PACKAGE_DISPOSITION_SAME_BODY_REPLAY:
        return State(
            status="running",
            scenario=scenario,
            event_name="pm_records_material_scan_result_disposition",
            family="package",
            flag_already_true=True,
            prior_keys=("material-batch-1:gen-1:packet-a,packet-b",),
            incoming_key="material-batch-1:gen-1:packet-a,packet-b",
            key_matches_prior=True,
            conflict_matches_prior=True,
        )
    if scenario == PACKAGE_DISPOSITION_DIFFERENT_BODY_CONFLICT:
        return State(
            status="running",
            scenario=scenario,
            event_name="pm_records_material_scan_result_disposition",
            family="package",
            flag_already_true=True,
            prior_keys=("material-batch-1:gen-1:packet-a,packet-b",),
            incoming_key="material-batch-1:gen-1:packet-a,packet-b",
            key_matches_prior=True,
            conflict_fields_present=True,
            conflict_matches_prior=False,
            terminal_reason="same_package_identity_different_body_hash",
        )
    if scenario == PACKAGE_DISPOSITION_CONTROL_BLOCKER_OWNED_CONFLICT:
        return State(
            status="running",
            scenario=scenario,
            event_name="pm_records_material_scan_result_disposition",
            family="package",
            flag_already_true=True,
            prior_keys=("material-batch-1:gen-1:packet-a,packet-b",),
            incoming_key="material-batch-1:gen-1:packet-a,packet-b",
            key_matches_prior=True,
            conflict_fields_present=True,
            conflict_matches_prior=False,
            repair_owner="control_blocker",
            terminal_reason="same_package_identity_different_body_hash_control_blocker_owned",
        )
    if scenario == PACKAGE_DISPOSITION_PM_REPAIR_OWNED_CONFLICT:
        return State(
            status="running",
            scenario=scenario,
            event_name="pm_records_material_scan_result_disposition",
            family="package",
            flag_already_true=True,
            prior_keys=("material-batch-1:gen-1:packet-a,packet-b",),
            incoming_key="material-batch-1:gen-1:packet-a,packet-b",
            key_matches_prior=True,
            conflict_fields_present=True,
            conflict_matches_prior=False,
            repair_owner="pm_repair_transaction",
            terminal_reason="same_package_identity_different_body_hash_pm_repair_owned",
        )
    if scenario == PACKAGE_DISPOSITION_STALE_UNOWNED_CONFLICT:
        return State(
            status="running",
            scenario=scenario,
            event_name="pm_records_material_scan_result_disposition",
            family="package",
            flag_already_true=False,
            prior_keys=("material-batch-1:gen-1:packet-a,packet-b",),
            incoming_key="material-batch-1:gen-1:packet-a,packet-b",
            key_matches_prior=True,
            conflict_fields_present=True,
            conflict_matches_prior=False,
            replay_source="role_output_ledger",
            canonical_package_authority_available=True,
            terminal_reason="same_package_identity_different_body_hash_canonical_authority_owned",
        )
    if scenario == PACKAGE_DISPOSITION_NEW_GENERATION:
        return State(
            status="running",
            scenario=scenario,
            event_name="pm_records_material_scan_result_disposition",
            family="package",
            flag_already_true=True,
            prior_keys=("material-batch-1:gen-1:packet-a,packet-b",),
            incoming_key="material-batch-2:gen-2:packet-c,packet-d",
            cycle_reset_recorded=True,
            route_version_advances=True,
        )
    raise ValueError(f"unknown scenario: {scenario}")


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _selected_state(scenario))
        return
    if state.status != "running":
        return
    if state.family == "one_shot" and state.flag_already_true and not state.key_matches_prior:
        yield Transition("router_rejects_one_shot_new_context_without_reset", replace(state, status="escalated", explicit_escalation_written=True))
        return
    if state.family == "transaction" and state.retry_attempt > state.retry_budget:
        yield Transition("router_escalates_after_retry_budget", replace(state, status="escalated", explicit_escalation_written=True))
        return
    if state.family == "cycle" and state.flag_already_true and not state.cycle_reset_recorded:
        yield Transition("router_returns_already_recorded_for_same_cycle_replay", replace(state, status="already_recorded", terminal_reason="same_cycle_replay"))
        return
    if (
        state.family == "package"
        and (state.key_matches_prior or state.incoming_key in state.prior_keys)
        and not state.conflict_matches_prior
        and state.repair_owner in {"control_blocker", "pm_repair_transaction", "terminal_quarantine"}
    ):
        label = f"router_skips_{state.repair_owner}_owned_package_conflict_replay"
        yield Transition(label, replace(state, status="repair_owned", side_effect_written=False, legal_wait_preserved=True))
        return
    if (
        state.family == "package"
        and (state.key_matches_prior or state.incoming_key in state.prior_keys)
        and not state.conflict_matches_prior
        and state.replay_source in {"role_output_ledger", "daemon_tick"}
        and state.canonical_package_authority_available
    ):
        yield Transition(
            "router_quarantines_canonical_package_authority_stale_conflict",
            replace(
                state,
                status="stale_quarantined",
                side_effect_written=False,
                legal_wait_preserved=True,
                canonical_body_preserved=True,
            ),
        )
        return
    if state.family == "package" and (state.key_matches_prior or state.incoming_key in state.prior_keys) and not state.conflict_matches_prior:
        yield Transition("router_rejects_same_package_different_body_hash", replace(state, status="escalated", explicit_escalation_written=True))
        return
    if state.key_matches_prior or state.incoming_key in state.prior_keys:
        yield Transition("router_returns_already_recorded_for_same_dedupe_key", replace(state, status="already_recorded", terminal_reason="same_dedupe_key"))
        return
    yield Transition("router_accepts_new_scoped_event_identity", replace(state, status="accepted", side_effect_written=True, terminal_reason="new_dedupe_key"))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "already_recorded", "escalated", "repair_owned", "stale_quarantined"}


def is_success(state: State) -> bool:
    return is_terminal(state)


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return is_terminal(state)


def _hard_check_failures(state: State) -> list[str]:
    failures: list[str] = []
    scoped_family = state.family in {"transaction", "gate", "cycle", "package"}
    new_key = bool(state.incoming_key and state.incoming_key not in state.prior_keys)
    same_key = bool(state.incoming_key and state.incoming_key in state.prior_keys)
    if state.status == "accepted" and same_key:
        failures.append("same dedupe key wrote duplicate side effect")
    if state.duplicate_side_effect_written:
        failures.append("duplicate side effect written for replayed event identity")
    if scoped_family and state.status == "already_recorded" and new_key and not (
        state.family == "cycle" and not state.cycle_reset_recorded
    ):
        failures.append("new scoped event identity was swallowed by global event flag")
    if state.family == "transaction" and state.retry_attempt <= state.retry_budget and state.status == "already_recorded" and new_key:
        failures.append("repair retry below budget was silently swallowed")
    if (
        state.status in {"accepted", "already_recorded", "escalated"}
        and state.family == "transaction"
        and state.retry_attempt > state.retry_budget
        and not state.explicit_escalation_written
    ):
        failures.append("repair retry budget exceeded without explicit PM escalation")
    if state.family == "cycle" and state.status == "accepted" and state.flag_already_true and not state.cycle_reset_recorded:
        failures.append("cycle-scoped event reused without reset evidence")
    if state.no_legal_next_action:
        failures.append("idempotency decision produced no legal next action")
    if state.status == "accepted" and scoped_family and not state.key_fields_present:
        failures.append("accepted scoped event without dedupe key fields")
    if state.family == "package" and state.status == "already_recorded" and not state.conflict_matches_prior:
        failures.append("conflicting package disposition body was treated as idempotent replay")
    if state.family == "package" and state.status == "repair_owned":
        if state.repair_owner not in {"control_blocker", "pm_repair_transaction", "terminal_quarantine"}:
            failures.append("repair-owned package conflict lacked an owning control-plane authority")
        if state.side_effect_written or state.stale_conflict_accepted_as_success:
            failures.append("repair-owned package conflict was accepted as successful disposition")
        if not state.legal_wait_preserved:
            failures.append("repair-owned package conflict replay did not preserve the legal wait")
        if state.daemon_crashed:
            failures.append("repair-owned package conflict replay crashed the daemon")
        if state.duplicate_blocker_created:
            failures.append("repair-owned package conflict replay created a duplicate blocker")
    if state.family == "package" and state.status == "stale_quarantined":
        if not state.canonical_package_authority_available:
            failures.append("stale unowned package conflict lacked canonical package authority")
        if state.side_effect_written or state.stale_conflict_accepted_as_success:
            failures.append("stale unowned package conflict was accepted as successful disposition")
        if not state.canonical_body_preserved:
            failures.append("stale unowned package conflict replay did not preserve canonical body")
        if state.daemon_crashed:
            failures.append("stale unowned package conflict replay crashed the daemon")
    if state.family == "package" and state.status == "accepted" and same_key:
        failures.append("same package disposition identity wrote duplicate side effect")
    if state.family == "package" and not state.conflict_fields_present:
        failures.append("package disposition identity lacked body_hash conflict field")
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
        "flowpilot_event_idempotency_contract",
        "External events must dedupe by scoped identity while preserving same-key replay idempotency.",
        hard_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


def build_workflow() -> Workflow:
    return Workflow((EventIdempotencyStep(),), name="flowpilot_event_idempotency")


def hazard_states() -> dict[str, State]:
    route_new = _selected_state(ROUTE_MUTATION_NEW_TX)
    gate_same = _selected_state(GATE_DECISION_SAME_KEY_REPLAY)
    retry_below = _selected_state(REPAIR_RETRY_BELOW_BUDGET)
    retry_exceeded = _selected_state(REPAIR_RETRY_EXCEEDS_BUDGET)
    cycle_new = _selected_state(CYCLE_EVENT_AFTER_RESET)
    package_conflict = _selected_state(PACKAGE_DISPOSITION_DIFFERENT_BODY_CONFLICT)
    package_same = _selected_state(PACKAGE_DISPOSITION_SAME_BODY_REPLAY)
    stale_unowned = _selected_state(PACKAGE_DISPOSITION_STALE_UNOWNED_CONFLICT)
    return {
        "global_flag_swallows_new_route_mutation": replace(
            route_new,
            status="already_recorded",
            side_effect_written=False,
            terminal_reason="global_flag_already_true",
        ),
        "unconditional_repeat_duplicates_gate_decision": replace(
            gate_same,
            status="accepted",
            side_effect_written=True,
            duplicate_side_effect_written=True,
            terminal_reason="unconditional_repeat",
        ),
        "repair_retry_below_budget_swallowed": replace(
            retry_below,
            status="already_recorded",
            side_effect_written=False,
            terminal_reason="global_flag_already_true",
        ),
        "retry_budget_exceeded_without_escalation": replace(
            retry_exceeded,
            status="already_recorded",
            explicit_escalation_written=False,
            terminal_reason="global_flag_already_true",
        ),
        "cycle_reuse_without_reset": replace(
            cycle_new,
            status="accepted",
            cycle_reset_recorded=False,
            side_effect_written=True,
            terminal_reason="missing_cycle_reset",
        ),
        "accepted_without_dedupe_key_fields": replace(
            route_new,
            status="accepted",
            key_fields_present=False,
            side_effect_written=True,
            terminal_reason="missing_key_fields",
        ),
        "no_legal_next_action_after_swallow": replace(
            route_new,
            status="already_recorded",
            side_effect_written=False,
            no_legal_next_action=True,
            terminal_reason="swallowed_then_stuck",
        ),
        "package_conflict_swallowed_as_replay": replace(
            package_conflict,
            status="already_recorded",
            explicit_escalation_written=False,
            terminal_reason="same_key_replay_without_conflict_check",
        ),
        "package_body_hash_left_in_dedupe_key": replace(
            package_same,
            status="accepted",
            key_matches_prior=True,
            side_effect_written=True,
            duplicate_side_effect_written=True,
            terminal_reason="body_hash_created_new_dedupe_key",
        ),
        "repair_owned_package_conflict_accepted_as_success": replace(
            _selected_state(PACKAGE_DISPOSITION_CONTROL_BLOCKER_OWNED_CONFLICT),
            status="repair_owned",
            side_effect_written=True,
            stale_conflict_accepted_as_success=True,
            terminal_reason="accepted_stale_replay",
        ),
        "repair_owned_package_conflict_crashed_daemon": replace(
            _selected_state(PACKAGE_DISPOSITION_PM_REPAIR_OWNED_CONFLICT),
            status="repair_owned",
            daemon_crashed=True,
            legal_wait_preserved=False,
            terminal_reason="daemon_error",
        ),
        "stale_unowned_package_conflict_accepted_as_success": replace(
            stale_unowned,
            status="stale_quarantined",
            side_effect_written=True,
            stale_conflict_accepted_as_success=True,
            terminal_reason="accepted_stale_unowned_replay",
        ),
        "stale_unowned_package_conflict_crashed_daemon": replace(
            stale_unowned,
            status="stale_quarantined",
            daemon_crashed=True,
            terminal_reason="daemon_error",
        ),
        "stale_unowned_package_conflict_reverted_canonical_body": replace(
            stale_unowned,
            status="stale_quarantined",
            canonical_body_preserved=False,
            terminal_reason="canonical_body_reverted_to_stale_replay",
        ),
        "package_conflict_field_missing": replace(
            package_same,
            status="accepted",
            conflict_fields_present=False,
            terminal_reason="no_conflict_field",
        ),
    }
