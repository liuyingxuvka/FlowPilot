"""FlowGuard model for FlowPilot dynamic return-path authority.

Risk intent brief:
- Prevent role-output reports from inventing a formal Router event when an
  output contract says the event is router supplied.
- Model the difference between static prompt/card guidance, mechanical
  role-output validation, and the live Router wait state that can actually
  receive an event.
- Protected harms: system-card-only work causing a formal model report with no
  concrete return lease, a role guessing an event name, a registered event being
  unavailable in the current wait state, and green role-output validation being
  mistaken for permission to continue.
- Protect gate-bearing phases from accepting a legacy/general report or repair
  follow-up that is recorded but does not satisfy the current gate flag.
- Treat the Product FlowGuard Officer product-architecture gate as a product
  behavior model submission, and treat the Process FlowGuard Officer route
  gate as a process route model submission. Keep old `modelability` and
  `route_process_check` names only as compatibility aliases for older events
  and artifacts.
- Hard invariants: router-supplied contracts require a concrete event from the
  current Router wait or a PM role-work packet result contract; system cards do
  not authorize formal output by themselves; mechanical output validation cannot
  imply Router acceptance; a current gate cannot continue until its concrete
  gate event or mapped PM result satisfies the gate flag; and a current run with
  rejected role-output events must be classified as blocked even when the report
  content was meaningful.
- Blindspot: this model reads only metadata for live-run projection. It does
  not inspect sealed report bodies or judge the semantic quality of a report.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_IDENTITY_CARD_ACK_ONLY = "valid_identity_card_ack_only"
VALID_PM_ROLE_WORK_PACKET_RESULT = "valid_pm_role_work_packet_result"
VALID_DIRECT_ROUTER_WAIT_EVENT = "valid_direct_router_wait_event"
VALID_ROUTER_REGISTERED_TASK_CARD_RESULT = "valid_router_registered_task_card_result"
VALID_ACTIVE_HOLDER_PACKET_RESULT = "valid_active_holder_packet_result"
VALID_FIXED_EVENT_CONTRACT = "valid_fixed_event_contract"
VALID_CURRENT_GATE_EVENT_SATISFIES_FLAG = "valid_current_gate_event_satisfies_flag"
VALID_PM_ROLE_WORK_RESULT_MAPPED_TO_CURRENT_GATE = "valid_pm_role_work_result_mapped_to_current_gate"
VALID_PRODUCT_BEHAVIOR_MODEL_SUBMISSION_WITH_COMPAT_ALIAS = "valid_product_behavior_model_submission_with_compat_alias"
VALID_PROCESS_ROUTE_MODEL_SUBMISSION_WITH_COMPAT_ALIAS = "valid_process_route_model_submission_with_compat_alias"

SYSTEM_CARD_ONLY_ROUTER_SUPPLIED_REPORT = "system_card_only_router_supplied_report"
TASK_CARD_WITHOUT_WORK_AUTHORITY = "task_card_without_work_authority"
IDENTITY_CARD_CARRIES_HIDDEN_WORK = "identity_card_carries_hidden_work"
ROLE_GUESSES_UNKNOWN_EVENT = "role_guesses_unknown_event"
REGISTERED_EVENT_NOT_CURRENTLY_ALLOWED = "registered_event_not_currently_allowed"
MECHANICAL_GREEN_USED_AS_ROUTER_ACCEPTANCE = "mechanical_green_used_as_router_acceptance"
STATIC_CARD_GUIDANCE_USED_AS_DYNAMIC_LEASE = "static_card_guidance_used_as_dynamic_lease"
LEGACY_DIRECT_EVENT_COMPETES_WITH_PM_PACKET = "legacy_direct_event_competes_with_pm_packet"
PM_ROLE_WORK_WRONG_RECIPIENT = "pm_role_work_wrong_recipient"
WRONG_ROLE_USES_WORK_AUTHORITY = "wrong_role_uses_work_authority"
WRONG_CONTRACT_USES_WORK_AUTHORITY = "wrong_contract_uses_work_authority"
STALE_WORK_AUTHORITY_USED = "stale_work_authority_used"
GATE_CARD_WITHOUT_COMPLETION_CONTRACT = "gate_card_without_completion_contract"
LEGACY_EVENT_ACCEPTED_WITHOUT_REQUIRED_GATE_FLAG = "legacy_event_accepted_without_required_gate_flag"
PM_REPAIR_RESOLVES_BLOCKER_WITHOUT_GATE_EVENT = "pm_repair_resolves_blocker_without_gate_event"
PM_ROLE_WORK_RESULT_NOT_MAPPED_TO_CURRENT_GATE = "pm_role_work_result_not_mapped_to_current_gate"
PRODUCT_BEHAVIOR_MODEL_GATE_USES_MODELABILITY_AS_CANONICAL_COMPLETION = (
    "product_behavior_model_gate_uses_modelability_as_canonical_completion"
)
PRODUCT_BEHAVIOR_MODEL_ALIAS_DOES_NOT_SET_COMPATIBILITY_FLAGS = (
    "product_behavior_model_alias_does_not_set_compatibility_flags"
)
PRODUCT_BEHAVIOR_MODEL_SUBMISSION_SKIPS_PM_ACCEPTANCE = "product_behavior_model_submission_skips_pm_acceptance"
PRODUCT_BEHAVIOR_MODEL_MISSING_CANONICAL_ARTIFACT = "product_behavior_model_missing_canonical_artifact"
PRODUCT_BEHAVIOR_MODEL_BLOCK_ALIAS_FLAGS_DIVERGE = "product_behavior_model_block_alias_flags_diverge"
PROCESS_ROUTE_MODEL_GATE_USES_ROUTE_CHECK_AS_CANONICAL_COMPLETION = (
    "process_route_model_gate_uses_route_check_as_canonical_completion"
)
PROCESS_ROUTE_MODEL_ALIAS_DOES_NOT_SET_COMPATIBILITY_FLAGS = (
    "process_route_model_alias_does_not_set_compatibility_flags"
)
PROCESS_ROUTE_MODEL_SUBMISSION_SKIPS_PM_ACCEPTANCE = "process_route_model_submission_skips_pm_acceptance"
PROCESS_ROUTE_MODEL_MISSING_CANONICAL_ARTIFACT = "process_route_model_missing_canonical_artifact"
PROCESS_ROUTE_MODEL_BLOCK_ALIAS_FLAGS_DIVERGE = "process_route_model_block_alias_flags_diverge"

VALID_SCENARIOS = (
    VALID_IDENTITY_CARD_ACK_ONLY,
    VALID_PM_ROLE_WORK_PACKET_RESULT,
    VALID_DIRECT_ROUTER_WAIT_EVENT,
    VALID_ROUTER_REGISTERED_TASK_CARD_RESULT,
    VALID_ACTIVE_HOLDER_PACKET_RESULT,
    VALID_FIXED_EVENT_CONTRACT,
    VALID_CURRENT_GATE_EVENT_SATISFIES_FLAG,
    VALID_PM_ROLE_WORK_RESULT_MAPPED_TO_CURRENT_GATE,
    VALID_PRODUCT_BEHAVIOR_MODEL_SUBMISSION_WITH_COMPAT_ALIAS,
    VALID_PROCESS_ROUTE_MODEL_SUBMISSION_WITH_COMPAT_ALIAS,
)
NEGATIVE_SCENARIOS = (
    SYSTEM_CARD_ONLY_ROUTER_SUPPLIED_REPORT,
    TASK_CARD_WITHOUT_WORK_AUTHORITY,
    IDENTITY_CARD_CARRIES_HIDDEN_WORK,
    ROLE_GUESSES_UNKNOWN_EVENT,
    REGISTERED_EVENT_NOT_CURRENTLY_ALLOWED,
    MECHANICAL_GREEN_USED_AS_ROUTER_ACCEPTANCE,
    STATIC_CARD_GUIDANCE_USED_AS_DYNAMIC_LEASE,
    LEGACY_DIRECT_EVENT_COMPETES_WITH_PM_PACKET,
    PM_ROLE_WORK_WRONG_RECIPIENT,
    WRONG_ROLE_USES_WORK_AUTHORITY,
    WRONG_CONTRACT_USES_WORK_AUTHORITY,
    STALE_WORK_AUTHORITY_USED,
    GATE_CARD_WITHOUT_COMPLETION_CONTRACT,
    LEGACY_EVENT_ACCEPTED_WITHOUT_REQUIRED_GATE_FLAG,
    PM_REPAIR_RESOLVES_BLOCKER_WITHOUT_GATE_EVENT,
    PM_ROLE_WORK_RESULT_NOT_MAPPED_TO_CURRENT_GATE,
    PRODUCT_BEHAVIOR_MODEL_GATE_USES_MODELABILITY_AS_CANONICAL_COMPLETION,
    PRODUCT_BEHAVIOR_MODEL_ALIAS_DOES_NOT_SET_COMPATIBILITY_FLAGS,
    PRODUCT_BEHAVIOR_MODEL_SUBMISSION_SKIPS_PM_ACCEPTANCE,
    PRODUCT_BEHAVIOR_MODEL_MISSING_CANONICAL_ARTIFACT,
    PRODUCT_BEHAVIOR_MODEL_BLOCK_ALIAS_FLAGS_DIVERGE,
    PROCESS_ROUTE_MODEL_GATE_USES_ROUTE_CHECK_AS_CANONICAL_COMPLETION,
    PROCESS_ROUTE_MODEL_ALIAS_DOES_NOT_SET_COMPATIBILITY_FLAGS,
    PROCESS_ROUTE_MODEL_SUBMISSION_SKIPS_PM_ACCEPTANCE,
    PROCESS_ROUTE_MODEL_MISSING_CANONICAL_ARTIFACT,
    PROCESS_ROUTE_MODEL_BLOCK_ALIAS_FLAGS_DIVERGE,
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS

ASSIGNMENT_SYSTEM_CARD = "system_card"
ASSIGNMENT_IDENTITY_CARD = "identity_card"
ASSIGNMENT_TASK_CARD = "task_card"
ASSIGNMENT_PM_ROLE_WORK_PACKET = "pm_role_work_packet"
ASSIGNMENT_DIRECT_ROUTER_WAIT = "direct_router_wait"
ASSIGNMENT_ACTIVE_HOLDER_LEASE = "active_holder_lease"

EVENT_MODE_FIXED = "fixed"
EVENT_MODE_ROUTER_SUPPLIED = "router_supplied"

EVENT_SOURCE_NONE = "none"
EVENT_SOURCE_FIXED_CONTRACT = "fixed_contract"
EVENT_SOURCE_CURRENT_ROUTER_WAIT = "current_router_wait"
EVENT_SOURCE_PM_PACKET_RESULT_CONTRACT = "pm_packet_result_contract"
EVENT_SOURCE_ROUTER_REGISTERED_TASK_AUTHORITY = "router_registered_task_authority"
EVENT_SOURCE_ACTIVE_HOLDER_LEASE = "active_holder_lease"
EVENT_SOURCE_ROLE_GUESS = "role_guess"
EVENT_SOURCE_STATIC_CARD_TEXT = "static_card_text"

PRODUCT_BEHAVIOR_MODEL_CANONICAL_GATE_EVENTS = frozenset(
    {
        "product_officer_submits_product_behavior_model",
        "product_officer_blocks_product_behavior_model",
    }
)
PRODUCT_BEHAVIOR_MODEL_COMPATIBILITY_GATE_EVENTS = frozenset(
    {
        "product_officer_passes_product_architecture_modelability",
        "product_officer_blocks_product_architecture_modelability",
    }
)
PRODUCT_BEHAVIOR_MODEL_GATE_EVENTS = (
    PRODUCT_BEHAVIOR_MODEL_CANONICAL_GATE_EVENTS | PRODUCT_BEHAVIOR_MODEL_COMPATIBILITY_GATE_EVENTS
)
PRODUCT_ARCHITECTURE_GATE_EVENTS = PRODUCT_BEHAVIOR_MODEL_GATE_EVENTS
PRODUCT_ARCHITECTURE_LEGACY_EVENTS = frozenset({"product_officer_model_report"})
PROCESS_ROUTE_MODEL_CANONICAL_GATE_EVENTS = frozenset(
    {
        "process_officer_submits_process_route_model",
        "process_officer_requests_process_route_model_repair",
        "process_officer_blocks_process_route_model",
    }
)
PROCESS_ROUTE_MODEL_COMPATIBILITY_GATE_EVENTS = frozenset(
    {
        "process_officer_passes_route_check",
        "process_officer_requires_route_repair",
        "process_officer_blocks_route_check",
    }
)
PROCESS_ROUTE_MODEL_GATE_EVENTS = PROCESS_ROUTE_MODEL_CANONICAL_GATE_EVENTS | PROCESS_ROUTE_MODEL_COMPATIBILITY_GATE_EVENTS


@dataclass(frozen=True)
class Tick:
    """One dynamic return-path transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"

    assignment_surface: str = ASSIGNMENT_SYSTEM_CARD
    output_contract_id: str = "officer_model_report"
    output_type: str = "officer_model_report"
    contract_event_mode: str = EVENT_MODE_ROUTER_SUPPLIED

    formal_output_requested: bool = True
    identity_ack_only: bool = False
    task_like_card: bool = False
    router_registered_work_authority_present: bool = False
    authority_role_matches: bool = True
    authority_contract_matches: bool = True
    authority_recipient_matches: bool = True
    authority_route_frontier_fresh: bool = True
    required_result_next_recipient: str = "project_manager"

    static_card_guidance_present: bool = False
    mechanical_role_output_valid: bool = False
    semantic_report_meaningful: bool = False

    concrete_return_event_present: bool = False
    return_event_source: str = EVENT_SOURCE_NONE
    return_event_name: str = "none"
    return_event_registered: bool = False
    return_event_currently_allowed: bool = False

    pm_role_work_packet_present: bool = False
    pm_role_work_result_contract_present: bool = False
    pm_role_work_result_maps_to_current_gate: bool = True
    direct_router_wait_present: bool = False
    legacy_direct_event_present: bool = False

    current_gate_active: bool = False
    current_gate_name: str = "none"
    current_gate_completion_contract_declared: bool = True
    current_gate_required_flag: str = "none"
    return_event_satisfies_current_gate: bool = True
    current_gate_flag_satisfied: bool = True
    control_blocker_resolved: bool = False
    repair_followup_event_satisfies_current_gate: bool = True
    compatibility_alias_sets_required_flags: bool = True
    pm_acceptance_required_after_submission: bool = False
    pm_acceptance_completed: bool = True
    downstream_product_flow_allowed: bool = False
    canonical_product_behavior_model_artifact_written: bool = True
    compatibility_product_model_artifact_written: bool = True
    block_alias_flags_aligned: bool = True
    process_compatibility_alias_sets_required_flags: bool = True
    pm_process_acceptance_required_after_submission: bool = False
    pm_process_acceptance_completed: bool = True
    downstream_route_challenge_flow_allowed: bool = False
    canonical_process_route_model_artifact_written: bool = True
    compatibility_process_route_check_artifact_written: bool = True
    process_block_alias_flags_aligned: bool = True

    router_accepted_event: bool = False
    current_run_allowed_to_continue: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _scenario_state(scenario: str) -> State:
    if scenario == VALID_IDENTITY_CARD_ACK_ONLY:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_IDENTITY_CARD,
            contract_event_mode=EVENT_MODE_FIXED,
            formal_output_requested=False,
            identity_ack_only=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=False,
            semantic_report_meaningful=False,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_FIXED_CONTRACT,
            return_event_name="role_card_acknowledged",
            return_event_registered=True,
            return_event_currently_allowed=True,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == VALID_CURRENT_GATE_EVENT_SATISFIES_FLAG:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_DIRECT_ROUTER_WAIT,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_CURRENT_ROUTER_WAIT,
            return_event_name="product_officer_submits_product_behavior_model",
            return_event_registered=True,
            return_event_currently_allowed=True,
            direct_router_wait_present=True,
            current_gate_active=True,
            current_gate_name="product_behavior_model",
            current_gate_required_flag="product_behavior_model_submitted",
            return_event_satisfies_current_gate=True,
            current_gate_flag_satisfied=True,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == VALID_PM_ROLE_WORK_RESULT_MAPPED_TO_CURRENT_GATE:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_PM_ROLE_WORK_PACKET,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_PM_PACKET_RESULT_CONTRACT,
            return_event_name="product_officer_submits_product_behavior_model",
            return_event_registered=True,
            return_event_currently_allowed=True,
            pm_role_work_packet_present=True,
            pm_role_work_result_contract_present=True,
            pm_role_work_result_maps_to_current_gate=True,
            current_gate_active=True,
            current_gate_name="product_behavior_model",
            current_gate_required_flag="product_behavior_model_submitted",
            return_event_satisfies_current_gate=True,
            current_gate_flag_satisfied=True,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == VALID_PRODUCT_BEHAVIOR_MODEL_SUBMISSION_WITH_COMPAT_ALIAS:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_DIRECT_ROUTER_WAIT,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_CURRENT_ROUTER_WAIT,
            return_event_name="product_officer_submits_product_behavior_model",
            return_event_registered=True,
            return_event_currently_allowed=True,
            direct_router_wait_present=True,
            current_gate_active=True,
            current_gate_name="product_behavior_model",
            current_gate_required_flag="product_behavior_model_submitted",
            return_event_satisfies_current_gate=True,
            current_gate_flag_satisfied=True,
            compatibility_alias_sets_required_flags=True,
            pm_acceptance_required_after_submission=True,
            pm_acceptance_completed=False,
            downstream_product_flow_allowed=False,
            canonical_product_behavior_model_artifact_written=True,
            compatibility_product_model_artifact_written=True,
            block_alias_flags_aligned=True,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == VALID_PROCESS_ROUTE_MODEL_SUBMISSION_WITH_COMPAT_ALIAS:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_DIRECT_ROUTER_WAIT,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_CURRENT_ROUTER_WAIT,
            return_event_name="process_officer_submits_process_route_model",
            return_event_registered=True,
            return_event_currently_allowed=True,
            direct_router_wait_present=True,
            current_gate_active=True,
            current_gate_name="process_route_model",
            current_gate_required_flag="process_route_model_submitted",
            return_event_satisfies_current_gate=True,
            current_gate_flag_satisfied=True,
            process_compatibility_alias_sets_required_flags=True,
            pm_process_acceptance_required_after_submission=True,
            pm_process_acceptance_completed=False,
            downstream_route_challenge_flow_allowed=False,
            canonical_process_route_model_artifact_written=True,
            compatibility_process_route_check_artifact_written=True,
            process_block_alias_flags_aligned=True,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == VALID_PM_ROLE_WORK_PACKET_RESULT:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_PM_ROLE_WORK_PACKET,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_PM_PACKET_RESULT_CONTRACT,
            return_event_name="pm_records_role_work_result_decision",
            return_event_registered=True,
            return_event_currently_allowed=True,
            pm_role_work_packet_present=True,
            pm_role_work_result_contract_present=True,
            required_result_next_recipient="project_manager",
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == VALID_DIRECT_ROUTER_WAIT_EVENT:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_DIRECT_ROUTER_WAIT,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_CURRENT_ROUTER_WAIT,
            return_event_name="product_officer_blocks_product_architecture_modelability",
            return_event_registered=True,
            return_event_currently_allowed=True,
            direct_router_wait_present=True,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == VALID_ROUTER_REGISTERED_TASK_CARD_RESULT:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_TASK_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            task_like_card=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_ROUTER_REGISTERED_TASK_AUTHORITY,
            return_event_name="current_node_reviewer_passes_result",
            return_event_registered=True,
            return_event_currently_allowed=True,
            direct_router_wait_present=True,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == VALID_ACTIVE_HOLDER_PACKET_RESULT:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_ACTIVE_HOLDER_LEASE,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            task_like_card=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_ACTIVE_HOLDER_LEASE,
            return_event_name="active_holder_result_mechanics_passed",
            return_event_registered=True,
            return_event_currently_allowed=True,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == VALID_FIXED_EVENT_CONTRACT:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_SYSTEM_CARD,
            contract_event_mode=EVENT_MODE_FIXED,
            formal_output_requested=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_FIXED_CONTRACT,
            return_event_name="pm_registers_role_work_request",
            return_event_registered=True,
            return_event_currently_allowed=True,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == SYSTEM_CARD_ONLY_ROUTER_SUPPLIED_REPORT:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_SYSTEM_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=False,
            return_event_source=EVENT_SOURCE_NONE,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == TASK_CARD_WITHOUT_WORK_AUTHORITY:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_TASK_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            task_like_card=True,
            router_registered_work_authority_present=False,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=False,
            return_event_source=EVENT_SOURCE_NONE,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == IDENTITY_CARD_CARRIES_HIDDEN_WORK:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_IDENTITY_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            identity_ack_only=True,
            task_like_card=True,
            router_registered_work_authority_present=False,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=False,
            return_event_source=EVENT_SOURCE_NONE,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == ROLE_GUESSES_UNKNOWN_EVENT:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_SYSTEM_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_ROLE_GUESS,
            return_event_name="product_officer_model_report",
            return_event_registered=False,
            return_event_currently_allowed=False,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == REGISTERED_EVENT_NOT_CURRENTLY_ALLOWED:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_SYSTEM_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_ROLE_GUESS,
            return_event_name="product_officer_blocks_product_architecture_modelability",
            return_event_registered=True,
            return_event_currently_allowed=False,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == MECHANICAL_GREEN_USED_AS_ROUTER_ACCEPTANCE:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_SYSTEM_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_ROLE_GUESS,
            return_event_name="product_officer_blocks_product_architecture_modelability",
            return_event_registered=True,
            return_event_currently_allowed=False,
            router_accepted_event=False,
            current_run_allowed_to_continue=True,
        )
    if scenario == STATIC_CARD_GUIDANCE_USED_AS_DYNAMIC_LEASE:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_SYSTEM_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=False,
            semantic_report_meaningful=False,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_STATIC_CARD_TEXT,
            return_event_name="use_router_supplied_event_name",
            return_event_registered=False,
            return_event_currently_allowed=False,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == LEGACY_DIRECT_EVENT_COMPETES_WITH_PM_PACKET:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_SYSTEM_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_ROLE_GUESS,
            return_event_name="product_officer_blocks_product_architecture_modelability",
            return_event_registered=True,
            return_event_currently_allowed=False,
            pm_role_work_packet_present=True,
            pm_role_work_result_contract_present=True,
            legacy_direct_event_present=True,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == PM_ROLE_WORK_WRONG_RECIPIENT:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_PM_ROLE_WORK_PACKET,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_PM_PACKET_RESULT_CONTRACT,
            return_event_name="pm_records_role_work_result_decision",
            return_event_registered=True,
            return_event_currently_allowed=True,
            pm_role_work_packet_present=True,
            pm_role_work_result_contract_present=True,
            required_result_next_recipient="human_like_reviewer",
            authority_recipient_matches=False,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == WRONG_ROLE_USES_WORK_AUTHORITY:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_TASK_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            task_like_card=True,
            router_registered_work_authority_present=True,
            authority_role_matches=False,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_ROUTER_REGISTERED_TASK_AUTHORITY,
            return_event_name="current_node_reviewer_passes_result",
            return_event_registered=True,
            return_event_currently_allowed=True,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == WRONG_CONTRACT_USES_WORK_AUTHORITY:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_TASK_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            task_like_card=True,
            router_registered_work_authority_present=True,
            authority_contract_matches=False,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_ROUTER_REGISTERED_TASK_AUTHORITY,
            return_event_name="current_node_reviewer_passes_result",
            return_event_registered=True,
            return_event_currently_allowed=True,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == STALE_WORK_AUTHORITY_USED:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_ACTIVE_HOLDER_LEASE,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            task_like_card=True,
            router_registered_work_authority_present=True,
            authority_route_frontier_fresh=False,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_ACTIVE_HOLDER_LEASE,
            return_event_name="active_holder_result_mechanics_passed",
            return_event_registered=True,
            return_event_currently_allowed=True,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == GATE_CARD_WITHOUT_COMPLETION_CONTRACT:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_SYSTEM_CARD,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=False,
            semantic_report_meaningful=False,
            concrete_return_event_present=False,
            current_gate_active=True,
            current_gate_name="product_architecture_modelability",
            current_gate_completion_contract_declared=False,
            current_gate_required_flag="product_architecture_modelability_passed",
            return_event_satisfies_current_gate=False,
            current_gate_flag_satisfied=False,
            router_accepted_event=False,
            current_run_allowed_to_continue=False,
        )
    if scenario == LEGACY_EVENT_ACCEPTED_WITHOUT_REQUIRED_GATE_FLAG:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_DIRECT_ROUTER_WAIT,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_CURRENT_ROUTER_WAIT,
            return_event_name="product_officer_model_report",
            return_event_registered=True,
            return_event_currently_allowed=True,
            direct_router_wait_present=True,
            current_gate_active=True,
            current_gate_name="product_architecture_modelability",
            current_gate_required_flag="product_architecture_modelability_passed",
            return_event_satisfies_current_gate=False,
            current_gate_flag_satisfied=False,
            legacy_direct_event_present=True,
            router_accepted_event=True,
            current_run_allowed_to_continue=False,
        )
    if scenario == PM_REPAIR_RESOLVES_BLOCKER_WITHOUT_GATE_EVENT:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_PM_ROLE_WORK_PACKET,
            contract_event_mode=EVENT_MODE_FIXED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_FIXED_CONTRACT,
            return_event_name="pm_registers_role_work_request",
            return_event_registered=True,
            return_event_currently_allowed=True,
            pm_role_work_packet_present=True,
            current_gate_active=True,
            current_gate_name="product_architecture_modelability",
            current_gate_required_flag="product_architecture_modelability_passed",
            return_event_satisfies_current_gate=False,
            current_gate_flag_satisfied=False,
            control_blocker_resolved=True,
            repair_followup_event_satisfies_current_gate=False,
            router_accepted_event=True,
            current_run_allowed_to_continue=False,
        )
    if scenario == PM_ROLE_WORK_RESULT_NOT_MAPPED_TO_CURRENT_GATE:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_PM_ROLE_WORK_PACKET,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_PM_PACKET_RESULT_CONTRACT,
            return_event_name="pm_records_role_work_result_decision",
            return_event_registered=True,
            return_event_currently_allowed=True,
            pm_role_work_packet_present=True,
            pm_role_work_result_contract_present=True,
            pm_role_work_result_maps_to_current_gate=False,
            current_gate_active=True,
            current_gate_name="product_architecture_modelability",
            current_gate_required_flag="product_architecture_modelability_passed",
            return_event_satisfies_current_gate=False,
            current_gate_flag_satisfied=False,
            router_accepted_event=True,
            current_run_allowed_to_continue=False,
        )
    if scenario == PRODUCT_BEHAVIOR_MODEL_GATE_USES_MODELABILITY_AS_CANONICAL_COMPLETION:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_DIRECT_ROUTER_WAIT,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_CURRENT_ROUTER_WAIT,
            return_event_name="product_officer_passes_product_architecture_modelability",
            return_event_registered=True,
            return_event_currently_allowed=True,
            current_gate_active=True,
            current_gate_name="product_architecture_modelability",
            current_gate_required_flag="product_architecture_modelability_passed",
            return_event_satisfies_current_gate=True,
            current_gate_flag_satisfied=True,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == PRODUCT_BEHAVIOR_MODEL_ALIAS_DOES_NOT_SET_COMPATIBILITY_FLAGS:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_DIRECT_ROUTER_WAIT,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_CURRENT_ROUTER_WAIT,
            return_event_name="product_officer_submits_product_behavior_model",
            return_event_registered=True,
            return_event_currently_allowed=True,
            current_gate_active=True,
            current_gate_name="product_behavior_model",
            current_gate_required_flag="product_behavior_model_submitted",
            return_event_satisfies_current_gate=True,
            current_gate_flag_satisfied=True,
            compatibility_alias_sets_required_flags=False,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == PRODUCT_BEHAVIOR_MODEL_SUBMISSION_SKIPS_PM_ACCEPTANCE:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_DIRECT_ROUTER_WAIT,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_CURRENT_ROUTER_WAIT,
            return_event_name="product_officer_submits_product_behavior_model",
            return_event_registered=True,
            return_event_currently_allowed=True,
            current_gate_active=True,
            current_gate_name="product_behavior_model",
            current_gate_required_flag="product_behavior_model_submitted",
            return_event_satisfies_current_gate=True,
            current_gate_flag_satisfied=True,
            pm_acceptance_required_after_submission=True,
            pm_acceptance_completed=False,
            downstream_product_flow_allowed=True,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == PRODUCT_BEHAVIOR_MODEL_MISSING_CANONICAL_ARTIFACT:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_DIRECT_ROUTER_WAIT,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_CURRENT_ROUTER_WAIT,
            return_event_name="product_officer_submits_product_behavior_model",
            return_event_registered=True,
            return_event_currently_allowed=True,
            current_gate_active=True,
            current_gate_name="product_behavior_model",
            current_gate_required_flag="product_behavior_model_submitted",
            return_event_satisfies_current_gate=True,
            current_gate_flag_satisfied=True,
            canonical_product_behavior_model_artifact_written=False,
            compatibility_product_model_artifact_written=True,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == PRODUCT_BEHAVIOR_MODEL_BLOCK_ALIAS_FLAGS_DIVERGE:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_DIRECT_ROUTER_WAIT,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_CURRENT_ROUTER_WAIT,
            return_event_name="product_officer_blocks_product_behavior_model",
            return_event_registered=True,
            return_event_currently_allowed=True,
            current_gate_active=True,
            current_gate_name="product_behavior_model",
            current_gate_required_flag="product_behavior_model_blocked",
            return_event_satisfies_current_gate=True,
            current_gate_flag_satisfied=True,
            block_alias_flags_aligned=False,
            router_accepted_event=True,
            current_run_allowed_to_continue=False,
        )
    if scenario == PROCESS_ROUTE_MODEL_GATE_USES_ROUTE_CHECK_AS_CANONICAL_COMPLETION:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_DIRECT_ROUTER_WAIT,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_CURRENT_ROUTER_WAIT,
            return_event_name="process_officer_passes_route_check",
            return_event_registered=True,
            return_event_currently_allowed=True,
            current_gate_active=True,
            current_gate_name="route_process_check",
            current_gate_required_flag="process_officer_route_check_passed",
            return_event_satisfies_current_gate=True,
            current_gate_flag_satisfied=True,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == PROCESS_ROUTE_MODEL_ALIAS_DOES_NOT_SET_COMPATIBILITY_FLAGS:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_DIRECT_ROUTER_WAIT,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_CURRENT_ROUTER_WAIT,
            return_event_name="process_officer_submits_process_route_model",
            return_event_registered=True,
            return_event_currently_allowed=True,
            current_gate_active=True,
            current_gate_name="process_route_model",
            current_gate_required_flag="process_route_model_submitted",
            return_event_satisfies_current_gate=True,
            current_gate_flag_satisfied=True,
            process_compatibility_alias_sets_required_flags=False,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == PROCESS_ROUTE_MODEL_SUBMISSION_SKIPS_PM_ACCEPTANCE:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_DIRECT_ROUTER_WAIT,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_CURRENT_ROUTER_WAIT,
            return_event_name="process_officer_submits_process_route_model",
            return_event_registered=True,
            return_event_currently_allowed=True,
            current_gate_active=True,
            current_gate_name="process_route_model",
            current_gate_required_flag="process_route_model_submitted",
            return_event_satisfies_current_gate=True,
            current_gate_flag_satisfied=True,
            pm_process_acceptance_required_after_submission=True,
            pm_process_acceptance_completed=False,
            downstream_route_challenge_flow_allowed=True,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == PROCESS_ROUTE_MODEL_MISSING_CANONICAL_ARTIFACT:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_DIRECT_ROUTER_WAIT,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_CURRENT_ROUTER_WAIT,
            return_event_name="process_officer_submits_process_route_model",
            return_event_registered=True,
            return_event_currently_allowed=True,
            current_gate_active=True,
            current_gate_name="process_route_model",
            current_gate_required_flag="process_route_model_submitted",
            return_event_satisfies_current_gate=True,
            current_gate_flag_satisfied=True,
            canonical_process_route_model_artifact_written=False,
            compatibility_process_route_check_artifact_written=True,
            router_accepted_event=True,
            current_run_allowed_to_continue=True,
        )
    if scenario == PROCESS_ROUTE_MODEL_BLOCK_ALIAS_FLAGS_DIVERGE:
        return State(
            status="running",
            scenario=scenario,
            assignment_surface=ASSIGNMENT_DIRECT_ROUTER_WAIT,
            contract_event_mode=EVENT_MODE_ROUTER_SUPPLIED,
            formal_output_requested=True,
            router_registered_work_authority_present=True,
            static_card_guidance_present=True,
            mechanical_role_output_valid=True,
            semantic_report_meaningful=True,
            concrete_return_event_present=True,
            return_event_source=EVENT_SOURCE_CURRENT_ROUTER_WAIT,
            return_event_name="process_officer_blocks_process_route_model",
            return_event_registered=True,
            return_event_currently_allowed=True,
            current_gate_active=True,
            current_gate_name="process_route_model",
            current_gate_required_flag="process_route_model_blocked",
            return_event_satisfies_current_gate=True,
            current_gate_flag_satisfied=True,
            process_block_alias_flags_aligned=False,
            router_accepted_event=True,
            current_run_allowed_to_continue=False,
        )
    raise ValueError(f"Unknown scenario: {scenario}")


def return_path_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "new":
        return failures

    if state.identity_ack_only and state.formal_output_requested:
        failures.append("identity card carried hidden formal work")
    if state.task_like_card and state.formal_output_requested and not state.router_registered_work_authority_present:
        failures.append("task-like card lacks Router-registered work authority")
    if state.formal_output_requested and state.router_registered_work_authority_present:
        if not state.authority_role_matches:
            failures.append("work authority role does not match submitting role")
        if not state.authority_contract_matches:
            failures.append("work authority contract does not match submitted output")
        if not state.authority_recipient_matches:
            failures.append("work authority recipient does not match required recipient")
        if not state.authority_route_frontier_fresh:
            failures.append("work authority route or frontier is stale")
    if state.pm_role_work_packet_present and state.required_result_next_recipient != "project_manager":
        failures.append("PM role-work result does not return to project_manager")

    if not state.formal_output_requested:
        if state.router_accepted_event and not state.return_event_currently_allowed:
            failures.append("Router accepted an ACK event that was not currently allowed")
        return failures

    if state.contract_event_mode == EVENT_MODE_ROUTER_SUPPLIED:
        if not state.concrete_return_event_present:
            failures.append("router-supplied contract has no concrete return event")
        if state.return_event_source not in {
            EVENT_SOURCE_CURRENT_ROUTER_WAIT,
            EVENT_SOURCE_PM_PACKET_RESULT_CONTRACT,
            EVENT_SOURCE_ROUTER_REGISTERED_TASK_AUTHORITY,
            EVENT_SOURCE_ACTIVE_HOLDER_LEASE,
        }:
            failures.append("router-supplied return event was not supplied by current Router wait, PM packet, or registered work authority")
        if state.assignment_surface == ASSIGNMENT_SYSTEM_CARD:
            failures.append("system card alone cannot authorize formal router-supplied output")

    if state.return_event_source == EVENT_SOURCE_ROLE_GUESS:
        failures.append("role guessed a formal return event")
    if state.return_event_source == EVENT_SOURCE_STATIC_CARD_TEXT:
        failures.append("static card text was treated as a dynamic event lease")
    if state.concrete_return_event_present and not state.return_event_registered:
        failures.append("formal return event is not registered")
    if state.concrete_return_event_present and not state.return_event_currently_allowed:
        failures.append("formal return event is not currently allowed by Router wait state")
    if state.router_accepted_event and not state.return_event_currently_allowed:
        failures.append("Router accepted an event that was not currently allowed")
    if state.mechanical_role_output_valid and state.current_run_allowed_to_continue and not state.router_accepted_event:
        failures.append("mechanical role-output validation was treated as Router acceptance")
    if state.legacy_direct_event_present and state.pm_role_work_packet_present:
        failures.append("legacy direct officer event competes with PM role-work result contract")
    if state.pm_role_work_packet_present and not state.pm_role_work_result_contract_present:
        failures.append("PM role-work packet has no result contract")
    if state.current_gate_active:
        if state.current_gate_name == "product_architecture_modelability":
            failures.append("product behavior model gate used modelability as canonical completion")
        if state.current_gate_name == "route_process_check":
            failures.append("process route model gate used route process check as canonical completion")
        if not state.current_gate_completion_contract_declared:
            failures.append("current gate card lacks a declared completion contract")
        if state.router_accepted_event and not state.return_event_satisfies_current_gate:
            failures.append("Router accepted an event that did not satisfy the current gate")
        if state.current_run_allowed_to_continue and not state.current_gate_flag_satisfied:
            failures.append("current run continued before the current gate flag was satisfied")
        if (
            state.control_blocker_resolved
            and not state.repair_followup_event_satisfies_current_gate
            and not state.current_gate_flag_satisfied
        ):
            failures.append("control blocker was resolved without satisfying the current gate")
        if (
            state.pm_role_work_packet_present
            and state.pm_role_work_result_contract_present
            and not state.pm_role_work_result_maps_to_current_gate
            and not state.current_gate_flag_satisfied
        ):
            failures.append("PM role-work result was not mapped to the current gate")
        if not state.compatibility_alias_sets_required_flags:
            failures.append("product behavior model compatibility alias did not set required flags")
        if (
            state.downstream_product_flow_allowed
            and state.pm_acceptance_required_after_submission
            and not state.pm_acceptance_completed
        ):
            failures.append("product behavior model submission allowed downstream flow before PM acceptance")
        if state.return_event_satisfies_current_gate and not state.canonical_product_behavior_model_artifact_written:
            failures.append("product behavior model submission did not write canonical artifact")
        if not state.compatibility_product_model_artifact_written:
            failures.append("product behavior model submission did not write compatibility artifact")
        if not state.block_alias_flags_aligned:
            failures.append("product behavior model block alias flags diverged")
        if not state.process_compatibility_alias_sets_required_flags:
            failures.append("process route model compatibility alias did not set required flags")
        if (
            state.downstream_route_challenge_flow_allowed
            and state.pm_process_acceptance_required_after_submission
            and not state.pm_process_acceptance_completed
        ):
            failures.append("process route model submission allowed downstream flow before PM acceptance")
        if state.return_event_satisfies_current_gate and not state.canonical_process_route_model_artifact_written:
            failures.append("process route model submission did not write canonical artifact")
        if not state.compatibility_process_route_check_artifact_written:
            failures.append("process route model submission did not write compatibility artifact")
        if not state.process_block_alias_flags_aligned:
            failures.append("process route model block alias flags diverged")
    return failures


class DynamicReturnPathStep:
    """Model one FlowPilot role-output return path decision.

    Input x State -> Set(Output x State)
    reads: task assignment surface, output contract event mode, role-output
    runtime validation, current Router wait, PM role-work packet result contract
    writes: accepted/rejected dynamic return-path classification
    idempotency: repeated analysis of the same output attempt must produce the
    same blocked/accepted classification.
    """

    name = "DynamicReturnPathStep"
    input_description = "dynamic return-path authority tick"
    output_description = "one return-path authority classification"
    reads = (
        "task_assignment_surface",
        "output_contract_index",
        "role_output_runtime_result",
        "current_router_wait_state",
        "pm_role_work_packet_result_contract",
    )
    writes = ("dynamic_return_path_classification",)
    idempotency = "classification is derived from immutable event and packet facts"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _scenario_state(scenario))
        return
    failures = return_path_failures(state)
    if failures:
        yield Transition(
            f"reject_{state.scenario}",
            replace(state, status="rejected", terminal_reason="; ".join(failures)),
        )
        return
    yield Transition(
        f"accept_{state.scenario}",
        replace(state, status="accepted", terminal_reason="dynamic_return_path_ok"),
    )


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and not return_path_failures(state)


def accepted_states_are_safe(state: State, trace) -> InvariantResult:
    del trace
    failures = return_path_failures(state)
    if state.status == "accepted" and failures:
        return InvariantResult.fail("unsafe dynamic return path was accepted")
    if state.status == "rejected" and not failures:
        return InvariantResult.fail("safe dynamic return path was rejected")
    return InvariantResult.pass_()


def router_supplied_outputs_have_runtime_lease(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted" or state.contract_event_mode != EVENT_MODE_ROUTER_SUPPLIED:
        return InvariantResult.pass_()
    if state.return_event_source not in {
        EVENT_SOURCE_CURRENT_ROUTER_WAIT,
        EVENT_SOURCE_PM_PACKET_RESULT_CONTRACT,
        EVENT_SOURCE_ROUTER_REGISTERED_TASK_AUTHORITY,
        EVENT_SOURCE_ACTIVE_HOLDER_LEASE,
    }:
        return InvariantResult.fail("accepted router-supplied output without runtime lease")
    return InvariantResult.pass_()


def mechanical_green_does_not_imply_continuation(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.current_run_allowed_to_continue and not state.router_accepted_event:
        return InvariantResult.fail("accepted continuation without Router acceptance")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepted_states_are_safe",
        description="Only safe dynamic return paths can be accepted.",
        predicate=accepted_states_are_safe,
    ),
    Invariant(
        name="router_supplied_outputs_have_runtime_lease",
        description="Router-supplied output contracts require a concrete runtime lease.",
        predicate=router_supplied_outputs_have_runtime_lease,
    ),
    Invariant(
        name="mechanical_green_does_not_imply_continuation",
        description="Role-output format validation cannot imply current-run continuation.",
        predicate=mechanical_green_does_not_imply_continuation,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def build_workflow() -> Workflow:
    return Workflow((DynamicReturnPathStep(),), name="flowpilot_dynamic_return_path")


def terminal_predicate(_input_obj, state: State, _trace) -> bool:
    return is_terminal(state)


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _iter_json_files(root: Path, pattern: str) -> Iterable[tuple[Path, dict]]:
    if not root.exists():
        return
    for path in sorted(root.glob(pattern)):
        if path.is_file():
            yield path, _read_json(path)


def router_supplied_contracts(project_root: Path) -> dict[str, dict]:
    index_path = project_root / "skills" / "flowpilot" / "assets" / "runtime_kit" / "contracts" / "contract_index.json"
    data = _read_json(index_path)
    contracts: dict[str, dict] = {}
    for item in data.get("contracts", []):
        if item.get("runtime_channel") == "role_output_runtime" and item.get("router_event_mode") == "router_supplied":
            contracts[item.get("contract_id", "")] = item
    return contracts


def project_live_run_projection(project_root: Path) -> dict[str, object]:
    current = _read_json(project_root / ".flowpilot" / "current.json")
    run_root_value = current.get("current_run_root")
    run_root = project_root / run_root_value if run_root_value else None
    contracts = router_supplied_contracts(project_root)
    contract_ids = set(contracts)
    output_types = {item.get("output_type") for item in contracts.values()}
    output_types.discard(None)

    projection: dict[str, object] = {
        "ok": True,
        "current_run_id": current.get("current_run_id"),
        "current_run_root": run_root_value,
        "router_supplied_contracts": sorted(contract_ids),
        "current_findings": [],
        "historical_gate_alignment_findings": [],
        "risk_surfaces": [],
        "mitigated_paths": [],
        "current_run_can_continue": True,
        "classification": "no_active_dynamic_return_path_findings",
    }
    if not run_root or not run_root.exists():
        projection["ok"] = False
        projection["classification"] = "current_run_missing"
        projection["current_run_can_continue"] = False
        return projection

    sessions: dict[str, dict] = {}
    for path, data in _iter_json_files(run_root / "role_output_sessions", "*.json"):
        contract_id = data.get("output_contract_id") or data.get("contract_id")
        output_type = data.get("output_type")
        event_name = data.get("event_name")
        if contract_id in contract_ids or output_type in output_types:
            sessions[str(event_name)] = {
                "path": str(path.relative_to(project_root)),
                "contract_id": contract_id,
                "output_type": output_type,
                "from_role": data.get("from_role"),
                "event_name": event_name,
            }

    router_state = _read_json(run_root / "router_state.json")
    flags = router_state.get("flags", {}) if isinstance(router_state, dict) else {}

    for path, data in _iter_json_files(run_root / "mailbox" / "system_cards", "*.json"):
        if data.get("card_id") != "product_officer.product_architecture_modelability":
            continue
        payload_contract = data.get("payload_contract")
        next_step_contract = data.get("next_step_contract")
        declared_completion = bool(payload_contract) or (
            isinstance(next_step_contract, dict)
            and bool(next_step_contract.get("allowed_external_events") or next_step_contract.get("postcondition"))
        )
        if not declared_completion:
            projection["risk_surfaces"].append(
                {
                    "kind": "gate_card_without_declared_completion_contract",
                    "card_id": data.get("card_id"),
                    "card_envelope": str(path.relative_to(project_root)),
                    "model_meaning": (
                        "A gate-bearing system card was delivered without a metadata-level completion "
                        "contract that names the concrete Router event or gate flag it must satisfy."
                    ),
                }
            )

    for path, data in _iter_json_files(run_root / "control_blocks", "control-blocker-*.json"):
        if ".sealed_repair_packet" in path.name:
            continue
        error_code = str(data.get("error_code") or "")
        event = data.get("originating_event")
        if not event:
            event = data.get("event_name")
        rejected_router_supplied_output = event in sessions and (
            "unknown_external_event" in error_code or "not_currently_allowed" in error_code
        )
        if rejected_router_supplied_output:
            session = sessions[str(event)]
            projection["current_findings"].append(
                {
                    "kind": "rejected_router_supplied_role_output",
                    "event_name": event,
                    "error_code": error_code,
                    "role_output_session": session["path"],
                    "control_blocker": str(path.relative_to(project_root)),
                    "contract_id": session.get("contract_id"),
                    "output_type": session.get("output_type"),
                    "from_role": session.get("from_role"),
                    "model_meaning": (
                        "The report may be semantically useful, but the formal return path was not "
                        "authorized by the current Router wait or a PM role-work result contract."
                    ),
                }
            )
        source = str(data.get("source") or "")
        no_legal_next_action = source == "router_no_legal_next_action" or "no_legal_next_action" in error_code
        if no_legal_next_action:
            resolved_by_event = str(data.get("resolved_by_event") or "")
            resolved = data.get("resolution_status") == "accepted_followup_event_recorded"
            finding = {
                "kind": (
                    "resolved_no_legal_next_action_without_gate_event"
                    if resolved_by_event not in PRODUCT_ARCHITECTURE_GATE_EVENTS
                    else "resolved_no_legal_next_action_with_gate_event"
                ),
                "control_blocker": str(path.relative_to(project_root)),
                "error_code": error_code,
                "resolved": resolved,
                "resolved_by_event": resolved_by_event,
                "pm_repair_rerun_target": data.get("pm_repair_rerun_target"),
                "allowed_resolution_events": data.get("allowed_resolution_events", []),
                "model_meaning": (
                    "A control blocker was needed because the Router had no legal next action. "
                    "If the resolution event is not the current gate event, the repair may only "
                    "have created a follow-up path rather than satisfying the blocked gate."
                ),
            }
            if resolved:
                projection["historical_gate_alignment_findings"].append(finding)
            else:
                projection["current_findings"].append(finding)

    if (
        flags.get("legacy_product_officer_model_report_received")
        and flags.get("product_architecture_modelability_passed")
        and any(
            item.get("kind") == "resolved_no_legal_next_action_without_gate_event"
            for item in projection["historical_gate_alignment_findings"]
        )
    ):
        projection["historical_gate_alignment_findings"].append(
            {
                "kind": "legacy_product_officer_report_preceded_gate_specific_resolution",
                "legacy_events": sorted(PRODUCT_ARCHITECTURE_LEGACY_EVENTS),
                "gate_events": sorted(PRODUCT_ARCHITECTURE_GATE_EVENTS),
                "legacy_flag": "legacy_product_officer_model_report_received",
                "gate_flag": "product_architecture_modelability_passed",
                "model_meaning": (
                    "The run recovered, but it shows the exact class this model protects: a legacy/general "
                    "officer report was recorded before the concrete gate event that actually satisfied "
                    "product_architecture_modelability."
                ),
            }
        )

    for contract_id, item in sorted(contracts.items()):
        projection["risk_surfaces"].append(
            {
                "kind": "router_supplied_contract_needs_dynamic_lease",
                "contract_id": contract_id,
                "output_type": item.get("output_type"),
                "task_family": item.get("task_family"),
                "recipient_roles": item.get("recipient_roles", []),
                "packet_type": item.get("packet_type"),
            }
        )

    for path, data in _iter_json_files(run_root / "packet_batches", "*.json"):
        for item in data.get("packets", []):
            contract_id = item.get("output_contract_id")
            if contract_id in contract_ids:
                projection["mitigated_paths"].append(
                    {
                        "kind": "pm_role_work_result_contract",
                        "path": str(path.relative_to(project_root)),
                        "packet_id": item.get("packet_id"),
                        "status": item.get("status"),
                        "contract_id": contract_id,
                        "strict_process_contract_binding": item.get("strict_process_contract_binding"),
                        "required_result_next_recipient": item.get("required_result_next_recipient"),
                    }
                )

    findings = projection["current_findings"]
    if findings:
        projection["current_run_can_continue"] = False
        projection["classification"] = "blocked_by_dynamic_return_path_findings"
    projection["current_finding_count"] = len(findings)
    projection["historical_gate_alignment_finding_count"] = len(projection["historical_gate_alignment_findings"])
    projection["risk_surface_count"] = len(projection["risk_surfaces"])
    projection["mitigated_path_count"] = len(projection["mitigated_paths"])
    return projection


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEGATIVE_SCENARIOS",
    "SCENARIOS",
    "VALID_SCENARIOS",
    "Action",
    "State",
    "Tick",
    "Transition",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
    "project_live_run_projection",
    "return_path_failures",
    "router_supplied_contracts",
    "terminal_predicate",
]
