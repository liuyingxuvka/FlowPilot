"""FlowGuard model for concrete FlowPilot protocol/contract conformance.

This model covers the failure class that the broader startup and output
contract models intentionally abstract away: concrete JSON paths, event names,
file-backed path/hash lifecycle, and host display receipts must line up across
cards, the contract registry, and router validation.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_FIXED_PROTOCOL = "valid_fixed_protocol"
STARTUP_FACT_JSONPATH_MISMATCH = "startup_fact_jsonpath_mismatch"
CONTROL_BLOCKER_AMBIGUOUS_EVENT = "control_blocker_ambiguous_event"
CONTROL_BLOCKER_WEAK_DECISION_CONTRACT = "control_blocker_weak_decision_contract"
PM_RESUME_DECISION_WEAK_CONTRACT = "pm_resume_decision_weak_contract"
STARTUP_FACT_HASH_ALIAS = "startup_fact_hash_alias"
COCKPIT_MISSING_HOST_RECEIPT = "cockpit_missing_host_receipt"
DISPLAY_FALLBACK_AFTER_PM_ACTIVATION = "display_fallback_after_pm_activation"
STARTUP_REPAIR_DEDUPES_NEW_REPORT = "startup_repair_dedupes_new_report"
ROLE_OUTPUT_ENVELOPE_AMBIGUITY = "role_output_envelope_ambiguity"
MATERIAL_SCAN_INLINE_BODY_ONLY = "material_scan_inline_body_only"
MATERIAL_DISPATCH_UNKNOWN_BLOCK_EVENT = "material_dispatch_unknown_block_event"
MATERIAL_DISPATCH_FRONTIER_PHASE_MISMATCH = "material_dispatch_frontier_phase_mismatch"
REVIEW_BLOCK_EVENTS_WITHOUT_PM_LANE = "review_block_events_without_pm_lane"
REVIEW_BLOCK_REPAIR_EVENT_HARDCODED = "review_block_repair_event_hardcoded"

NEGATIVE_SCENARIOS = (
    STARTUP_FACT_JSONPATH_MISMATCH,
    CONTROL_BLOCKER_AMBIGUOUS_EVENT,
    CONTROL_BLOCKER_WEAK_DECISION_CONTRACT,
    PM_RESUME_DECISION_WEAK_CONTRACT,
    STARTUP_FACT_HASH_ALIAS,
    COCKPIT_MISSING_HOST_RECEIPT,
    DISPLAY_FALLBACK_AFTER_PM_ACTIVATION,
    STARTUP_REPAIR_DEDUPES_NEW_REPORT,
    ROLE_OUTPUT_ENVELOPE_AMBIGUITY,
    MATERIAL_SCAN_INLINE_BODY_ONLY,
    MATERIAL_DISPATCH_UNKNOWN_BLOCK_EVENT,
    MATERIAL_DISPATCH_FRONTIER_PHASE_MISMATCH,
    REVIEW_BLOCK_EVENTS_WITHOUT_PM_LANE,
    REVIEW_BLOCK_REPAIR_EVENT_HARDCODED,
)
SCENARIOS = (VALID_FIXED_PROTOCOL, *NEGATIVE_SCENARIOS)

STARTUP_FACT_CONTRACT_ID = "flowpilot.output_contract.startup_fact_report.v1"
PM_CONTROL_BLOCKER_CONTRACT_ID = "flowpilot.output_contract.pm_control_blocker_repair_decision.v1"
PM_RESUME_DECISION_CONTRACT_ID = "flowpilot.output_contract.pm_resume_decision.v1"
REVIEWER_IDS_PATH = "external_fact_review.reviewer_checked_requirement_ids"
TOP_LEVEL_REVIEWER_IDS_PATH = "reviewer_checked_requirement_ids"
PM_CONTROL_BLOCKER_EVENT = "pm_records_control_blocker_repair_decision"
PM_STARTUP_REPAIR_EVENT = "pm_requests_startup_repair"
MATERIAL_DISPATCH_BLOCK_EVENT = "reviewer_blocks_material_scan_dispatch"
MATERIAL_DISPATCH_BLOCK_FLAG = "material_scan_dispatch_blocked"
MODEL_MISS_REVIEW_BLOCK_FLAGS = frozenset(
    {
        "node_acceptance_plan_review_blocked",
        "node_review_blocked",
    }
)
MODEL_MISS_REVIEW_BLOCK_EVENTS_BY_FLAG = {
    "node_acceptance_plan_review_blocked": "reviewer_blocks_node_acceptance_plan",
    "node_review_blocked": "current_node_reviewer_blocks_result",
}
CONTROL_RECHECK_REVIEW_BLOCK_FLAGS = frozenset(
    {
        "material_scan_dispatch_recheck_blocked",
        "material_scan_dispatch_recheck_protocol_blocked",
    }
)
DECLARED_REVIEW_BLOCK_FLAGS = MODEL_MISS_REVIEW_BLOCK_FLAGS | CONTROL_RECHECK_REVIEW_BLOCK_FLAGS
MODEL_MISS_REVIEW_BLOCK_CARD_IDS = frozenset(
    {"pm.model_miss_triage", "pm.review_repair", "pm.event.reviewer_blocked"}
)
PM_REVIEW_BLOCK_REPAIR_EVENT = "pm_mutates_route_after_review_block"

ROLE_OUTPUT_REQUIRED_PAIRS = frozenset(
    {
        "body_ref.path/body_ref.hash",
        "runtime_receipt_ref.path/runtime_receipt_ref.hash",
    }
)

PM_CONTROL_BLOCKER_REQUIRED_FIELDS = frozenset(
    {
        "decided_by_role",
        "blocker_id",
        "decision",
        "prior_path_context_review",
        "repair_action",
        "rerun_target",
        "blockers",
        "contract_self_check",
    }
)

PM_RESUME_DECISION_REQUIRED_FIELDS = frozenset(
    {
        "decision_owner",
        "decision",
        "explicit_recovery_evidence_recorded",
        "prior_path_context_review.reviewed",
        "prior_path_context_review.source_paths",
        "prior_path_context_review.completed_nodes_considered",
        "prior_path_context_review.superseded_nodes_considered",
        "prior_path_context_review.stale_evidence_considered",
        "prior_path_context_review.prior_blocks_or_experiments_considered",
        "prior_path_context_review.impact_on_decision",
        "prior_path_context_review.controller_summary_used_as_evidence",
        "controller_reminder.controller_only",
        "controller_reminder.controller_may_read_sealed_bodies",
        "controller_reminder.controller_may_infer_from_chat_history",
        "controller_reminder.controller_may_advance_or_close_route",
    }
)


@dataclass(frozen=True)
class Tick:
    """One protocol conformance tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"

    startup_contract_paths: frozenset[str] = field(default_factory=frozenset)
    startup_card_example_paths: frozenset[str] = field(default_factory=frozenset)
    startup_card_prose_paths: frozenset[str] = field(default_factory=frozenset)
    startup_router_validator_paths: frozenset[str] = field(default_factory=frozenset)
    startup_router_canonical_paths: frozenset[str] = field(default_factory=frozenset)

    pm_control_blocker_allowed_events: frozenset[str] = field(default_factory=frozenset)
    pm_control_blocker_card_events: frozenset[str] = field(default_factory=frozenset)
    pm_startup_repair_requires_activation_card: bool = True
    control_blocker_action_delivers_review_repair_card: bool = False

    pm_control_blocker_contract_fields: frozenset[str] = field(default_factory=frozenset)
    pm_control_blocker_router_fields: frozenset[str] = field(default_factory=frozenset)
    pm_control_blocker_card_fields: frozenset[str] = field(default_factory=frozenset)
    pm_resume_contract_fields: frozenset[str] = field(default_factory=frozenset)
    pm_resume_router_fields: frozenset[str] = field(default_factory=frozenset)
    pm_resume_card_fields: frozenset[str] = field(default_factory=frozenset)
    pm_resume_action_contract_fields: frozenset[str] = field(default_factory=frozenset)

    router_rewrites_startup_fact_canonical: bool = True
    startup_role_may_submit_to_canonical_path: bool = True
    router_blocks_startup_fact_canonical_alias: bool = False

    display_requested_cockpit: bool = False
    display_has_host_receipt: bool = False
    display_has_explicit_fallback: bool = False
    display_status_available_before_startup_fact_review: bool = True

    startup_repair_request_repeatable_for_new_blocking_report: bool = True
    startup_repair_request_tracks_cycle_identity: bool = True
    startup_repair_exact_duplicate_rejected: bool = True

    role_output_contract_path_hash_pairs: frozenset[str] = field(default_factory=frozenset)
    role_output_router_path_hash_pairs: frozenset[str] = field(default_factory=frozenset)
    role_output_card_path_hash_pairs: frozenset[str] = field(default_factory=frozenset)
    role_output_cards_require_compact_refs: bool = True
    role_output_cards_forbid_sha256_aliases: bool = True
    role_output_router_rejects_sha256_aliases: bool = True
    role_output_router_rejects_nested_envelope: bool = True

    material_scan_card_requires_file_backed_packet_bodies: bool = True
    material_scan_router_accepts_file_backed_packet_specs: bool = True
    material_scan_router_requires_inline_body_text_only: bool = False
    material_scan_index_forbids_controller_body_reads: bool = True

    material_dispatch_block_event_registered: bool = True
    material_dispatch_block_report_writer: bool = True
    material_dispatch_pm_block_cards_reachable: bool = True
    material_dispatch_route_memory_tracks_block: bool = True
    material_dispatch_direct_preflight_required: bool = True

    declared_reviewer_block_flags: frozenset[str] = field(default_factory=lambda: DECLARED_REVIEW_BLOCK_FLAGS)
    reviewer_block_lane_flags: frozenset[str] = field(default_factory=lambda: DECLARED_REVIEW_BLOCK_FLAGS)
    model_miss_review_block_event_flags: frozenset[str] = field(default_factory=lambda: MODEL_MISS_REVIEW_BLOCK_FLAGS)
    model_miss_review_block_card_flags: frozenset[str] = field(default_factory=lambda: MODEL_MISS_REVIEW_BLOCK_FLAGS)
    model_miss_review_block_cards_aligned: bool = True
    model_miss_triage_accepts_review_block_flags: frozenset[str] = field(default_factory=lambda: MODEL_MISS_REVIEW_BLOCK_FLAGS)
    pm_review_block_repair_event_accepts_flags: frozenset[str] = field(default_factory=lambda: MODEL_MISS_REVIEW_BLOCK_FLAGS)
    pm_review_block_repair_event_routes_flags: frozenset[str] = field(default_factory=lambda: MODEL_MISS_REVIEW_BLOCK_FLAGS)

    material_dispatch_frontier_phase_synchronized: bool = True
    material_dispatch_card_has_pre_route_material_exception: bool = True
    material_scan_packets_mark_pre_route_not_current_node: bool = True

    router_decision: str = "none"  # none | accept | reject
    router_rejection_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class ProtocolConformanceStep:
    """Model one concrete FlowPilot protocol conformance transition.

    Input x State -> Set(Output x State)
    reads: card JSON paths, contract fields, router validators, event
    preconditions, path/hash alias rules, and display receipt facts.
    writes: one scenario selection or terminal protocol decision.
    idempotency: repeated ticks do not duplicate scenario facts or terminal
    decisions.
    """

    name = "ProtocolConformanceStep"
    reads = (
        "card_jsonpaths",
        "contract_registry_fields",
        "router_validator_fields",
        "event_preconditions",
        "file_backed_hash_lifecycle",
        "display_receipts",
    )
    writes = ("scenario_facts", "terminal_protocol_decision")
    input_description = "protocol conformance tick"
    output_description = "one abstract protocol conformance action"
    idempotency = "repeat ticks leave scenario and terminal decision unchanged"

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


def _valid_state() -> State:
    startup_paths = frozenset(
        {
            "reviewed_by_role",
            "passed",
            "external_fact_review",
            "external_fact_review.reviewed_by_role",
            "external_fact_review.direct_evidence_paths_checked",
            "external_fact_review.self_attested_ai_claims_accepted_as_proof",
            REVIEWER_IDS_PATH,
            "findings",
            "blockers",
            "residual_risks",
            "contract_self_check",
        }
    )
    return State(
        status="running",
        scenario=VALID_FIXED_PROTOCOL,
        startup_contract_paths=startup_paths,
        startup_card_example_paths=startup_paths,
        startup_card_prose_paths=frozenset({REVIEWER_IDS_PATH}),
        startup_router_validator_paths=frozenset({REVIEWER_IDS_PATH}),
        startup_router_canonical_paths=frozenset({REVIEWER_IDS_PATH}),
        pm_control_blocker_allowed_events=frozenset({PM_CONTROL_BLOCKER_EVENT}),
        pm_control_blocker_card_events=frozenset({PM_CONTROL_BLOCKER_EVENT}),
        pm_control_blocker_contract_fields=PM_CONTROL_BLOCKER_REQUIRED_FIELDS,
        pm_control_blocker_router_fields=PM_CONTROL_BLOCKER_REQUIRED_FIELDS,
        pm_control_blocker_card_fields=PM_CONTROL_BLOCKER_REQUIRED_FIELDS,
        pm_resume_contract_fields=PM_RESUME_DECISION_REQUIRED_FIELDS,
        pm_resume_router_fields=PM_RESUME_DECISION_REQUIRED_FIELDS,
        pm_resume_card_fields=PM_RESUME_DECISION_REQUIRED_FIELDS,
        pm_resume_action_contract_fields=PM_RESUME_DECISION_REQUIRED_FIELDS,
        router_rewrites_startup_fact_canonical=True,
        startup_role_may_submit_to_canonical_path=False,
        router_blocks_startup_fact_canonical_alias=True,
        display_requested_cockpit=True,
        display_has_host_receipt=True,
        display_has_explicit_fallback=False,
        role_output_contract_path_hash_pairs=ROLE_OUTPUT_REQUIRED_PAIRS,
        role_output_router_path_hash_pairs=ROLE_OUTPUT_REQUIRED_PAIRS,
        role_output_card_path_hash_pairs=ROLE_OUTPUT_REQUIRED_PAIRS,
        role_output_cards_require_compact_refs=True,
        role_output_cards_forbid_sha256_aliases=True,
        role_output_router_rejects_sha256_aliases=True,
        role_output_router_rejects_nested_envelope=True,
        material_scan_card_requires_file_backed_packet_bodies=True,
        material_scan_router_accepts_file_backed_packet_specs=True,
        material_scan_router_requires_inline_body_text_only=False,
        material_scan_index_forbids_controller_body_reads=True,
        material_dispatch_block_event_registered=True,
        material_dispatch_block_report_writer=True,
        material_dispatch_pm_block_cards_reachable=True,
        material_dispatch_route_memory_tracks_block=True,
        material_dispatch_direct_preflight_required=True,
        material_dispatch_frontier_phase_synchronized=True,
        material_dispatch_card_has_pre_route_material_exception=True,
        material_scan_packets_mark_pre_route_not_current_node=True,
    )


def _scenario_state(scenario: str) -> State:
    state = _valid_state()
    state = replace(state, scenario=scenario)
    if scenario == STARTUP_FACT_JSONPATH_MISMATCH:
        return replace(
            state,
            startup_contract_paths=(state.startup_contract_paths - frozenset({REVIEWER_IDS_PATH}))
            | frozenset({TOP_LEVEL_REVIEWER_IDS_PATH}),
            startup_card_example_paths=(state.startup_card_example_paths - frozenset({REVIEWER_IDS_PATH}))
            | frozenset({TOP_LEVEL_REVIEWER_IDS_PATH}),
        )
    if scenario == CONTROL_BLOCKER_AMBIGUOUS_EVENT:
        return replace(
            state,
            pm_control_blocker_allowed_events=frozenset({PM_CONTROL_BLOCKER_EVENT, PM_STARTUP_REPAIR_EVENT}),
            pm_control_blocker_card_events=frozenset({PM_STARTUP_REPAIR_EVENT}),
            control_blocker_action_delivers_review_repair_card=False,
        )
    if scenario == CONTROL_BLOCKER_WEAK_DECISION_CONTRACT:
        weak_fields = frozenset({"decided_by_role", "blocker_id", "decision"})
        return replace(
            state,
            pm_control_blocker_contract_fields=weak_fields,
            pm_control_blocker_router_fields=weak_fields,
        )
    if scenario == PM_RESUME_DECISION_WEAK_CONTRACT:
        weak_fields = frozenset({"decision_owner", "decision"})
        return replace(
            state,
            pm_resume_contract_fields=weak_fields,
            pm_resume_card_fields=weak_fields,
            pm_resume_action_contract_fields=weak_fields,
        )
    if scenario == STARTUP_FACT_HASH_ALIAS:
        return replace(
            state,
            startup_role_may_submit_to_canonical_path=True,
            router_blocks_startup_fact_canonical_alias=False,
        )
    if scenario == COCKPIT_MISSING_HOST_RECEIPT:
        return replace(
            state,
            display_requested_cockpit=True,
            display_has_host_receipt=False,
            display_has_explicit_fallback=False,
        )
    if scenario == DISPLAY_FALLBACK_AFTER_PM_ACTIVATION:
        return replace(
            state,
            display_requested_cockpit=True,
            display_has_host_receipt=False,
            display_has_explicit_fallback=True,
            display_status_available_before_startup_fact_review=False,
        )
    if scenario == STARTUP_REPAIR_DEDUPES_NEW_REPORT:
        return replace(
            state,
            startup_repair_request_repeatable_for_new_blocking_report=False,
            startup_repair_request_tracks_cycle_identity=False,
            startup_repair_exact_duplicate_rejected=False,
        )
    if scenario == ROLE_OUTPUT_ENVELOPE_AMBIGUITY:
        return replace(
            state,
            role_output_card_path_hash_pairs=frozenset({"report_path/report_hash"}),
            role_output_cards_require_compact_refs=False,
            role_output_cards_forbid_sha256_aliases=False,
        )
    if scenario == MATERIAL_SCAN_INLINE_BODY_ONLY:
        return replace(
            state,
            material_scan_card_requires_file_backed_packet_bodies=False,
            material_scan_router_accepts_file_backed_packet_specs=False,
            material_scan_router_requires_inline_body_text_only=True,
        )
    if scenario == MATERIAL_DISPATCH_UNKNOWN_BLOCK_EVENT:
        return replace(
            state,
            material_dispatch_block_event_registered=False,
            material_dispatch_block_report_writer=False,
            material_dispatch_pm_block_cards_reachable=False,
            material_dispatch_route_memory_tracks_block=False,
        )
    if scenario == MATERIAL_DISPATCH_FRONTIER_PHASE_MISMATCH:
        return replace(
            state,
            material_dispatch_frontier_phase_synchronized=False,
            material_dispatch_card_has_pre_route_material_exception=False,
        )
    if scenario == REVIEW_BLOCK_EVENTS_WITHOUT_PM_LANE:
        old_lane_flags = frozenset({"node_review_blocked"})
        return replace(
            state,
            model_miss_review_block_card_flags=old_lane_flags,
            model_miss_triage_accepts_review_block_flags=old_lane_flags,
            pm_review_block_repair_event_accepts_flags=old_lane_flags,
            pm_review_block_repair_event_routes_flags=old_lane_flags,
        )
    if scenario == REVIEW_BLOCK_REPAIR_EVENT_HARDCODED:
        return replace(
            state,
            pm_review_block_repair_event_accepts_flags=frozenset({"node_review_blocked"}),
            pm_review_block_repair_event_routes_flags=frozenset({"node_review_blocked"}),
        )
    return state


def _jsonpath_failures(state: State) -> list[str]:
    failures: list[str] = []
    router_paths = state.startup_router_validator_paths | state.startup_router_canonical_paths
    if REVIEWER_IDS_PATH not in router_paths:
        failures.append("startup fact router validator does not require nested reviewer_checked_requirement_ids")
    sources = {
        "startup fact output contract": state.startup_contract_paths,
        "startup fact card example": state.startup_card_example_paths,
        "startup fact card prose": state.startup_card_prose_paths,
    }
    for name, paths in sources.items():
        if REVIEWER_IDS_PATH not in paths:
            failures.append(f"{name} does not expose router-required {REVIEWER_IDS_PATH}")
        if TOP_LEVEL_REVIEWER_IDS_PATH in paths and REVIEWER_IDS_PATH not in paths:
            failures.append(f"{name} exposes top-level reviewer_checked_requirement_ids instead of nested path")
    return failures


def _control_blocker_event_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.pm_control_blocker_allowed_events != frozenset({PM_CONTROL_BLOCKER_EVENT}):
        failures.append("PM control-blocker lane does not narrow allowed_resolution_events to pm_records_control_blocker_repair_decision")
    if (
        PM_CONTROL_BLOCKER_EVENT not in state.pm_control_blocker_card_events
        and not state.control_blocker_action_delivers_review_repair_card
    ):
        failures.append("PM control-blocker guidance does not name the legal repair-decision event")
    if (
        PM_STARTUP_REPAIR_EVENT in state.pm_control_blocker_allowed_events
        and state.pm_startup_repair_requires_activation_card
    ):
        failures.append("PM control-blocker lane allows startup repair event whose startup activation card precondition may be unsatisfied")
    return failures


def _control_blocker_contract_failures(state: State) -> list[str]:
    failures: list[str] = []
    missing_contract = PM_CONTROL_BLOCKER_REQUIRED_FIELDS - state.pm_control_blocker_contract_fields
    missing_router = PM_CONTROL_BLOCKER_REQUIRED_FIELDS - state.pm_control_blocker_router_fields
    missing_card = PM_CONTROL_BLOCKER_REQUIRED_FIELDS - state.pm_control_blocker_card_fields
    if missing_contract:
        failures.append("PM control-blocker output contract omits required fields: " + ", ".join(sorted(missing_contract)))
    if missing_router:
        failures.append("router control-blocker decision validator omits required fields: " + ", ".join(sorted(missing_router)))
    if missing_card:
        failures.append("PM control-blocker card omits required fields: " + ", ".join(sorted(missing_card)))
    return failures


def _pm_resume_decision_contract_failures(state: State) -> list[str]:
    failures: list[str] = []
    missing_contract = PM_RESUME_DECISION_REQUIRED_FIELDS - state.pm_resume_contract_fields
    missing_router = PM_RESUME_DECISION_REQUIRED_FIELDS - state.pm_resume_router_fields
    missing_card = PM_RESUME_DECISION_REQUIRED_FIELDS - state.pm_resume_card_fields
    missing_action = PM_RESUME_DECISION_REQUIRED_FIELDS - state.pm_resume_action_contract_fields
    if missing_contract:
        failures.append("PM resume decision output contract omits required fields: " + ", ".join(sorted(missing_contract)))
    if missing_router:
        failures.append("router PM resume decision validator omits required fields: " + ", ".join(sorted(missing_router)))
    if missing_card:
        failures.append("PM resume decision card omits required JSON template fields: " + ", ".join(sorted(missing_card)))
    if missing_action:
        failures.append("PM resume decision action payload_contract omits required fields: " + ", ".join(sorted(missing_action)))
    return failures


def _hash_lifecycle_failures(state: State) -> list[str]:
    if (
        state.router_rewrites_startup_fact_canonical
        and state.startup_role_may_submit_to_canonical_path
        and not state.router_blocks_startup_fact_canonical_alias
    ):
        return [
            "startup fact role submission can alias router canonical report path before router rewrites the canonical file"
        ]
    return []


def _display_receipt_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.display_requested_cockpit and not (
        state.display_has_host_receipt or state.display_has_explicit_fallback
    ):
        failures.append("cockpit requested without host receipt or explicit fallback receipt")
    if (
        state.display_requested_cockpit
        and state.display_has_explicit_fallback
        and not state.display_status_available_before_startup_fact_review
    ):
        failures.append("display fallback receipt is unavailable before startup reviewer fact review")
    return failures


def _startup_repair_cycle_failures(state: State) -> list[str]:
    failures: list[str] = []
    if not state.startup_repair_request_repeatable_for_new_blocking_report:
        failures.append("startup repair event is deduped by a one-shot flag instead of current report and decision identity")
    if not state.startup_repair_request_tracks_cycle_identity:
        failures.append("startup repair request does not record repair cycle identity and current blocking report hash")
    if not state.startup_repair_exact_duplicate_rejected:
        failures.append("startup repair exact duplicate replay is not rejected or ignored distinctly from a new repair cycle")
    return failures


def _role_output_envelope_failures(state: State) -> list[str]:
    failures: list[str] = []
    missing_contract = ROLE_OUTPUT_REQUIRED_PAIRS - state.role_output_contract_path_hash_pairs
    missing_router = ROLE_OUTPUT_REQUIRED_PAIRS - state.role_output_router_path_hash_pairs
    missing_cards = ROLE_OUTPUT_REQUIRED_PAIRS - state.role_output_card_path_hash_pairs
    if missing_contract:
        failures.append("role output envelope contract omits required path/hash pairs: " + ", ".join(sorted(missing_contract)))
    if missing_router:
        failures.append("router role output loader omits required path/hash pairs: " + ", ".join(sorted(missing_router)))
    if missing_cards:
        failures.append("role output guidance omits exact path/hash pairs: " + ", ".join(sorted(missing_cards)))
    if not state.role_output_cards_require_compact_refs:
        failures.append("role output guidance does not require compact body_ref/runtime_receipt_ref envelope refs")
    if not state.role_output_cards_forbid_sha256_aliases:
        failures.append("role output guidance does not forbid *_sha256 hash aliases")
    if not state.role_output_router_rejects_sha256_aliases:
        failures.append("router role output loader accepts *_sha256 hash aliases")
    if not state.role_output_router_rejects_nested_envelope:
        failures.append("router role output loader accepts nested role_output_envelope objects")
    return failures


def _material_scan_packet_failures(state: State) -> list[str]:
    failures: list[str] = []
    if not state.material_scan_card_requires_file_backed_packet_bodies:
        failures.append("PM material scan guidance does not require file-backed packet body paths and hashes")
    if not state.material_scan_router_accepts_file_backed_packet_specs:
        failures.append("router material scan writer does not accept file-backed packet body specs")
    if state.material_scan_router_requires_inline_body_text_only:
        failures.append("router material scan writer requires inline body_text in Controller-visible payload")
    if not state.material_scan_index_forbids_controller_body_reads:
        failures.append("material scan index does not state controller_may_read_packet_body=false")
    return failures


def _material_dispatch_block_failures(state: State) -> list[str]:
    failures: list[str] = []
    if not state.material_dispatch_block_event_registered:
        failures.append("material dispatch reviewer block event is not registered")
    if not state.material_dispatch_block_report_writer:
        failures.append("material dispatch reviewer block event has no file-backed report writer")
    if not state.material_dispatch_pm_block_cards_reachable:
        failures.append("material dispatch router block cannot route to PM control-blocker repair")
    if not state.material_dispatch_route_memory_tracks_block:
        failures.append("material dispatch reviewer block is missing from route-memory reviewer block markers")
    if not state.material_dispatch_direct_preflight_required:
        failures.append("material scan packet relay does not require router direct-dispatch preflight")
    return failures


def _missing_extra(actual: frozenset[str], expected: frozenset[str]) -> str:
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    parts: list[str] = []
    if missing:
        parts.append("missing " + ", ".join(missing))
    if extra:
        parts.append("extra " + ", ".join(extra))
    return "; ".join(parts) if parts else "sets differ"


def _review_block_lane_failures(state: State) -> list[str]:
    failures: list[str] = []
    unclassified = state.declared_reviewer_block_flags - state.reviewer_block_lane_flags
    if unclassified:
        failures.append(
            "declared reviewer block flags lack an explicit router lane: "
            + ", ".join(sorted(unclassified))
        )
    if state.model_miss_review_block_event_flags != MODEL_MISS_REVIEW_BLOCK_FLAGS:
        failures.append(
            "model-miss reviewer block event taxonomy does not declare expected flags: "
            + _missing_extra(state.model_miss_review_block_event_flags, MODEL_MISS_REVIEW_BLOCK_FLAGS)
        )
    if (
        not state.model_miss_review_block_cards_aligned
        or state.model_miss_review_block_card_flags != MODEL_MISS_REVIEW_BLOCK_FLAGS
    ):
        failures.append(
            "PM model-miss cards do not cover all declared model-miss reviewer block flags: "
            + _missing_extra(state.model_miss_review_block_card_flags, MODEL_MISS_REVIEW_BLOCK_FLAGS)
        )
    if state.model_miss_triage_accepts_review_block_flags != MODEL_MISS_REVIEW_BLOCK_FLAGS:
        failures.append(
            "PM model-miss triage validator does not accept all declared model-miss reviewer block flags: "
            + _missing_extra(state.model_miss_triage_accepts_review_block_flags, MODEL_MISS_REVIEW_BLOCK_FLAGS)
        )
    if state.pm_review_block_repair_event_accepts_flags != MODEL_MISS_REVIEW_BLOCK_FLAGS:
        failures.append(
            "PM review-block repair event does not accept all declared model-miss reviewer block flags: "
            + _missing_extra(state.pm_review_block_repair_event_accepts_flags, MODEL_MISS_REVIEW_BLOCK_FLAGS)
        )
    if state.pm_review_block_repair_event_routes_flags != MODEL_MISS_REVIEW_BLOCK_FLAGS:
        failures.append(
            "PM review-block repair event has no writer for all declared model-miss reviewer block flags: "
            + _missing_extra(state.pm_review_block_repair_event_routes_flags, MODEL_MISS_REVIEW_BLOCK_FLAGS)
        )
    return failures


def _material_dispatch_frontier_failures(state: State) -> list[str]:
    failures: list[str] = []
    if not state.material_dispatch_frontier_phase_synchronized:
        failures.append("material dispatch review can run while execution_frontier still reports startup_intake")
    if not state.material_dispatch_card_has_pre_route_material_exception:
        failures.append("material dispatch reviewer card treats pre-route material_scan as a current-node dispatch")
    if not state.material_scan_packets_mark_pre_route_not_current_node:
        failures.append("material scan packets are not marked as pre-route non-current-node work")
    return failures


def protocol_failures(state: State) -> list[str]:
    failures: list[str] = []
    failures.extend(_jsonpath_failures(state))
    failures.extend(_control_blocker_event_failures(state))
    failures.extend(_control_blocker_contract_failures(state))
    failures.extend(_pm_resume_decision_contract_failures(state))
    failures.extend(_hash_lifecycle_failures(state))
    failures.extend(_display_receipt_failures(state))
    failures.extend(_startup_repair_cycle_failures(state))
    failures.extend(_role_output_envelope_failures(state))
    failures.extend(_material_scan_packet_failures(state))
    failures.extend(_material_dispatch_block_failures(state))
    failures.extend(_review_block_lane_failures(state))
    failures.extend(_material_dispatch_frontier_failures(state))
    return failures


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return

    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _scenario_state(scenario))
        return

    failures = protocol_failures(state)
    if failures:
        reason = failures[0]
        yield Transition(
            f"router_rejects_{state.scenario}",
            replace(
                state,
                status="rejected",
                router_decision="reject",
                router_rejection_reason=reason,
            ),
        )
        return

    yield Transition(
        "router_accepts_conformant_protocol",
        replace(state, status="accepted", router_decision="accept"),
    )


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return is_terminal(state)


def accepted_protocol_conforms(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    failures = protocol_failures(state)
    if failures:
        return InvariantResult.fail(failures[0])
    return InvariantResult.pass_()


def negative_scenarios_are_rejected(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.scenario in NEGATIVE_SCENARIOS:
        return InvariantResult.fail(f"router accepted negative protocol scenario {state.scenario}")
    if state.status == "rejected" and state.scenario == VALID_FIXED_PROTOCOL:
        return InvariantResult.fail(f"router rejected valid protocol scenario: {state.router_rejection_reason}")
    return InvariantResult.pass_()


def terminal_decisions_are_explicit(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.router_decision != "accept":
        return InvariantResult.fail("accepted terminal state lacks accept decision")
    if state.status == "rejected" and (
        state.router_decision != "reject" or not state.router_rejection_reason
    ):
        return InvariantResult.fail("rejected terminal state lacks explicit rejection reason")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepted_protocol_conforms",
        description="Accepted protocol states must align concrete cards, contracts, router validators, path/hash lifecycle, and display receipts.",
        predicate=accepted_protocol_conforms,
    ),
    Invariant(
        name="negative_scenarios_are_rejected",
        description="Known-bad protocol scenarios must be rejected while the fixed protocol is accepted.",
        predicate=negative_scenarios_are_rejected,
    ),
    Invariant(
        name="terminal_decisions_are_explicit",
        description="Terminal protocol states must carry an explicit router accept/reject decision.",
        predicate=terminal_decisions_are_explicit,
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
    return Workflow((ProtocolConformanceStep(),), name="flowpilot_protocol_contract_conformance")


def terminal_predicate(_input_obj, state: State, _trace) -> bool:
    return is_terminal(state)


def hazard_states() -> dict[str, State]:
    return {
        scenario: replace(_scenario_state(scenario), status="accepted", router_decision="accept")
        for scenario in NEGATIVE_SCENARIOS
    }


def _load_router(project_root: Path) -> Any:
    assets_root = project_root / "skills" / "flowpilot" / "assets"
    router_path = assets_root / "flowpilot_router.py"
    sys.path.insert(0, str(assets_root))
    spec = importlib.util.spec_from_file_location(
        "flowpilot_router_for_protocol_contract_conformance", router_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load router module from {router_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _contract_fields(project_root: Path, contract_id: str) -> frozenset[str]:
    contract_path = project_root / "skills" / "flowpilot" / "assets" / "runtime_kit" / "contracts" / "contract_index.json"
    payload = json.loads(contract_path.read_text(encoding="utf-8"))
    for contract in payload.get("contracts", []):
        if isinstance(contract, dict) and contract.get("contract_id") == contract_id:
            return frozenset(str(field) for field in contract.get("required_body_fields", []))
    raise RuntimeError(f"missing contract {contract_id}")


def _contract_role_output_path_hash_pairs(project_root: Path) -> frozenset[str]:
    contract_path = project_root / "skills" / "flowpilot" / "assets" / "runtime_kit" / "contracts" / "contract_index.json"
    payload = json.loads(contract_path.read_text(encoding="utf-8"))
    for contract in payload.get("contracts", []):
        if isinstance(contract, dict) and contract.get("contract_id") == "flowpilot.output_contract.role_output_envelope.v1":
            return frozenset(str(pair) for pair in contract.get("required_envelope_path_hash_pairs", []))
    raise RuntimeError("missing role output envelope contract")


def _tuple_assignment_values(source: str, variable_name: str) -> frozenset[str]:
    match = re.search(rf"{re.escape(variable_name)}\s*=\s*\((.*?)\)", source, re.DOTALL)
    if not match:
        return frozenset()
    return frozenset(re.findall(r'"([^"]+)"', match.group(1)))


def _path_hash_pairs_from_keys(path_keys: frozenset[str], hash_keys: frozenset[str]) -> frozenset[str]:
    pairs: set[str] = set()
    for path_key in path_keys:
        hash_key = path_key.replace("_path", "_hash")
        if hash_key in hash_keys:
            pairs.add(f"{path_key}/{hash_key}")
    return frozenset(pairs)


def _router_role_output_path_hash_pairs(router_source: str) -> frozenset[str]:
    segment = _function_segment(router_source, "_load_file_backed_role_payload")
    pairs = set(_path_hash_pairs_from_keys(
        _tuple_assignment_values(segment, "path_keys"),
        _tuple_assignment_values(segment, "hash_keys"),
    ))
    if "body_ref" in segment and "validate_envelope_runtime_receipt" in segment:
        pairs.add("body_ref.path/body_ref.hash")
    if "runtime_receipt_ref" in segment and "validate_envelope_runtime_receipt" in segment:
        pairs.add("runtime_receipt_ref.path/runtime_receipt_ref.hash")
    return frozenset(pairs)


def _role_output_card_path_hash_pairs(*texts: str) -> frozenset[str]:
    combined = "\n".join(texts)
    pairs: set[str] = set()
    for path_key, hash_key in (
        ("body_ref.path", "body_ref.hash"),
        ("runtime_receipt_ref.path", "runtime_receipt_ref.hash"),
        ("body_path", "body_hash"),
        ("report_path", "report_hash"),
        ("decision_path", "decision_hash"),
        ("result_body_path", "result_body_hash"),
    ):
        dotted_pair_present = path_key in combined and hash_key in combined
        compact_pair_present = (
            path_key.startswith("body_ref")
            and "body_ref" in combined
            and ("path/hash" in combined or ("path" in combined and "hash" in combined))
        ) or (
            path_key.startswith("runtime_receipt_ref")
            and "runtime_receipt_ref" in combined
            and ("path/hash" in combined or ("path" in combined and "hash" in combined))
        )
        if dotted_pair_present or compact_pair_present:
            pairs.add(f"{path_key}/{hash_key}")
    return frozenset(pairs)


def _role_output_cards_require_compact_refs(*texts: str) -> bool:
    combined = "\n".join(texts).lower()
    names_envelope = (
        "role_output_envelope" in combined
        or "role-output envelope" in combined
        or "role output envelope" in combined
    )
    return (
        names_envelope
        and "body_ref" in combined
        and "runtime_receipt_ref" in combined
        and ("path/hash" in combined or ("path" in combined and "hash" in combined))
    )


def _role_output_cards_forbid_sha256_aliases(*texts: str) -> bool:
    combined = "\n".join(texts).lower()
    return "sha256" in combined and ("do not use" in combined or "forbid" in combined or "not accepted" in combined)


def _router_rejects_sha256_aliases(router_source: str) -> bool:
    segment = _function_segment(router_source, "_load_file_backed_role_payload")
    return not any(key.endswith("_sha256") for key in _tuple_assignment_values(segment, "hash_keys"))


def _router_rejects_nested_role_output_envelope(router_source: str) -> bool:
    segment = _function_segment(router_source, "_load_file_backed_role_payload")
    return "role_output_envelope" not in _tuple_assignment_values(segment, "path_keys")


def _material_scan_card_requires_file_backed_packet_bodies(text: str) -> bool:
    lower = text.lower()
    return "body_path" in lower and "body_hash" in lower and (
        "body_text" not in lower or "do not put `body_text`" in lower
    )


def _material_scan_router_accepts_file_backed_packet_specs(router_source: str) -> bool:
    segment = _function_segment(router_source, "_write_material_scan_packets") + _function_segment(
        router_source,
        "_material_packet_body_text_from_spec",
    )
    return (
        ("body_path" in segment or "packet_body_path" in segment)
        and ("body_hash" in segment or "packet_body_hash" in segment)
    )


def _material_scan_router_requires_inline_body_text_only(router_source: str) -> bool:
    segment = _function_segment(router_source, "_write_material_scan_packets")
    return 'body_text = spec.get("body_text")' in segment and not _material_scan_router_accepts_file_backed_packet_specs(router_source)


def _material_scan_index_forbids_controller_body_reads(router_source: str) -> bool:
    segment = _function_segment(router_source, "_write_material_scan_packets")
    return '"controller_may_read_packet_body": False' in segment


def _material_dispatch_block_event_registered(router: Any) -> bool:
    return MATERIAL_DISPATCH_BLOCK_EVENT in router.EXTERNAL_EVENTS


def _material_dispatch_block_report_writer(router_source: str) -> bool:
    segment = _function_segment(router_source, "_record_external_event_unchecked")
    return MATERIAL_DISPATCH_BLOCK_EVENT in segment and (
        "_write_material_dispatch_block" in segment or "_write_role_gate_report" in segment
    )


def _material_dispatch_pm_block_cards_reachable(router_source: str) -> bool:
    control_blocker_segment = (
        _function_segment(router_source, "_control_blocker_allowed_resolution_events")
        + "\n"
        + _function_segment(router_source, "_repair_outcome_table")
        + "\n"
        + _function_segment(router_source, "_write_control_blocker_repair_decision")
    )
    return (
        PM_CONTROL_BLOCKER_EVENT in router_source
        and "PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT" in control_blocker_segment
        and "router_direct_material_scan_dispatch_recheck_passed" in control_blocker_segment
        and "router_direct_material_scan_dispatch_recheck_blocked" in control_blocker_segment
        and "router_protocol_blocker_material_scan_dispatch_recheck" in control_blocker_segment
    )


def _material_dispatch_route_memory_tracks_block(router_source: str) -> bool:
    segment = _function_segment(router_source, "_refresh_route_memory")
    return MATERIAL_DISPATCH_BLOCK_EVENT in segment


def _material_dispatch_direct_preflight_required(router_source: str) -> bool:
    next_segment = _function_segment(router_source, "_next_material_packet_action")
    relay_segment = _function_segment(router_source, "_relay_packet_records")
    return (
        "validate_packet_ready_for_direct_relay" in relay_segment
        and "reviewer_dispatch_allowed" not in next_segment
        and MATERIAL_DISPATCH_BLOCK_FLAG not in next_segment
    )


def _declared_reviewer_block_flags(router: Any) -> frozenset[str]:
    flags: set[str] = set()
    for event_name, meta in router.EXTERNAL_EVENTS.items():
        if bool(meta.get("legacy")):
            continue
        if (
            event_name.startswith("reviewer_blocks_")
            or event_name.startswith("reviewer_protocol_blocker_")
            or event_name == "current_node_reviewer_blocks_result"
        ):
            flag = meta.get("flag")
            if flag:
                flags.add(str(flag))
    return frozenset(flags)


def _declared_model_miss_review_block_flags(router: Any, router_source: str) -> frozenset[str]:
    declared = getattr(router, "MODEL_MISS_REVIEW_BLOCK_FLAGS", None)
    if declared is not None:
        return frozenset(str(flag) for flag in declared)
    match = re.search(r"MODEL_MISS_REVIEW_BLOCK_FLAGS\s*=\s*\((.*?)\)", router_source, re.DOTALL)
    if not match:
        return frozenset()
    return frozenset(re.findall(r'"([^"]+)"', match.group(1)))


def _model_miss_review_block_event_flags(router: Any) -> frozenset[str]:
    event_names = getattr(router, "MODEL_MISS_REVIEW_BLOCK_EVENTS", tuple(MODEL_MISS_REVIEW_BLOCK_EVENTS_BY_FLAG.values()))
    flags: set[str] = set()
    for event_name in event_names:
        meta = router.EXTERNAL_EVENTS.get(str(event_name), {})
        flag = meta.get("flag")
        if flag:
            flags.add(str(flag))
    return frozenset(flags)


def _model_miss_review_block_card_flag_sets(router: Any) -> tuple[frozenset[str], bool]:
    flag_sets: list[frozenset[str]] = []
    for entry in router.SYSTEM_CARD_SEQUENCE:
        if entry.get("card_id") in MODEL_MISS_REVIEW_BLOCK_CARD_IDS:
            flag_sets.append(frozenset(str(flag) for flag in entry.get("requires_any_flag", [])))
    if not flag_sets:
        return frozenset(), False
    union = frozenset().union(*flag_sets)
    return union, all(flags == flag_sets[0] for flags in flag_sets)


def _known_model_miss_flags_in_segment(segment: str, declared_flags: frozenset[str]) -> frozenset[str]:
    if "_require_single_active_model_miss_review_block" in segment:
        return declared_flags
    return frozenset(flag for flag in MODEL_MISS_REVIEW_BLOCK_FLAGS if flag in segment)


def _model_miss_triage_accepts_review_block_flags(router_source: str, declared_flags: frozenset[str]) -> frozenset[str]:
    segment = _function_segment(router_source, "_write_model_miss_triage_decision")
    return _known_model_miss_flags_in_segment(segment, declared_flags)


def _event_handler_branch_segment(source: str, event_name: str) -> str:
    pattern = rf'^\s+elif event == "{re.escape(event_name)}":(.*?)(?=^\s+elif event == |^\s+record =|\Z)'
    match = re.search(pattern, source, re.DOTALL | re.MULTILINE)
    return match.group(0) if match else ""


def _pm_review_block_repair_event_accepts_flags(router_source: str, declared_flags: frozenset[str]) -> frozenset[str]:
    branch = _event_handler_branch_segment(router_source, PM_REVIEW_BLOCK_REPAIR_EVENT)
    helper = _function_segment(router_source, "_write_pm_review_block_repair")
    return _known_model_miss_flags_in_segment(branch + "\n" + helper, declared_flags)


def _pm_review_block_repair_event_routes_flags(router: Any, router_source: str) -> frozenset[str]:
    branch = _event_handler_branch_segment(router_source, PM_REVIEW_BLOCK_REPAIR_EVENT)
    helper = _function_segment(router_source, "_write_pm_review_block_repair")
    segment = branch + "\n" + helper
    routed: set[str] = set()
    if "_write_route_mutation" in segment:
        routed.update(str(flag) for flag in getattr(router, "MODEL_MISS_ROUTE_MUTATION_BLOCK_FLAGS", ("node_review_blocked",)))
    if "_write_material_dispatch_repair" in segment:
        routed.update(str(flag) for flag in getattr(router, "MODEL_MISS_MATERIAL_DISPATCH_REPAIR_FLAGS", (MATERIAL_DISPATCH_BLOCK_FLAG,)))
    return frozenset(routed) & MODEL_MISS_REVIEW_BLOCK_FLAGS


def _material_dispatch_frontier_phase_synchronized(router_source: str) -> bool:
    segment = _function_segment(router_source, "_write_material_scan_packets")
    return "execution_frontier.json" in segment or "_set_pre_route_frontier_phase" in segment


def _material_dispatch_card_has_pre_route_material_exception(text: str) -> bool:
    lower = text.lower()
    return "material_scan" in lower and "pre-route" in lower and "is_current_node=false" in lower


def _material_scan_packets_mark_pre_route_not_current_node(router_source: str) -> bool:
    segment = _function_segment(router_source, "_write_material_scan_packets")
    return "is_current_node=False" in segment


def _flatten_json_paths(value: Any, prefix: str = "") -> set[str]:
    paths: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            paths.add(path)
            paths.update(_flatten_json_paths(child, path))
    return paths


def _first_json_block_paths(text: str) -> frozenset[str]:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if not match:
        return frozenset()
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return frozenset()
    return frozenset(_flatten_json_paths(payload))


def _startup_card_prose_paths(text: str) -> frozenset[str]:
    marker = "Your report body must include `external_fact_review` with:"
    if marker not in text:
        return frozenset()
    section = text.split(marker, 1)[1].split("## Report Contract", 1)[0]
    paths: set[str] = set()
    if "reviewer_checked_requirement_ids" in section:
        paths.add(REVIEWER_IDS_PATH)
    return frozenset(paths)


def _function_segment(source: str, function_name: str) -> str:
    match = re.search(rf"^def {re.escape(function_name)}\(.*?(?=^def |\Z)", source, re.DOTALL | re.MULTILINE)
    return match.group(0) if match else ""


def _startup_router_validator_paths(router_source: str) -> frozenset[str]:
    segment = _function_segment(router_source, "_validate_startup_external_fact_review")
    paths = {"external_fact_review"}
    for field_name in re.findall(r'review\.get\("([^"]+)"\)', segment):
        paths.add(f"external_fact_review.{field_name}")
    return frozenset(paths)


def _startup_router_canonical_paths(router_source: str) -> frozenset[str]:
    segment = _function_segment(router_source, "_validate_startup_external_fact_review")
    if f'"{TOP_LEVEL_REVIEWER_IDS_PATH}"' in segment:
        return frozenset({REVIEWER_IDS_PATH})
    return frozenset()


def _pm_control_blocker_router_fields(router_source: str) -> frozenset[str]:
    segment = _function_segment(router_source, "_write_control_blocker_repair_decision")
    fields = set(re.findall(r'decision\.get\("([^"]+)"\)', segment))
    if 'decision["decision"]' in segment or "decision['decision']" in segment:
        fields.add("decision")
    return frozenset(fields)


def _pm_resume_router_fields(router: Any) -> frozenset[str]:
    return frozenset(str(field) for field in getattr(router, "PM_RESUME_DECISION_REQUIRED_BODY_FIELDS", ()))


def _pm_resume_action_contract_fields(router_source: str) -> frozenset[str]:
    delivery_segment = _function_segment(router_source, "_next_system_card_action")
    wait_segment = _function_segment(router_source, "compute_controller_action")
    helper_segment = _function_segment(router_source, "_pm_resume_decision_payload_contract")
    card_dispatch_segment = _function_segment(router_source, "_pm_decision_payload_contract_for_card")
    event_dispatch_segment = _function_segment(router_source, "_role_decision_payload_contract_for_events")
    if "PM_RESUME_DECISION_REQUIRED_BODY_FIELDS" not in helper_segment:
        return frozenset()
    wait_has_contract = (
        '"payload_contract": _pm_resume_decision_payload_contract' in wait_segment
        or (
            "_role_decision_payload_contract_for_events" in wait_segment
            and 'allowed_events == ["pm_resume_recovery_decision_returned"]' in event_dispatch_segment
            and "_pm_resume_decision_payload_contract" in event_dispatch_segment
        )
    )
    if not wait_has_contract:
        return frozenset()
    delivery_has_contract = (
        (
            'entry["card_id"] == "pm.resume_decision"' in delivery_segment
            and 'delivery_extra["payload_contract"] = _pm_resume_decision_payload_contract' in delivery_segment
        )
        or (
            "_pm_decision_payload_contract_for_card" in delivery_segment
            and 'card_id == "pm.resume_decision"' in card_dispatch_segment
            and "_pm_resume_decision_payload_contract" in card_dispatch_segment
        )
    )
    if not delivery_has_contract:
        return frozenset()
    return PM_RESUME_DECISION_REQUIRED_FIELDS


def _pm_control_blocker_card_events(*texts: str) -> frozenset[str]:
    events = set()
    combined = "\n".join(texts)
    if PM_CONTROL_BLOCKER_EVENT in combined:
        events.add(PM_CONTROL_BLOCKER_EVENT)
    if PM_STARTUP_REPAIR_EVENT in combined:
        events.add(PM_STARTUP_REPAIR_EVENT)
    return frozenset(events)


def _pm_control_blocker_allowed_events(router: Any) -> frozenset[str]:
    policy = router._control_blocker_policy(  # noqa: SLF001 - source conformance probe
        "pm_repair_decision_required",
        responsible_role="project_manager",
        event="reviewer_reports_startup_facts",
    )
    raw = policy.get("allowed_resolution_events")
    if not isinstance(raw, list):
        return frozenset()
    return frozenset(str(item) for item in raw)


def _router_rewrites_startup_fact_canonical(router_source: str) -> bool:
    segment = _function_segment(router_source, "_write_startup_fact_report")
    return 'run_root / "startup" / "startup_fact_report.json"' in segment and "write_json(" in segment


def _router_blocks_startup_fact_canonical_alias(router_source: str) -> bool:
    segment = _function_segment(router_source, "_write_startup_fact_report")
    return "canonical startup_fact_report.json" in segment and "report_path" in segment


def _display_status_available_before_startup_fact_review(router_source: str) -> bool:
    segment = _function_segment(router_source, "_next_startup_display_action")
    if not segment:
        return False
    if "startup_activation_approved" in segment:
        return False
    compute_segment = _function_segment(router_source, "compute_controller_action")
    display_index = compute_segment.find("_next_startup_display_action")
    system_card_index = compute_segment.find("_next_system_card_action")
    return display_index != -1 and system_card_index != -1 and display_index < system_card_index


def _startup_repair_request_repeatable_for_new_blocking_report(router_source: str) -> bool:
    segment = _function_segment(router_source, "_record_external_event_unchecked")
    return (
        "repeatable_startup_repair_request" in segment
        and "pm_requests_startup_repair" in segment
        and "startup_fact_reported" in segment
        and "pm_startup_activation_card_delivered" in segment
    )


def _startup_repair_request_tracks_cycle_identity(router_source: str) -> bool:
    segment = _function_segment(router_source, "_write_startup_repair_request")
    return (
        "startup_repair_cycle" in segment
        and "blocked_report_hash" in segment
        and "decision_hash" in segment
        and "startup_repair_requests.json" in segment
    )


def _startup_repair_exact_duplicate_rejected(router_source: str) -> bool:
    segment = _function_segment(router_source, "_write_startup_repair_request")
    return (
        "last_decision_hash" in segment
        and "fresh PM decision" in segment
        and "startup repair request repeats the previous PM decision" in segment
    )


def _startup_role_may_submit_to_canonical_path(card_text: str) -> bool:
    lower = card_text.lower()
    asks_for_startup_fact_report_file = "startup fact report file" in lower
    separates_submission = (
        "startup fact report submission" in lower
        or "raw submission" in lower
        or "must not be the router canonical" in lower
    )
    return asks_for_startup_fact_report_file and not separates_submission


def collect_source_state(project_root: Path) -> State:
    router = _load_router(project_root)
    router_path = project_root / "skills" / "flowpilot" / "assets" / "flowpilot_router.py"
    router_source = router_path.read_text(encoding="utf-8")
    runtime_root = project_root / "skills" / "flowpilot" / "assets" / "runtime_kit"
    startup_card_text = (runtime_root / "cards" / "reviewer" / "startup_fact_check.md").read_text(encoding="utf-8")
    pm_core_text = (runtime_root / "cards" / "roles" / "project_manager.md").read_text(encoding="utf-8")
    reviewer_core_text = (runtime_root / "cards" / "roles" / "human_like_reviewer.md").read_text(encoding="utf-8")
    worker_a_core_text = (runtime_root / "cards" / "roles" / "worker_a.md").read_text(encoding="utf-8")
    worker_b_core_text = (runtime_root / "cards" / "roles" / "worker_b.md").read_text(encoding="utf-8")
    pm_startup_text = (runtime_root / "cards" / "phases" / "pm_startup_activation.md").read_text(encoding="utf-8")
    pm_repair_text = (runtime_root / "cards" / "phases" / "pm_review_repair.md").read_text(encoding="utf-8")
    pm_resume_text = (runtime_root / "cards" / "phases" / "pm_resume_decision.md").read_text(encoding="utf-8")
    pm_material_scan_text = (runtime_root / "cards" / "phases" / "pm_material_scan.md").read_text(encoding="utf-8")
    reviewer_dispatch_text = (runtime_root / "cards" / "reviewer" / "dispatch_request.md").read_text(encoding="utf-8")
    role_output_guidance_texts = (
        startup_card_text,
        pm_core_text,
        reviewer_core_text,
        worker_a_core_text,
        worker_b_core_text,
        pm_repair_text,
    )

    pm_startup_repair_requires_activation = (
        router.EXTERNAL_EVENTS.get(PM_STARTUP_REPAIR_EVENT, {}).get("requires_flag")
        == "pm_startup_activation_card_delivered"
    )
    declared_model_miss_flags = _declared_model_miss_review_block_flags(router, router_source)
    model_miss_card_flags, model_miss_cards_aligned = _model_miss_review_block_card_flag_sets(router)

    return State(
        status="accepted",
        scenario="current_source",
        startup_contract_paths=_contract_fields(project_root, STARTUP_FACT_CONTRACT_ID),
        startup_card_example_paths=_first_json_block_paths(startup_card_text),
        startup_card_prose_paths=_startup_card_prose_paths(startup_card_text),
        startup_router_validator_paths=_startup_router_validator_paths(router_source),
        startup_router_canonical_paths=_startup_router_canonical_paths(router_source),
        pm_control_blocker_allowed_events=_pm_control_blocker_allowed_events(router),
        pm_control_blocker_card_events=_pm_control_blocker_card_events(
            pm_core_text,
            pm_startup_text,
            pm_repair_text,
        ),
        pm_startup_repair_requires_activation_card=pm_startup_repair_requires_activation,
        control_blocker_action_delivers_review_repair_card="card_id=\"pm.review_repair\"" in router_source
        or '"card_id": "pm.review_repair"' in router_source,
        pm_control_blocker_contract_fields=_contract_fields(project_root, PM_CONTROL_BLOCKER_CONTRACT_ID),
        pm_control_blocker_router_fields=_pm_control_blocker_router_fields(router_source),
        pm_control_blocker_card_fields=_first_json_block_paths(pm_repair_text),
        pm_resume_contract_fields=_contract_fields(project_root, PM_RESUME_DECISION_CONTRACT_ID),
        pm_resume_router_fields=_pm_resume_router_fields(router),
        pm_resume_card_fields=_first_json_block_paths(pm_resume_text),
        pm_resume_action_contract_fields=_pm_resume_action_contract_fields(router_source),
        router_rewrites_startup_fact_canonical=_router_rewrites_startup_fact_canonical(router_source),
        startup_role_may_submit_to_canonical_path=_startup_role_may_submit_to_canonical_path(startup_card_text),
        router_blocks_startup_fact_canonical_alias=_router_blocks_startup_fact_canonical_alias(router_source),
        display_requested_cockpit=True,
        display_has_host_receipt=False,
        display_has_explicit_fallback=True,
        display_status_available_before_startup_fact_review=_display_status_available_before_startup_fact_review(
            router_source
        ),
        startup_repair_request_repeatable_for_new_blocking_report=_startup_repair_request_repeatable_for_new_blocking_report(
            router_source
        ),
        startup_repair_request_tracks_cycle_identity=_startup_repair_request_tracks_cycle_identity(
            router_source
        ),
        startup_repair_exact_duplicate_rejected=_startup_repair_exact_duplicate_rejected(router_source),
        role_output_contract_path_hash_pairs=_contract_role_output_path_hash_pairs(project_root),
        role_output_router_path_hash_pairs=_router_role_output_path_hash_pairs(router_source),
        role_output_card_path_hash_pairs=_role_output_card_path_hash_pairs(*role_output_guidance_texts),
        role_output_cards_require_compact_refs=_role_output_cards_require_compact_refs(
            *role_output_guidance_texts
        ),
        role_output_cards_forbid_sha256_aliases=_role_output_cards_forbid_sha256_aliases(
            *role_output_guidance_texts
        ),
        role_output_router_rejects_sha256_aliases=_router_rejects_sha256_aliases(router_source),
        role_output_router_rejects_nested_envelope=_router_rejects_nested_role_output_envelope(
            router_source
        ),
        material_scan_card_requires_file_backed_packet_bodies=_material_scan_card_requires_file_backed_packet_bodies(
            pm_material_scan_text
        ),
        material_scan_router_accepts_file_backed_packet_specs=_material_scan_router_accepts_file_backed_packet_specs(
            router_source
        ),
        material_scan_router_requires_inline_body_text_only=_material_scan_router_requires_inline_body_text_only(
            router_source
        ),
        material_scan_index_forbids_controller_body_reads=_material_scan_index_forbids_controller_body_reads(
            router_source
        ),
        material_dispatch_block_event_registered=_material_dispatch_block_event_registered(router),
        material_dispatch_block_report_writer=_material_dispatch_block_report_writer(router_source),
        material_dispatch_pm_block_cards_reachable=_material_dispatch_pm_block_cards_reachable(router_source),
        material_dispatch_route_memory_tracks_block=_material_dispatch_route_memory_tracks_block(router_source),
        material_dispatch_direct_preflight_required=_material_dispatch_direct_preflight_required(
            router_source
        ),
        declared_reviewer_block_flags=_declared_reviewer_block_flags(router),
        reviewer_block_lane_flags=declared_model_miss_flags | CONTROL_RECHECK_REVIEW_BLOCK_FLAGS,
        model_miss_review_block_event_flags=_model_miss_review_block_event_flags(router),
        model_miss_review_block_card_flags=model_miss_card_flags,
        model_miss_review_block_cards_aligned=model_miss_cards_aligned,
        model_miss_triage_accepts_review_block_flags=_model_miss_triage_accepts_review_block_flags(
            router_source,
            declared_model_miss_flags,
        ),
        pm_review_block_repair_event_accepts_flags=_pm_review_block_repair_event_accepts_flags(
            router_source,
            declared_model_miss_flags,
        ),
        pm_review_block_repair_event_routes_flags=_pm_review_block_repair_event_routes_flags(
            router,
            router_source,
        ),
        material_dispatch_frontier_phase_synchronized=_material_dispatch_frontier_phase_synchronized(
            router_source
        ),
        material_dispatch_card_has_pre_route_material_exception=_material_dispatch_card_has_pre_route_material_exception(
            reviewer_dispatch_text
        ),
        material_scan_packets_mark_pre_route_not_current_node=_material_scan_packets_mark_pre_route_not_current_node(
            router_source
        ),
    )


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEGATIVE_SCENARIOS",
    "PM_CONTROL_BLOCKER_EVENT",
    "PM_CONTROL_BLOCKER_REQUIRED_FIELDS",
    "SCENARIOS",
    "VALID_FIXED_PROTOCOL",
    "Action",
    "State",
    "Tick",
    "Transition",
    "build_workflow",
    "collect_source_state",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "protocol_failures",
    "terminal_predicate",
]
