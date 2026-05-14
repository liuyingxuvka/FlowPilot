"""FlowGuard model for FlowPilot card envelopes and return-event gates.

Risk intent brief:
- Prevent system-card delivery from being mistaken for target-role reading or
  target-role completion.
- Protect the Controller boundary by requiring envelope-only relay and
  runtime-created card receipts plus role-authored direct Router ACK/report
  envelopes before Router advancement.
- Model-critical durable state: role I/O protocol acknowledgement for the
  current resume tick, card envelope identity, card manifest hash, target role
  and agent identity, read receipt timing, expected card-return event records,
  explicit runtime check-in instructions, direct Router ack/report envelope
  identity,
  same-role system-card bundle eligibility, batch dependency graph, cross-role
  parallel delivery joins, and legacy prompt-delivery compatibility.
- Adversarial branches include legacy delivery treated as read, missing read
  receipt, missing ack/report envelope, ack/report without receipt references,
  wrong role, old run, old agent after replacement, hash mismatch, receipt
  before delivery, missing runtime check-in instructions, hand-written ACKs,
  stale prompts that still teach Controller ACK handling, missing direct Router
  ACK instructions in role cards or packet templates,
  Controller relaying a pre-apply planned artifact path as if it were a
  committed envelope, public Controller apply of a relay-only system-card
  action, missing resume I/O acknowledgement, preload-only authorization,
  bundle receipt replacing per-card receipts, same-role bundle crossing
  run/role/agent/resume boundaries, unsafe bundle dependencies, hidden
  dependency parallelization, Controller body reads, Controller batch mutation,
  gate or node movement before current-scope ACK clearance, formal work-packet
  relay before the target role clears required system cards, duplicate system
  card delivery for a merely missing ACK, ACKs being treated as target-role
  work completion, and dead-end waiting after an interruption.
- Hard invariants: Controller never reads card bodies; Router advancement
  requires current-run/current-role/current-agent/current-hash runtime receipts
  referenced by a current direct Router ack/report envelope; same-role card bundles are
  allowed only when every member card keeps manifest/hash/delivery/receipt
  evidence and the bundle does not hide an external boundary; cross-role
  parallel delivery is allowed only with Router-authored dependency and join
  metadata; role I/O protocol acknowledgement is required after
  heartbeat/manual resume or replacement; gate/node movement and formal
  work-packet relay wait for scoped/target-role ACK clearance; a missing ACK
  reminds the role to complete the original card or bundle ACK loop unless the
  original artifact is invalid, stale, lost, or tied to a replaced identity;
  read receipts and ACKs are mechanical proof only and never replace
  PM/reviewer/officer judgement or worker result completion.
- Blindspot: this is a focused protocol model. It does not judge whether a
  role understood a card after opening it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class Tick:
    """One card-envelope protocol transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | passed
    steps: int = 0

    legacy_prompt_delivery_recorded: bool = False
    legacy_delivery_treated_as_read: bool = False

    resume_tick_active: bool = False
    role_replacement_active: bool = False
    role_io_protocol_injected: bool = False
    role_io_ack_current_tick: bool = False
    role_io_ack_current_agent: bool = False

    internal_delivery_action_exposed: bool = False
    planned_artifact_paths_exposed: bool = False
    planned_action_relay_allowed: bool = False
    router_auto_committed_internal_action: bool = False
    committed_artifact_exists: bool = False
    committed_artifact_hash_verified: bool = False
    post_apply_envelope_issued: bool = False
    controller_relayed_preapply_artifact: bool = False
    runtime_open_blocked_not_committed: bool = False
    public_system_card_apply_used: bool = False

    card_envelope_issued: bool = False
    card_delivery_recorded: bool = False
    card_hash_matches_manifest: bool = False
    card_return_event_declared: bool = False
    checkin_instruction_declared: bool = False
    checkin_tool_command_declared: bool = False
    card_ack_token_declared: bool = False
    direct_router_ack_instruction_declared: bool = False
    startup_card_before_frontier: bool = False
    direct_ack_token_frontier_optional_when_missing: bool = False
    direct_ack_token_requires_frontier_before_available: bool = False
    legacy_return_event_field_used: bool = False
    expected_return_path_recorded: bool = False
    pending_return_recorded: bool = False
    controller_relayed_card_envelope: bool = False
    controller_envelope_only: bool = False
    controller_read_card_body: bool = False
    controller_mutated_batch: bool = False
    controller_skipped_envelope: bool = False

    card_read_receipt_written: bool = False
    receipt_current_run: bool = False
    receipt_current_role: bool = False
    receipt_current_agent: bool = False
    receipt_hash_matches_manifest: bool = False
    receipt_after_delivery: bool = False
    receipt_after_role_io_ack: bool = False
    role_used_checkin_runtime: bool = False

    required_card_declared: bool = False
    required_card_coverage_checked: bool = False
    required_card_coverage_passed: bool = False
    missing_required_receipt_detected: bool = False
    await_required_receipts: bool = False
    expected_return_missing_detected: bool = False
    await_expected_return: bool = False
    return_reminder_issued: bool = False
    ack_clearance_scope_recorded: bool = False
    gate_boundary_transition_requested: bool = False
    gate_boundary_ack_clearance_checked: bool = False
    gate_boundary_ack_clearance_passed: bool = False
    formal_work_packet_requested: bool = False
    formal_work_packet_ack_clearance_checked: bool = False
    formal_work_packet_ack_clearance_passed: bool = False
    formal_work_packet_relayed: bool = False
    missing_ack_reminder_reuses_original_envelope: bool = False
    duplicate_system_card_reissued_for_missing_ack: bool = False
    ack_report_returned: bool = False
    ack_current_run: bool = False
    ack_current_role: bool = False
    ack_current_agent: bool = False
    ack_references_read_receipts: bool = False
    ack_returned_after_receipts: bool = False
    ack_body_empty: bool = False
    ack_direct_to_router: bool = False
    ack_router_token_valid: bool = False
    ack_no_controller_handoff: bool = False
    handwritten_ack_attempted: bool = False
    card_ack_sent_to_external_event_entrypoint: bool = False
    card_ack_external_event_auto_rerouted: bool = False
    card_ack_external_event_rejected: bool = False
    card_ack_recorded_as_external_event: bool = False
    check_card_return_apply_required: bool = False
    receipt_repair_request_issued: bool = False
    redelivery_attempt_issued: bool = False
    stale_delivery_superseded: bool = False

    bundle_receipt_used: bool = False
    per_card_receipts_referenced: bool = False

    same_role_bundle_used: bool = False
    same_role_bundle_same_run_role_agent_tick: bool = False
    same_role_bundle_manifest_batch_checked: bool = False
    same_role_bundle_dependencies_safe: bool = False
    same_role_bundle_no_external_boundary_hidden: bool = False
    same_role_bundle_member_delivery_records_kept: bool = False
    same_role_bundle_member_return_events_declared: bool = False
    same_role_bundle_pending_return_recorded: bool = False
    same_role_bundle_incomplete_ack_detected: bool = False
    same_role_bundle_missing_receipts_listed: bool = False
    same_role_bundle_pending_kept_after_incomplete: bool = False
    same_role_bundle_recovery_wait_returned: bool = False
    same_role_bundle_recovered_after_complete_ack: bool = False
    same_role_bundle_per_card_receipts_joined: bool = False
    same_role_bundle_ack_joined: bool = False
    same_role_bundle_check_apply_required: bool = False

    cross_role_batch_used: bool = False
    batch_dependency_graph_declared: bool = False
    batch_join_policy_declared: bool = False
    batch_card_return_events_declared: bool = False
    independent_parallel_delivery: bool = False
    hidden_dependency_parallelized: bool = False
    all_required_batch_receipts_joined: bool = False
    all_required_batch_ack_reports_joined: bool = False
    missing_batch_join_detected: bool = False
    awaiting_batch_join_receipts: bool = False
    awaiting_batch_card_return_events: bool = False
    preload_only_receipt_used_as_authorization: bool = False

    prompt_ack_coverage_checked: bool = False
    prompt_ack_coverage_passed: bool = False
    stale_controller_ack_prompt_present: bool = False
    role_direct_router_ack_prompt_present: bool = False
    packet_direct_router_ack_prompt_present: bool = False
    packet_direct_router_result_prompt_present: bool = False
    controller_waits_on_router_notice_prompt_present: bool = False

    heartbeat_resume_loaded_pending_return: bool = False
    manual_resume_loaded_pending_return: bool = False
    recovery_action_available: bool = False

    pm_decision_gate_kept: bool = False
    read_receipt_used_as_semantic_gate: bool = False
    card_ack_used_as_target_work_completion: bool = False
    target_work_completion_wait_preserved: bool = False
    router_advanced: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _inc(state: State, **changes: object) -> State:
    return replace(state, status="running", steps=state.steps + 1, **changes)


class CardEnvelopeStep:
    """Model one card-envelope control-plane transition.

    Input x State -> Set(Output x State)
    reads: role I/O ack ledger, card delivery ledger, card read receipts,
    pending return-event ledger, ack/report envelopes, batch dependency graph,
    batch join policy, and PM decision gate state
    writes: role I/O ack, card envelope delivery, runtime read receipt,
    pending return record, ack/report envelope, receipt coverage result,
    batch join result, recovery decision, or route advancement
    idempotency: delivery and receipt records are keyed by run, resume tick,
    role, agent, card id, delivery id, and card hash
    """

    name = "CardEnvelopeStep"
    input_description = "card envelope protocol tick"
    output_description = "one card envelope state transition"
    reads = (
        "role_io_ack_ledger",
        "card_delivery_ledger",
        "card_read_receipts",
        "pending_return_ledger",
        "ack_clearance_scope",
        "ack_report_envelopes",
        "same_role_bundle_eligibility",
        "batch_dependency_graph",
        "batch_join_policy",
        "pm_decision_gate",
    )
    writes = (
        "role_io_ack",
        "card_envelope_delivery",
        "runtime_card_read_receipt",
        "pending_return_record",
        "ack_report_envelope",
        "receipt_coverage_check",
        "ack_clearance_check",
        "ack_reminder",
        "formal_work_packet_relay",
        "same_role_bundle_ack_join",
        "batch_join_receipt",
        "resume_recovery_decision",
        "router_advance_decision",
    )
    idempotency = "run/role/agent/card/delivery/hash keyed receipts are monotonic"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "passed":
        return

    if state.status == "new":
        yield Transition(
            "legacy_prompt_delivery_shape_recorded_without_v2_receipt",
            _inc(state, legacy_prompt_delivery_recorded=True),
        )
        yield Transition(
            "role_io_protocol_injected_and_acknowledged_for_current_tick",
            _inc(
                state,
                resume_tick_active=True,
                role_io_protocol_injected=True,
                role_io_ack_current_tick=True,
                role_io_ack_current_agent=True,
            ),
        )
        return

    if state.legacy_prompt_delivery_recorded:
        yield Transition(
            "legacy_delivery_stops_before_v2_authorization",
            replace(_inc(state), status="passed"),
        )
        return

    if not state.internal_delivery_action_exposed:
        yield Transition(
            "router_computes_internal_card_delivery_action_without_relay_permission",
            _inc(
                state,
                internal_delivery_action_exposed=True,
                planned_artifact_paths_exposed=True,
                planned_action_relay_allowed=False,
            ),
        )
        return

    if not state.card_envelope_issued:
        yield Transition(
            "router_issues_card_envelope_with_manifest_hash_and_card_return_event",
            _inc(
                state,
                router_auto_committed_internal_action=True,
                committed_artifact_exists=True,
                committed_artifact_hash_verified=True,
                post_apply_envelope_issued=True,
                card_envelope_issued=True,
                card_delivery_recorded=True,
                card_hash_matches_manifest=True,
                required_card_declared=True,
                card_return_event_declared=True,
                checkin_instruction_declared=True,
                checkin_tool_command_declared=True,
                card_ack_token_declared=True,
                direct_router_ack_instruction_declared=True,
                startup_card_before_frontier=True,
                direct_ack_token_frontier_optional_when_missing=True,
                expected_return_path_recorded=True,
                pending_return_recorded=True,
                ack_clearance_scope_recorded=True,
            ),
        )
        return

    if not state.controller_relayed_card_envelope:
        yield Transition(
            "controller_relays_card_envelope_only",
            _inc(
                state,
                controller_relayed_card_envelope=True,
                controller_envelope_only=True,
            ),
        )
        return

    if not state.ack_report_returned and not state.expected_return_missing_detected:
        yield Transition(
            "router_detects_missing_expected_return_and_waits",
            _inc(
                state,
                expected_return_missing_detected=True,
                await_expected_return=True,
            ),
        )
        return

    if state.expected_return_missing_detected and not (
        state.heartbeat_resume_loaded_pending_return or state.manual_resume_loaded_pending_return
    ):
        yield Transition(
            "heartbeat_or_manual_resume_loads_pending_return",
            _inc(
                state,
                heartbeat_resume_loaded_pending_return=True,
                manual_resume_loaded_pending_return=True,
                recovery_action_available=True,
            ),
        )
        return

    if state.expected_return_missing_detected and not state.return_reminder_issued:
        yield Transition(
            "router_issues_missing_return_reminder",
            _inc(
                state,
                return_reminder_issued=True,
                missing_ack_reminder_reuses_original_envelope=True,
            ),
        )
        return

    if state.expected_return_missing_detected and not state.gate_boundary_ack_clearance_checked:
        yield Transition(
            "router_blocks_gate_boundary_on_missing_scope_ack",
            _inc(
                state,
                gate_boundary_transition_requested=True,
                gate_boundary_ack_clearance_checked=True,
                gate_boundary_ack_clearance_passed=False,
                missing_ack_reminder_reuses_original_envelope=True,
            ),
        )
        return

    if state.expected_return_missing_detected and not state.formal_work_packet_ack_clearance_checked:
        yield Transition(
            "router_blocks_formal_work_packet_on_target_missing_ack",
            _inc(
                state,
                formal_work_packet_requested=True,
                formal_work_packet_ack_clearance_checked=True,
                formal_work_packet_ack_clearance_passed=False,
                formal_work_packet_relayed=False,
                missing_ack_reminder_reuses_original_envelope=True,
            ),
        )
        return

    if not state.card_read_receipt_written:
        if not state.redelivery_attempt_issued:
            yield Transition(
                "router_reissues_stale_delivery_attempt_before_role_ack",
                _inc(
                    state,
                    redelivery_attempt_issued=True,
                    stale_delivery_superseded=True,
                ),
            )
        yield Transition(
            "role_runtime_open_card_writes_current_receipt",
            _inc(
                state,
                card_read_receipt_written=True,
                receipt_current_run=True,
                receipt_current_role=True,
                receipt_current_agent=True,
                receipt_hash_matches_manifest=True,
                receipt_after_delivery=True,
                receipt_after_role_io_ack=True,
                role_used_checkin_runtime=True,
                per_card_receipts_referenced=True,
            ),
        )
        return

    if not state.ack_report_returned:
        yield Transition(
            "role_returns_card_ack_envelope_referencing_read_receipts",
            _inc(
                state,
                ack_report_returned=True,
                ack_current_run=True,
                ack_current_role=True,
                ack_current_agent=True,
                ack_references_read_receipts=True,
                ack_returned_after_receipts=True,
                ack_body_empty=True,
                ack_direct_to_router=True,
                ack_router_token_valid=True,
                ack_no_controller_handoff=True,
                per_card_receipts_referenced=True,
            ),
        )
        return

    if (
        state.ack_report_returned
        and not state.card_ack_sent_to_external_event_entrypoint
        and not state.required_card_coverage_checked
    ):
        yield Transition(
            "router_rejects_card_ack_received_at_legacy_external_event_entrypoint",
            _inc(
                state,
                card_ack_sent_to_external_event_entrypoint=True,
                card_ack_external_event_rejected=True,
            ),
        )
        return

    if not state.prompt_ack_coverage_checked:
        yield Transition(
            "prompt_coverage_confirms_direct_router_ack_instructions",
            _inc(
                state,
                prompt_ack_coverage_checked=True,
                prompt_ack_coverage_passed=True,
                role_direct_router_ack_prompt_present=True,
                packet_direct_router_ack_prompt_present=True,
                packet_direct_router_result_prompt_present=True,
                controller_waits_on_router_notice_prompt_present=True,
            ),
        )
        return

    if not state.required_card_coverage_checked:
        yield Transition(
            "router_checks_ack_report_and_required_card_receipt_coverage",
            _inc(
                state,
                required_card_coverage_checked=True,
                required_card_coverage_passed=True,
                check_card_return_apply_required=True,
            ),
        )
        return

    if state.gate_boundary_transition_requested and not state.gate_boundary_ack_clearance_passed:
        yield Transition(
            "router_clears_gate_boundary_after_scope_ack",
            _inc(state, gate_boundary_ack_clearance_passed=True),
        )
        return

    if state.formal_work_packet_requested and not state.formal_work_packet_ack_clearance_passed:
        yield Transition(
            "router_clears_formal_work_packet_after_target_ack",
            _inc(
                state,
                formal_work_packet_ack_clearance_passed=True,
                formal_work_packet_relayed=True,
                target_work_completion_wait_preserved=True,
            ),
        )
        return

    if not state.same_role_bundle_used:
        yield Transition(
            "router_issues_guarded_same_role_system_card_bundle",
            _inc(
                state,
                same_role_bundle_used=True,
                same_role_bundle_same_run_role_agent_tick=True,
                same_role_bundle_manifest_batch_checked=True,
                same_role_bundle_dependencies_safe=True,
                same_role_bundle_no_external_boundary_hidden=True,
                same_role_bundle_member_delivery_records_kept=True,
                same_role_bundle_member_return_events_declared=True,
                same_role_bundle_pending_return_recorded=True,
            ),
        )
        return

    if not (
        state.same_role_bundle_incomplete_ack_detected
        or state.same_role_bundle_per_card_receipts_joined
        or state.same_role_bundle_ack_joined
    ):
        yield Transition(
            "router_records_incomplete_same_role_bundle_ack_and_waits_for_missing_receipts",
            _inc(
                state,
                same_role_bundle_incomplete_ack_detected=True,
                same_role_bundle_missing_receipts_listed=True,
                same_role_bundle_pending_kept_after_incomplete=True,
            ),
        )
        yield Transition(
            "role_returns_same_role_bundle_ack_and_router_joins_per_card_receipts",
            _inc(
                state,
                same_role_bundle_per_card_receipts_joined=True,
                same_role_bundle_ack_joined=True,
                same_role_bundle_check_apply_required=True,
                per_card_receipts_referenced=True,
            ),
        )
        return

    if state.same_role_bundle_incomplete_ack_detected and not state.same_role_bundle_recovery_wait_returned:
        yield Transition(
            "router_returns_same_role_bundle_recovery_wait_for_same_role",
            _inc(state, same_role_bundle_recovery_wait_returned=True),
        )
        return

    if not (state.same_role_bundle_per_card_receipts_joined and state.same_role_bundle_ack_joined):
        yield Transition(
            "role_completes_same_role_bundle_ack_and_router_joins_per_card_receipts",
            _inc(
                state,
                same_role_bundle_per_card_receipts_joined=True,
                same_role_bundle_ack_joined=True,
                same_role_bundle_check_apply_required=True,
                same_role_bundle_recovered_after_complete_ack=state.same_role_bundle_incomplete_ack_detected,
                per_card_receipts_referenced=True,
            ),
        )
        return

    if not state.cross_role_batch_used:
        yield Transition(
            "router_issues_guarded_cross_role_parallel_batch",
            _inc(
                state,
                cross_role_batch_used=True,
                batch_dependency_graph_declared=True,
                batch_join_policy_declared=True,
                batch_card_return_events_declared=True,
                independent_parallel_delivery=True,
            ),
        )
        return

    if not (state.all_required_batch_receipts_joined and state.all_required_batch_ack_reports_joined):
        if not state.missing_batch_join_detected:
            yield Transition(
                "router_detects_missing_cross_role_batch_returns_and_waits",
                _inc(
                    state,
                    missing_batch_join_detected=True,
                    awaiting_batch_join_receipts=True,
                    awaiting_batch_card_return_events=True,
                ),
            )
            return
        yield Transition(
            "roles_return_parallel_batch_acks_and_router_joins_required_receipts",
            _inc(
                state,
                all_required_batch_receipts_joined=True,
                all_required_batch_ack_reports_joined=True,
                per_card_receipts_referenced=True,
            ),
        )
        return

    yield Transition(
        "router_advances_after_card_receipts_batch_join_and_pm_gate",
        replace(
            _inc(
                state,
                pm_decision_gate_kept=True,
                router_advanced=True,
            ),
            status="passed",
        ),
    )


def is_terminal(state: State) -> bool:
    return state.status == "passed"


def is_success(state: State) -> bool:
    if not is_terminal(state):
        return False
    if state.legacy_prompt_delivery_recorded:
        return not state.router_advanced and not state.legacy_delivery_treated_as_read
    return state.router_advanced and not invariant_failures(state)


def _receipt_valid(state: State) -> bool:
    return (
        state.card_read_receipt_written
        and state.role_used_checkin_runtime
        and state.receipt_current_run
        and state.receipt_current_role
        and state.receipt_current_agent
        and state.receipt_hash_matches_manifest
        and state.receipt_after_delivery
        and state.receipt_after_role_io_ack
    )


def _ack_valid(state: State) -> bool:
    return (
        state.ack_report_returned
        and not state.handwritten_ack_attempted
        and state.ack_current_run
        and state.ack_current_role
        and state.ack_current_agent
        and state.ack_references_read_receipts
        and state.ack_returned_after_receipts
        and state.ack_body_empty
        and state.ack_direct_to_router
        and state.ack_router_token_valid
        and state.ack_no_controller_handoff
        and state.card_ack_token_declared
        and state.direct_router_ack_instruction_declared
    )


def controller_must_stay_envelope_only(state: State, trace) -> InvariantResult:
    del trace
    if state.controller_read_card_body:
        return InvariantResult.fail("Controller read a system-card body")
    if state.planned_action_relay_allowed:
        return InvariantResult.fail("pre-apply system-card planning action was marked relay-allowed")
    if state.controller_relayed_preapply_artifact or state.runtime_open_blocked_not_committed:
        return InvariantResult.fail("Controller relayed planned system-card action before committed envelope artifact existed")
    if state.public_system_card_apply_used:
        return InvariantResult.fail("public Controller apply attempted to deliver a relay-only system-card action")
    if state.controller_relayed_card_envelope and not (
        state.committed_artifact_exists
        and state.committed_artifact_hash_verified
        and state.card_delivery_recorded
        and state.pending_return_recorded
    ):
        return InvariantResult.fail("Controller relayed card envelope before artifact, hash, ledger, and return wait were committed")
    if state.controller_relayed_card_envelope and not state.controller_envelope_only:
        return InvariantResult.fail("Controller relayed a card without envelope-only proof")
    if state.controller_mutated_batch or state.controller_skipped_envelope:
        return InvariantResult.fail("Controller changed Router-authored batch delivery")
    return InvariantResult.pass_()


def required_card_receipt_gate(state: State, trace) -> InvariantResult:
    del trace
    if state.legacy_return_event_field_used:
        return InvariantResult.fail("legacy return_event JSON field was still emitted")
    if state.card_envelope_issued and not (
        state.card_return_event_declared and state.expected_return_path_recorded and state.pending_return_recorded
    ):
        return InvariantResult.fail("card envelope lacked a Router-owned expected card_return_event")
    if state.card_envelope_issued and not (
        state.checkin_instruction_declared and state.checkin_tool_command_declared
    ):
        return InvariantResult.fail("card envelope omitted explicit runtime check-in instruction")
    if state.card_envelope_issued and not (
        state.card_ack_token_declared and state.direct_router_ack_instruction_declared
    ):
        return InvariantResult.fail("card envelope omitted direct Router ACK token or instruction")
    if state.startup_card_before_frontier and state.direct_ack_token_requires_frontier_before_available:
        return InvariantResult.fail("direct Router ACK token required route/frontier before startup frontier exists")
    if state.startup_card_before_frontier and not state.direct_ack_token_frontier_optional_when_missing:
        return InvariantResult.fail("startup card ACK token did not allow missing route/frontier binding")
    if state.card_envelope_issued and not (
        state.router_auto_committed_internal_action
        and state.committed_artifact_exists
        and state.post_apply_envelope_issued
    ):
        return InvariantResult.fail("system card envelope was issued without an internal auto-commit artifact lifecycle")
    if state.legacy_delivery_treated_as_read:
        return InvariantResult.fail("legacy prompt delivery record was treated as a v2 read receipt")
    if state.required_card_coverage_passed and not (_receipt_valid(state) and _ack_valid(state)):
        return InvariantResult.fail("required system card coverage passed without valid read receipt and ack/report envelope")
    if state.router_advanced and state.required_card_declared and not (
        state.required_card_coverage_checked
        and state.required_card_coverage_passed
        and _receipt_valid(state)
        and _ack_valid(state)
    ):
        return InvariantResult.fail("Router advanced before required system-card read receipt and ack/report coverage")
    if (state.missing_required_receipt_detected or state.await_required_receipts) and state.router_advanced and not _receipt_valid(state):
        return InvariantResult.fail("Router advanced while required card receipt wait/repair was unresolved")
    if (state.expected_return_missing_detected or state.await_expected_return) and state.router_advanced and not _ack_valid(state):
        return InvariantResult.fail("Router advanced while expected ack/report wait was unresolved")
    return InvariantResult.pass_()


def card_return_ack_uses_router_check_action(state: State, trace) -> InvariantResult:
    del trace
    if state.card_ack_recorded_as_external_event:
        return InvariantResult.fail("card ack was accepted as a normal external event instead of direct Router ACK")
    if state.card_ack_external_event_auto_rerouted:
        return InvariantResult.fail("legacy card ACK external-event entrypoint still auto-rerouted instead of hard failing")
    if state.card_ack_sent_to_external_event_entrypoint and not state.card_ack_external_event_rejected:
        return InvariantResult.fail("legacy card ACK external-event entrypoint was not rejected")
    if state.required_card_coverage_checked and not state.check_card_return_apply_required:
        return InvariantResult.fail("check_card_return_event changed state but was marked apply_required false")
    return InvariantResult.pass_()


def prompt_ack_instruction_coverage(state: State, trace) -> InvariantResult:
    del trace
    if state.stale_controller_ack_prompt_present:
        return InvariantResult.fail("stale prompt still instructed ACK return to Controller")
    if state.prompt_ack_coverage_checked and not state.prompt_ack_coverage_passed:
        return InvariantResult.fail("prompt coverage check did not pass direct Router ACK instructions")
    if state.router_advanced and not (
        state.prompt_ack_coverage_checked
        and state.prompt_ack_coverage_passed
        and state.role_direct_router_ack_prompt_present
        and state.packet_direct_router_ack_prompt_present
        and state.packet_direct_router_result_prompt_present
        and state.controller_waits_on_router_notice_prompt_present
    ):
        return InvariantResult.fail("Router advanced without prompt coverage for direct Router ACK instructions")
    return InvariantResult.pass_()


def read_receipt_identity_gate(state: State, trace) -> InvariantResult:
    del trace
    if state.card_read_receipt_written and not _receipt_valid(state):
        return InvariantResult.fail("card read receipt did not match current run, role, agent, hash, delivery, and I/O ack")
    return InvariantResult.pass_()


def ack_report_must_reference_receipts(state: State, trace) -> InvariantResult:
    del trace
    if state.ack_report_returned and not _ack_valid(state):
        return InvariantResult.fail("ack/report envelope did not match current run, role, agent, receipt refs, and relay boundary")
    if state.ack_references_read_receipts and not _receipt_valid(state):
        return InvariantResult.fail("ack/report referenced invalid or incomplete read receipts")
    return InvariantResult.pass_()


def same_role_bundle_requires_global_safe_segment(state: State, trace) -> InvariantResult:
    del trace
    if not state.same_role_bundle_used:
        return InvariantResult.pass_()
    if not (
        state.same_role_bundle_same_run_role_agent_tick
        and state.same_role_bundle_manifest_batch_checked
        and state.same_role_bundle_member_delivery_records_kept
        and state.same_role_bundle_member_return_events_declared
        and state.same_role_bundle_pending_return_recorded
    ):
        return InvariantResult.fail(
            "same-role system-card bundle crossed run, role, agent, or resume-tick boundary"
        )
    if not (
        state.same_role_bundle_dependencies_safe
        and state.same_role_bundle_no_external_boundary_hidden
    ):
        return InvariantResult.fail(
            "same-role system-card bundle included an unsafe dependency or external boundary"
        )
    if state.same_role_bundle_ack_joined and not state.same_role_bundle_check_apply_required:
        return InvariantResult.fail("same-role bundle return check was not an explicit apply-required router action")
    if state.same_role_bundle_incomplete_ack_detected and not (
        state.same_role_bundle_missing_receipts_listed
        and state.same_role_bundle_pending_kept_after_incomplete
    ):
        return InvariantResult.fail("incomplete same-role bundle ACK did not list missing receipts and keep pending return")
    if state.router_advanced and state.same_role_bundle_incomplete_ack_detected and not state.same_role_bundle_recovery_wait_returned:
        return InvariantResult.fail("incomplete same-role bundle ACK did not return a same-role recovery wait")
    if state.router_advanced and state.same_role_bundle_incomplete_ack_detected and not state.same_role_bundle_recovered_after_complete_ack:
        return InvariantResult.fail("same-role bundle advanced after incomplete ACK without a completed recovery ACK")
    if state.router_advanced and not (
        state.same_role_bundle_per_card_receipts_joined
        and state.same_role_bundle_ack_joined
        and state.per_card_receipts_referenced
    ):
        return InvariantResult.fail(
            "same-role system-card bundle advanced without per-card receipt and bundle ACK join"
        )
    return InvariantResult.pass_()


def pending_return_wait_has_recovery_path(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "passed" and state.await_expected_return and not state.ack_report_returned and not (
        state.recovery_action_available or state.return_reminder_issued or state.redelivery_attempt_issued
    ):
        return InvariantResult.fail("pending return wait had no heartbeat/manual resume recovery action")
    return InvariantResult.pass_()


def scoped_ack_clearance_blocks_gate_and_work(state: State, trace) -> InvariantResult:
    del trace
    if state.card_envelope_issued and not state.ack_clearance_scope_recorded:
        return InvariantResult.fail("system-card pending return lacked ACK clearance scope metadata")
    if (
        state.gate_boundary_transition_requested
        and state.router_advanced
        and not state.gate_boundary_ack_clearance_passed
    ):
        return InvariantResult.fail("Router crossed a route gate before current-scope system-card ACK clearance")
    if (
        state.formal_work_packet_relayed
        and not (
            state.formal_work_packet_ack_clearance_checked
            and state.formal_work_packet_ack_clearance_passed
            and _ack_valid(state)
        )
    ):
        return InvariantResult.fail("formal work packet was relayed before target-role system-card ACK clearance")
    if state.expected_return_missing_detected and state.return_reminder_issued and not (
        state.missing_ack_reminder_reuses_original_envelope
    ):
        return InvariantResult.fail("missing system-card ACK recovery did not remind against the original committed envelope")
    if state.duplicate_system_card_reissued_for_missing_ack:
        return InvariantResult.fail("missing system-card ACK triggered duplicate card delivery instead of original-card reminder")
    if state.redelivery_attempt_issued and not state.stale_delivery_superseded:
        return InvariantResult.fail("system-card redelivery was not limited to stale, lost, invalid, or replaced delivery recovery")
    return InvariantResult.pass_()


def role_io_ack_required_for_resume_and_replacement(state: State, trace) -> InvariantResult:
    del trace
    if state.card_read_receipt_written and (state.resume_tick_active or state.role_replacement_active):
        if not (
            state.role_io_protocol_injected
            and state.role_io_ack_current_tick
            and state.role_io_ack_current_agent
            and state.receipt_after_role_io_ack
        ):
            return InvariantResult.fail("role processed card/mail without current resume-tick role I/O acknowledgement")
    return InvariantResult.pass_()


def bundle_receipt_cannot_replace_single_card_receipts(state: State, trace) -> InvariantResult:
    del trace
    if state.bundle_receipt_used and not state.per_card_receipts_referenced:
        return InvariantResult.fail("bundle receipt replaced independent per-card receipts")
    return InvariantResult.pass_()


def cross_role_batch_requires_dependency_graph_and_join(state: State, trace) -> InvariantResult:
    del trace
    if state.cross_role_batch_used and not (
        state.batch_dependency_graph_declared
        and state.batch_join_policy_declared
        and state.batch_card_return_events_declared
        and state.independent_parallel_delivery
    ):
        return InvariantResult.fail("cross-role batch lacked explicit dependency graph, return events, join policy, or independence proof")
    if state.hidden_dependency_parallelized:
        return InvariantResult.fail("cross-role batch parallelized a hidden dependency")
    if state.router_advanced and state.cross_role_batch_used and not (
        state.all_required_batch_receipts_joined and state.all_required_batch_ack_reports_joined
    ):
        return InvariantResult.fail("Router advanced before required cross-role batch ack/report and receipt joins")
    if (
        state.missing_batch_join_detected
        or state.awaiting_batch_join_receipts
        or state.awaiting_batch_card_return_events
    ) and state.router_advanced and not (
        state.all_required_batch_receipts_joined and state.all_required_batch_ack_reports_joined
    ):
        return InvariantResult.fail("Router advanced while cross-role batch return/join wait was unresolved")
    return InvariantResult.pass_()


def preload_receipt_cannot_authorize_work(state: State, trace) -> InvariantResult:
    del trace
    if state.preload_only_receipt_used_as_authorization:
        return InvariantResult.fail("preload-only receipt was used as work authorization")
    return InvariantResult.pass_()


def read_receipt_is_not_semantic_gate(state: State, trace) -> InvariantResult:
    del trace
    if state.read_receipt_used_as_semantic_gate:
        return InvariantResult.fail("system-card read receipt replaced semantic PM/reviewer/officer judgement")
    if state.card_ack_used_as_target_work_completion:
        return InvariantResult.fail("system-card ACK was treated as target-role work completion")
    if state.formal_work_packet_relayed and not state.target_work_completion_wait_preserved:
        return InvariantResult.fail("formal work packet relay did not preserve target-role work completion wait")
    if state.router_advanced and not state.pm_decision_gate_kept:
        return InvariantResult.fail("Router advanced without preserving PM decision gate")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "controller_must_stay_envelope_only",
        "Controller may relay card and batch envelopes but must not read card bodies or mutate Router batches.",
        controller_must_stay_envelope_only,
    ),
    Invariant(
        "required_card_receipt_gate",
        "Required card coverage and Router advancement require valid runtime read receipts.",
        required_card_receipt_gate,
    ),
    Invariant(
        "card_return_ack_uses_router_check_action",
        "Card acks are mechanical return checks and must use the direct Router ACK path.",
        card_return_ack_uses_router_check_action,
    ),
    Invariant(
        "prompt_ack_instruction_coverage",
        "Prompts and packet templates must teach direct Router ACKs and reject stale Controller ACK instructions.",
        prompt_ack_instruction_coverage,
    ),
    Invariant(
        "read_receipt_identity_gate",
        "Card read receipt must match current run, role, agent, hash, delivery time, and I/O ack.",
        read_receipt_identity_gate,
    ),
    Invariant(
        "ack_report_must_reference_receipts",
        "Ack/report envelopes must be current, envelope-only, and reference valid runtime read receipts.",
        ack_report_must_reference_receipts,
    ),
    Invariant(
        "pending_return_wait_has_recovery_path",
        "Pending return waits must have a heartbeat/manual-resume recovery, reminder, or redelivery path.",
        pending_return_wait_has_recovery_path,
    ),
    Invariant(
        "scoped_ack_clearance_blocks_gate_and_work",
        "Gate movement and formal work packets require scoped system-card ACK clearance and reminder-only missing-ACK recovery.",
        scoped_ack_clearance_blocks_gate_and_work,
    ),
    Invariant(
        "role_io_ack_required_for_resume_and_replacement",
        "Resume and replacement require current role I/O acknowledgement before card or mail handling.",
        role_io_ack_required_for_resume_and_replacement,
    ),
    Invariant(
        "bundle_receipt_cannot_replace_single_card_receipts",
        "Bundle receipts are references and cannot replace independent per-card receipts.",
        bundle_receipt_cannot_replace_single_card_receipts,
    ),
    Invariant(
        "same_role_bundle_requires_global_safe_segment",
        "Same-role system-card bundles must keep per-card evidence and cannot hide external boundaries.",
        same_role_bundle_requires_global_safe_segment,
    ),
    Invariant(
        "cross_role_batch_requires_dependency_graph_and_join",
        "Cross-role parallel batch delivery requires explicit Router dependency graph and receipt join.",
        cross_role_batch_requires_dependency_graph_and_join,
    ),
    Invariant(
        "preload_receipt_cannot_authorize_work",
        "Preload-only receipts cannot authorize work execution.",
        preload_receipt_cannot_authorize_work,
    ),
    Invariant(
        "read_receipt_is_not_semantic_gate",
        "Read receipts prove mechanical open only and never replace semantic judgement gates.",
        read_receipt_is_not_semantic_gate,
    ),
)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 25

REQUIRED_LABELS = (
    "legacy_prompt_delivery_shape_recorded_without_v2_receipt",
    "legacy_delivery_stops_before_v2_authorization",
    "role_io_protocol_injected_and_acknowledged_for_current_tick",
    "router_computes_internal_card_delivery_action_without_relay_permission",
    "router_issues_card_envelope_with_manifest_hash_and_card_return_event",
    "controller_relays_card_envelope_only",
    "router_detects_missing_expected_return_and_waits",
    "heartbeat_or_manual_resume_loads_pending_return",
    "router_issues_missing_return_reminder",
    "router_blocks_gate_boundary_on_missing_scope_ack",
    "router_blocks_formal_work_packet_on_target_missing_ack",
    "router_reissues_stale_delivery_attempt_before_role_ack",
    "role_runtime_open_card_writes_current_receipt",
    "role_returns_card_ack_envelope_referencing_read_receipts",
    "router_rejects_card_ack_received_at_legacy_external_event_entrypoint",
    "prompt_coverage_confirms_direct_router_ack_instructions",
    "router_checks_ack_report_and_required_card_receipt_coverage",
    "router_clears_gate_boundary_after_scope_ack",
    "router_clears_formal_work_packet_after_target_ack",
    "router_issues_guarded_same_role_system_card_bundle",
    "router_records_incomplete_same_role_bundle_ack_and_waits_for_missing_receipts",
    "router_returns_same_role_bundle_recovery_wait_for_same_role",
    "role_returns_same_role_bundle_ack_and_router_joins_per_card_receipts",
    "role_completes_same_role_bundle_ack_and_router_joins_per_card_receipts",
    "router_issues_guarded_cross_role_parallel_batch",
    "router_detects_missing_cross_role_batch_returns_and_waits",
    "roles_return_parallel_batch_acks_and_router_joins_required_receipts",
    "router_advances_after_card_receipts_batch_join_and_pm_gate",
)


def build_workflow() -> Workflow:
    return Workflow((CardEnvelopeStep(),), name="flowpilot_card_envelope")


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(str(result.message))
    return failures


def target_v2_state() -> State:
    return State(
        status="passed",
        resume_tick_active=True,
        role_io_protocol_injected=True,
        role_io_ack_current_tick=True,
        role_io_ack_current_agent=True,
        internal_delivery_action_exposed=True,
        planned_artifact_paths_exposed=True,
        planned_action_relay_allowed=False,
        router_auto_committed_internal_action=True,
        committed_artifact_exists=True,
        committed_artifact_hash_verified=True,
        post_apply_envelope_issued=True,
        public_system_card_apply_used=False,
        card_envelope_issued=True,
        card_delivery_recorded=True,
        card_hash_matches_manifest=True,
        card_return_event_declared=True,
        checkin_instruction_declared=True,
        checkin_tool_command_declared=True,
        card_ack_token_declared=True,
        direct_router_ack_instruction_declared=True,
        startup_card_before_frontier=True,
        direct_ack_token_frontier_optional_when_missing=True,
        expected_return_path_recorded=True,
        pending_return_recorded=True,
        ack_clearance_scope_recorded=True,
        controller_relayed_card_envelope=True,
        controller_envelope_only=True,
        card_read_receipt_written=True,
        receipt_current_run=True,
        receipt_current_role=True,
        receipt_current_agent=True,
        receipt_hash_matches_manifest=True,
        receipt_after_delivery=True,
        receipt_after_role_io_ack=True,
        role_used_checkin_runtime=True,
        required_card_declared=True,
        required_card_coverage_checked=True,
        required_card_coverage_passed=True,
        missing_required_receipt_detected=True,
        await_required_receipts=True,
        expected_return_missing_detected=True,
        await_expected_return=True,
        return_reminder_issued=True,
        gate_boundary_transition_requested=True,
        gate_boundary_ack_clearance_checked=True,
        gate_boundary_ack_clearance_passed=True,
        formal_work_packet_requested=True,
        formal_work_packet_ack_clearance_checked=True,
        formal_work_packet_ack_clearance_passed=True,
        formal_work_packet_relayed=True,
        missing_ack_reminder_reuses_original_envelope=True,
        ack_report_returned=True,
        ack_current_run=True,
        ack_current_role=True,
        ack_current_agent=True,
        ack_references_read_receipts=True,
        ack_returned_after_receipts=True,
        ack_body_empty=True,
        ack_direct_to_router=True,
        ack_router_token_valid=True,
        ack_no_controller_handoff=True,
        card_ack_sent_to_external_event_entrypoint=True,
        card_ack_external_event_rejected=True,
        check_card_return_apply_required=True,
        receipt_repair_request_issued=True,
        redelivery_attempt_issued=True,
        stale_delivery_superseded=True,
        per_card_receipts_referenced=True,
        same_role_bundle_used=True,
        same_role_bundle_same_run_role_agent_tick=True,
        same_role_bundle_manifest_batch_checked=True,
        same_role_bundle_dependencies_safe=True,
        same_role_bundle_no_external_boundary_hidden=True,
        same_role_bundle_member_delivery_records_kept=True,
        same_role_bundle_member_return_events_declared=True,
        same_role_bundle_pending_return_recorded=True,
        same_role_bundle_incomplete_ack_detected=True,
        same_role_bundle_missing_receipts_listed=True,
        same_role_bundle_pending_kept_after_incomplete=True,
        same_role_bundle_recovery_wait_returned=True,
        same_role_bundle_recovered_after_complete_ack=True,
        same_role_bundle_per_card_receipts_joined=True,
        same_role_bundle_ack_joined=True,
        same_role_bundle_check_apply_required=True,
        cross_role_batch_used=True,
        batch_dependency_graph_declared=True,
        batch_join_policy_declared=True,
        batch_card_return_events_declared=True,
        independent_parallel_delivery=True,
        all_required_batch_receipts_joined=True,
        all_required_batch_ack_reports_joined=True,
        missing_batch_join_detected=True,
        awaiting_batch_join_receipts=True,
        awaiting_batch_card_return_events=True,
        prompt_ack_coverage_checked=True,
        prompt_ack_coverage_passed=True,
        role_direct_router_ack_prompt_present=True,
        packet_direct_router_ack_prompt_present=True,
        packet_direct_router_result_prompt_present=True,
        controller_waits_on_router_notice_prompt_present=True,
        heartbeat_resume_loaded_pending_return=True,
        manual_resume_loaded_pending_return=True,
        recovery_action_available=True,
        pm_decision_gate_kept=True,
        target_work_completion_wait_preserved=True,
        router_advanced=True,
    )


def legacy_prompt_delivery_state() -> State:
    return State(
        status="passed",
        legacy_prompt_delivery_recorded=True,
        card_delivery_recorded=True,
        required_card_declared=True,
    )


def legacy_expected_bad_state() -> State:
    return replace(
        legacy_prompt_delivery_state(),
        legacy_delivery_treated_as_read=True,
        required_card_coverage_checked=True,
        required_card_coverage_passed=True,
        check_card_return_apply_required=True,
        pm_decision_gate_kept=True,
        router_advanced=True,
    )


def hazard_states() -> dict[str, State]:
    safe = target_v2_state()
    return {
        "legacy_delivery_treated_as_read": legacy_expected_bad_state(),
        "preapply_pending_relayed_as_committed_artifact": replace(
            safe,
            router_auto_committed_internal_action=False,
            committed_artifact_exists=False,
            committed_artifact_hash_verified=False,
            post_apply_envelope_issued=False,
            card_delivery_recorded=False,
            pending_return_recorded=False,
            controller_relayed_preapply_artifact=True,
            runtime_open_blocked_not_committed=True,
        ),
        "preapply_planned_action_marked_relay_allowed": replace(
            safe,
            planned_action_relay_allowed=True,
        ),
        "public_apply_deliver_system_card_used": replace(
            safe,
            public_system_card_apply_used=True,
        ),
        "legacy_return_event_field_used": replace(
            safe,
            legacy_return_event_field_used=True,
        ),
        "missing_checkin_instruction": replace(
            safe,
            checkin_instruction_declared=False,
        ),
        "missing_checkin_tool_command": replace(
            safe,
            checkin_tool_command_declared=False,
        ),
        "missing_card_ack_token": replace(
            safe,
            card_ack_token_declared=False,
        ),
        "missing_direct_router_ack_instruction": replace(
            safe,
            direct_router_ack_instruction_declared=False,
        ),
        "direct_ack_token_requires_frontier_before_startup_frontier_exists": replace(
            safe,
            direct_ack_token_requires_frontier_before_available=True,
        ),
        "startup_card_token_missing_frontier_optional_binding": replace(
            safe,
            direct_ack_token_frontier_optional_when_missing=False,
        ),
        "role_handwrites_ack_instead_of_runtime": replace(
            safe,
            role_used_checkin_runtime=False,
            handwritten_ack_attempted=True,
        ),
        "card_ack_recorded_as_external_event": replace(
            safe,
            card_ack_recorded_as_external_event=True,
        ),
        "card_ack_external_event_auto_rerouted": replace(
            safe,
            card_ack_sent_to_external_event_entrypoint=True,
            card_ack_external_event_auto_rerouted=True,
            card_ack_external_event_rejected=False,
        ),
        "card_ack_external_event_not_rejected": replace(
            safe,
            card_ack_sent_to_external_event_entrypoint=True,
            card_ack_external_event_rejected=False,
        ),
        "check_card_return_apply_optional": replace(
            safe,
            check_card_return_apply_required=False,
        ),
        "missing_read_receipt": replace(
            safe,
            card_read_receipt_written=False,
            required_card_coverage_passed=True,
            await_required_receipts=True,
        ),
        "missing_ack_report": replace(
            safe,
            ack_report_returned=False,
            required_card_coverage_passed=True,
            await_expected_return=True,
        ),
        "ack_without_receipt_refs": replace(
            safe,
            ack_references_read_receipts=False,
        ),
        "ack_without_direct_router_token": replace(
            safe,
            ack_router_token_valid=False,
        ),
        "ack_sent_through_controller_handoff": replace(
            safe,
            ack_no_controller_handoff=False,
        ),
        "ack_contains_body_content": replace(
            safe,
            ack_body_empty=False,
        ),
        "ack_not_submitted_to_router": replace(
            safe,
            ack_direct_to_router=False,
        ),
        "advanced_during_missing_receipt_wait": replace(
            safe,
            card_read_receipt_written=False,
            await_required_receipts=True,
            router_advanced=True,
        ),
        "advanced_during_missing_return_wait": replace(
            safe,
            ack_report_returned=False,
            await_expected_return=True,
            router_advanced=True,
        ),
        "pending_return_without_recovery": replace(
            safe,
            ack_report_returned=False,
            await_expected_return=True,
            recovery_action_available=False,
            return_reminder_issued=False,
            redelivery_attempt_issued=False,
            router_advanced=False,
        ),
        "gate_boundary_advanced_before_scope_ack": replace(
            safe,
            gate_boundary_transition_requested=True,
            gate_boundary_ack_clearance_checked=True,
            gate_boundary_ack_clearance_passed=False,
            router_advanced=True,
        ),
        "formal_work_packet_relayed_before_target_ack": replace(
            safe,
            ack_report_returned=False,
            formal_work_packet_requested=True,
            formal_work_packet_ack_clearance_checked=True,
            formal_work_packet_ack_clearance_passed=False,
            formal_work_packet_relayed=True,
        ),
        "missing_ack_duplicate_system_card_reissued": replace(
            safe,
            expected_return_missing_detected=True,
            return_reminder_issued=False,
            duplicate_system_card_reissued_for_missing_ack=True,
            redelivery_attempt_issued=True,
            stale_delivery_superseded=False,
        ),
        "card_ack_treated_as_target_work_completion": replace(
            safe,
            card_ack_used_as_target_work_completion=True,
            target_work_completion_wait_preserved=False,
        ),
        "wrong_role_receipt": replace(safe, receipt_current_role=False),
        "wrong_role_ack_report": replace(safe, ack_current_role=False),
        "old_run_receipt": replace(safe, receipt_current_run=False),
        "old_run_ack_report": replace(safe, ack_current_run=False),
        "old_agent_after_replacement": replace(
            safe,
            role_replacement_active=True,
            role_io_ack_current_agent=True,
            receipt_current_agent=False,
            ack_current_agent=False,
        ),
        "hash_mismatch": replace(safe, receipt_hash_matches_manifest=False),
        "receipt_before_delivery": replace(safe, receipt_after_delivery=False),
        "resume_without_role_io_ack": replace(
            safe,
            role_io_protocol_injected=False,
            role_io_ack_current_tick=False,
            receipt_after_role_io_ack=False,
        ),
        "bundle_receipt_without_per_card_refs": replace(
            safe,
            bundle_receipt_used=True,
            per_card_receipts_referenced=False,
        ),
        "same_role_bundle_cross_role_or_run": replace(
            safe,
            same_role_bundle_same_run_role_agent_tick=False,
        ),
        "same_role_bundle_missing_manifest_batch": replace(
            safe,
            same_role_bundle_manifest_batch_checked=False,
        ),
        "same_role_bundle_unsafe_dependency": replace(
            safe,
            same_role_bundle_dependencies_safe=False,
        ),
        "same_role_bundle_hides_external_boundary": replace(
            safe,
            same_role_bundle_no_external_boundary_hidden=False,
        ),
        "same_role_bundle_missing_per_card_receipts": replace(
            safe,
            same_role_bundle_per_card_receipts_joined=False,
            same_role_bundle_ack_joined=True,
            per_card_receipts_referenced=False,
        ),
        "same_role_bundle_missing_ack_join": replace(
            safe,
            same_role_bundle_ack_joined=False,
            same_role_bundle_per_card_receipts_joined=True,
        ),
        "same_role_bundle_check_apply_optional": replace(
            safe,
            same_role_bundle_check_apply_required=False,
        ),
        "same_role_bundle_incomplete_ack_missing_recovery_wait": replace(
            safe,
            same_role_bundle_incomplete_ack_detected=True,
            same_role_bundle_missing_receipts_listed=True,
            same_role_bundle_pending_kept_after_incomplete=True,
            same_role_bundle_recovery_wait_returned=False,
        ),
        "same_role_bundle_incomplete_ack_advanced_without_complete_ack": replace(
            safe,
            same_role_bundle_incomplete_ack_detected=True,
            same_role_bundle_missing_receipts_listed=True,
            same_role_bundle_pending_kept_after_incomplete=True,
            same_role_bundle_recovery_wait_returned=True,
            same_role_bundle_recovered_after_complete_ack=False,
        ),
        "preload_receipt_authorizes_work": replace(
            safe,
            preload_only_receipt_used_as_authorization=True,
        ),
        "cross_role_batch_missing_dependency_graph": replace(
            safe,
            batch_dependency_graph_declared=False,
        ),
        "cross_role_batch_missing_card_return_events": replace(
            safe,
            batch_card_return_events_declared=False,
        ),
        "cross_role_hidden_dependency_parallelized": replace(
            safe,
            hidden_dependency_parallelized=True,
        ),
        "cross_role_missing_required_join": replace(
            safe,
            all_required_batch_receipts_joined=False,
            all_required_batch_ack_reports_joined=False,
            awaiting_batch_join_receipts=True,
            awaiting_batch_card_return_events=True,
            router_advanced=True,
        ),
        "controller_reads_card_body": replace(
            safe,
            controller_read_card_body=True,
        ),
        "controller_mutates_batch": replace(
            safe,
            controller_mutated_batch=True,
        ),
        "read_receipt_replaces_semantic_gate": replace(
            safe,
            read_receipt_used_as_semantic_gate=True,
            pm_decision_gate_kept=False,
        ),
        "stale_controller_ack_prompt": replace(
            safe,
            stale_controller_ack_prompt_present=True,
        ),
        "missing_role_direct_router_ack_prompt": replace(
            safe,
            role_direct_router_ack_prompt_present=False,
        ),
        "missing_packet_direct_router_ack_prompt": replace(
            safe,
            packet_direct_router_ack_prompt_present=False,
        ),
        "missing_packet_direct_router_result_prompt": replace(
            safe,
            packet_direct_router_result_prompt_present=False,
        ),
        "missing_controller_waits_on_router_notice_prompt": replace(
            safe,
            controller_waits_on_router_notice_prompt_present=False,
        ),
    }
