"""Prompt-isolated FlowPilot router.

This module is the new FlowPilot control entrypoint. It is deliberately small:
it reads the current run state, returns one JSON action envelope, and verifies
that every bootloader/controller action was first authorized by the router.

The router is not a project manager. It does not decide whether evidence is
sufficient, whether a route is good, or whether a worker succeeded. It only
decides which system card or packet-delivery gate is currently allowed.
"""

from __future__ import annotations

from flowpilot_router_facade_imports import *
from flowpilot_router_protocol_dispatch_policy import *


_ROUTER_MODULE = sys.modules.get(__name__)
if _ROUTER_MODULE is None:
    _ROUTER_MODULE = ModuleType(__name__)
    sys.modules[__name__] = _ROUTER_MODULE
_ROUTER_MODULE.__dict__.update(globals())
install_facade_exports(_ROUTER_MODULE, globals())
_ROUTER_MODULE.__dict__.update(globals())


CARD_RETURN_EVENT_BYPASS_EVENTS = {
    "heartbeat_or_manual_resume_requested",
    "controller_reports_role_liveness_fault",
    "controller_reports_role_no_output",
    "host_records_heartbeat_binding",
    "user_requests_run_stop",
    "user_requests_run_cancel",
}

STARTUP_REVIEW_BEGIN_JOIN_EVENTS = {
    "reviewer_reports_startup_facts",
}

PRE_REVIEW_STARTUP_CARD_IDS = {
    "pm.core",
    "pm.output_contract_catalog",
    "pm.role_work_request",
    "pm.phase_map",
    "pm.startup_intake",
}

STARTUP_ASYNC_CARD_IDS = {
    "reviewer.startup_fact_check",
    "pm.core",
    "pm.output_contract_catalog",
    "pm.role_work_request",
    "pm.phase_map",
    "pm.startup_intake",
    "pm.startup_activation",
}

REVIEWER_STARTUP_FACT_CARD_ID = "reviewer.startup_fact_check"


CURRENT_SCOPE_REVIEWER_CARD_IDS = {
    "reviewer.worker_result_review",
}

CURRENT_SCOPE_REVIEW_EVENTS = {
    "current_node_reviewer_passes_result",
    "current_node_reviewer_blocks_result",
}


_FORBIDDEN_STARTUP_INTAKE_BODY_KEYS = {
    "body_text",
    "content",
    "prompt_text",
    "raw_body",
    "raw_text",
    "request_text",
    "text",
    "user_prompt",
    "user_request_text",
}


PRE_ROUTE_PHASE_ITEMS = (
    ("material_understanding", "Material understanding", "pm_material_understanding_card_delivered"),
    ("product_architecture", "Product architecture", "pm_product_architecture_card_delivered"),
    ("root_contract", "Root contract", "pm_root_contract_card_delivered"),
    ("dependency_policy", "Dependency policy", "pm_dependency_policy_card_delivered"),
    ("child_skill_gate_manifest", "Child-skill gates", "pm_child_skill_gate_manifest_card_delivered"),
)


CONTROL_TRANSACTION_EVENT_USAGES = {
    "recorded_event",
    "wait",
    "rerun_target",
    "repair_outcome",
    "reconcile",
}
CONTROL_TRANSACTION_COMMIT_TARGETS = {
    "frontier",
    "run_state",
    "status_summary",
    "packet_ledger",
    "blocker_index",
    "repair_transaction",
    "repair_transaction_index",
    "route",
    "stale_evidence",
    "dispatch_index",
}
CONTROL_TRANSACTION_OUTCOME_POLICIES = {
    "single_event",
    "three_distinct_outcomes",
    "quarantine_invalid",
}
CONTROL_TRANSACTION_LEGACY_POLICIES = {
    "block_if_invalid",
    "quarantine_invalid",
}
CONTROL_TRANSACTION_PACKET_AUTHORITY_POLICIES = {
    True,
    False,
    "when_reviewing_packet_result",
    "when_repair_rechecks_packet_result",
    "audit_existing_only",
}
CONTROL_TRANSACTION_REPAIR_POLICIES = {
    True,
    False,
    "when_mutation_resolves_control_blocker",
    "audit_existing_only",
}


ROUTE_ACTION_POLICY_REQUIRED_BOOL_FLAGS = (
    "router_must_compute_before_pm_decision",
    "router_must_validate_before_event_acceptance",
    "router_must_validate_before_commit",
    "pm_may_choose_only_from_legal_next_actions",
)


ROUTE_ACTION_POLICY_EVENT_TO_ACTION = {
    "pm_builds_parent_backward_targets": "build_parent_backward_targets",
    "reviewer_passes_parent_backward_replay": "review_parent_backward_replay",
    "reviewer_blocks_parent_backward_replay": "review_parent_backward_replay",
    "pm_records_parent_segment_decision": "record_parent_segment_decision",
    "pm_completes_parent_node_from_backward_replay": "complete_parent_node",
    "pm_mutates_route_after_review_block": "mutate_route",
    "pm_approves_terminal_closure": "terminal_closure",
}


ROUTE_ACTION_POLICY_CARD_TO_ACTION = {
    "pm.parent_backward_targets": "build_parent_backward_targets",
    "reviewer.parent_backward_replay": "review_parent_backward_replay",
    "pm.parent_segment_decision": "record_parent_segment_decision",
    "pm.closure": "terminal_closure",
}


ROUTE_ACTION_POLICY_PARENT_CLOSURE_ACTIONS = {
    "build_parent_backward_targets",
    "review_parent_backward_replay",
    "record_parent_segment_decision",
    "complete_parent_node",
}


ROUTE_ACTION_POLICY_ROUTE_MOVEMENT_ACTIONS = set(ROUTE_ACTION_POLICY_EVENT_TO_ACTION.values())


_ROUTER_MODULE.__dict__.update(globals())


if __name__ == "__main__":
    raise SystemExit(main())
