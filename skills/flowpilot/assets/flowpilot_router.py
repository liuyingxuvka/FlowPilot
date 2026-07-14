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
from flowpilot_router_control_transactions import (
    CONTROL_TRANSACTION_COMMIT_TARGETS,
    CONTROL_TRANSACTION_EVENT_USAGES,
    CONTROL_TRANSACTION_OUTCOME_POLICIES,
    CONTROL_TRANSACTION_PACKET_AUTHORITY_POLICIES,
    CONTROL_TRANSACTION_REPAIR_POLICIES,
)
from flowpilot_router_protocol_dispatch_policy import *
from flowpilot_router_route_frontier_policy_registry import (
    ROUTE_ACTION_POLICY_CARD_TO_ACTION,
    ROUTE_ACTION_POLICY_EVENT_TO_ACTION,
    ROUTE_ACTION_POLICY_PARENT_CLOSURE_ACTIONS,
    ROUTE_ACTION_POLICY_REQUIRED_BOOL_FLAGS,
    ROUTE_ACTION_POLICY_ROUTE_MOVEMENT_ACTIONS,
)


_ROUTER_MODULE = sys.modules.get(__name__)
if _ROUTER_MODULE is None:
    _ROUTER_MODULE = ModuleType(__name__)
    sys.modules[__name__] = _ROUTER_MODULE
_ROUTER_MODULE.__dict__.update(globals())
install_facade_exports(_ROUTER_MODULE, globals())
_ROUTER_MODULE.__dict__.update(globals())


CARD_RETURN_EVENT_BYPASS_EVENTS = {
    "manual_resume_requested",
    "controller_reports_role_liveness_fault",
    "controller_reports_role_no_output",
    "host_records_manual_resume_binding",
    "user_requests_run_stop",
    "user_requests_run_cancel",
}

STARTUP_REVIEW_BEGIN_JOIN_EVENTS = set()

PRE_REVIEW_STARTUP_CARD_IDS = {
    "pm.core",
    "pm.output_contract_catalog",
    "pm.role_work_request",
    "pm.phase_map",
    "pm.startup_intake",
}

STARTUP_ASYNC_CARD_IDS = {
    "pm.core",
    "pm.output_contract_catalog",
    "pm.role_work_request",
    "pm.phase_map",
    "pm.startup_intake",
}


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
    ("product_architecture", "Product architecture", "pm_product_architecture_card_delivered"),
    ("root_contract", "Root contract", "pm_root_contract_card_delivered"),
    ("dependency_policy", "Dependency policy", "pm_dependency_policy_card_delivered"),
    ("child_skill_gate_manifest", "Child-skill gates", "pm_child_skill_gate_manifest_card_delivered"),
)


_ROUTER_MODULE.__dict__.update(globals())


if __name__ == "__main__":
    raise SystemExit(main())
