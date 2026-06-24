"""Decision-table child declarations for FlowPilot router protocol."""

from __future__ import annotations

STARTUP_ANSWER_ENUMS = {}

STARTUP_ANSWER_BOOLEANS = {
    "background_collaboration_authorized",
}

GATE_DECISION_REQUIRED_FIELDS = (
    "gate_decision_version",
    "gate_id",
    "gate_kind",
    "owner_role",
    "risk_type",
    "gate_strength",
    "decision",
    "blocking",
    "required_evidence",
    "evidence_refs",
    "reason",
    "next_action",
    "contract_self_check",
)

PM_PRIOR_PATH_CONTEXT_REVIEW_REQUIRED_FIELDS = (
    "reviewed",
    "source_paths",
    "completed_nodes_considered",
    "superseded_nodes_considered",
    "stale_evidence_considered",
    "prior_blocks_or_experiments_considered",
    "impact_on_decision",
    "controller_summary_used_as_evidence",
)

PM_RESUME_CONTROLLER_REMINDER_REQUIRED_FIELDS = (
    "controller_only",
    "controller_may_read_sealed_bodies",
    "controller_may_infer_from_chat_history",
    "controller_may_advance_or_close_route",
)

PM_RESUME_DECISION_ALLOWED_VALUES = {
    "break_glass",
    "continue_current_packet_loop",
    "request_sender_reissue",
    "restore_or_replace_roles_from_memory",
    "create_repair_or_route_mutation_node",
    "stop_for_user_or_environment",
    "close_after_final_ledger_and_terminal_replay",
}

PM_RESUME_DECISION_REQUIRED_BODY_FIELDS = (
    "decision_owner",
    "decision",
    "explicit_recovery_evidence_recorded",
    *(f"prior_path_context_review.{field}" for field in PM_PRIOR_PATH_CONTEXT_REVIEW_REQUIRED_FIELDS),
    *(f"controller_reminder.{field}" for field in PM_RESUME_CONTROLLER_REMINDER_REQUIRED_FIELDS),
)

PM_PARENT_SEGMENT_DECISION_ALLOWED_VALUES = {
    "continue",
    "repair_existing_child",
    "add_sibling_child",
    "rebuild_child_subtree",
    "bubble_to_parent",
    "pm_stop",
}

PM_PARENT_SEGMENT_DECISION_REQUIRED_BODY_FIELDS = (
    "decision_owner",
    "decision",
    *(f"prior_path_context_review.{field}" for field in PM_PRIOR_PATH_CONTEXT_REVIEW_REQUIRED_FIELDS),
)

PM_TERMINAL_CLOSURE_DECISION_ALLOWED_VALUES = {
    "approve_terminal_closure",
}

PM_TERMINAL_CLOSURE_DECISION_REQUIRED_BODY_FIELDS = (
    "approved_by_role",
    "decision",
    *(f"prior_path_context_review.{field}" for field in PM_PRIOR_PATH_CONTEXT_REVIEW_REQUIRED_FIELDS),
)

PM_SUGGESTION_FINAL_DISPOSITIONS = {
    "adopt_now",
    "repair_or_reissue",
    "mutate_route",
    "defer_to_named_node",
    "reject_with_reason",
    "waive_with_authority",
    "stop_for_user",
    "record_for_flowpilot_maintenance",
}

PM_SUGGESTION_CLOSURE_STATUSES_BY_DISPOSITION = {
    "adopt_now": {"closed"},
    "repair_or_reissue": {"closed"},
    "mutate_route": {"closed"},
    "defer_to_named_node": {"deferred_to_named_node", "closed"},
    "reject_with_reason": {"closed"},
    "waive_with_authority": {"closed"},
    "stop_for_user": {"stopped_for_user", "closed"},
    "record_for_flowpilot_maintenance": {"closed"},
}

PM_SUGGESTION_WORKER_ROLES = {"worker"}

PM_SUGGESTION_FLOWGUARD_OPERATOR_ROLES = {"flowguard_operator"}

SELF_INTERROGATION_SCOPES = {
    "startup",
    "product_architecture",
    "node_entry",
    "repair",
    "completion",
    "role_result",
}

SELF_INTERROGATION_HARD_SEVERITIES = {"hard_blocker", "current_gate_blocker"}

SELF_INTERROGATION_FINAL_DISPOSITIONS = {
    *PM_SUGGESTION_FINAL_DISPOSITIONS,
    "incorporated_into_artifact",
    "entered_pm_suggestion_ledger",
    "no_action_needed",
}

GATE_DECISION_ALLOWED_KINDS = {
    "quality",
    "repair",
    "parent_replay",
    "resource",
    "stage_advance",
    "completion",
    "other",
}

GATE_DECISION_ALLOWED_OWNER_ROLES = {
    "project_manager",
    "human_like_reviewer",
    "flowguard_operator",
}

GATE_DECISION_ALLOWED_RISKS = {
    "product_state",
    "visual_quality",
    "mixed_product_visual",
    "documentation_only",
    "composition",
    "resource",
    "control_state",
    "none",
}

GATE_DECISION_ALLOWED_STRENGTHS = {
    "hard",
    "soft",
    "advisory",
    "skip_with_reason",
}

GATE_DECISION_ALLOWED_DECISIONS = {
    "pass",
    "block",
    "waive",
    "skip",
    "repair_local",
    "mutate_route",
}

GATE_DECISION_ALLOWED_EVIDENCE_KINDS = {
    "file",
    "command",
    "screenshot",
    "model_result",
    "reviewer_walkthrough",
    "state_ref",
    "none",
}

GATE_DECISION_ALLOWED_NEXT_ACTIONS = {
    "continue",
    "local_repair",
    "route_mutation",
    "collect_evidence",
    "reviewer_recheck",
    "stop",
}

GATE_DECISION_SEMANTIC_OVERREACH_FIELDS = {
    "router_approved_semantic_sufficiency",
    "router_semantic_decision",
    "router_sufficiency_decision",
    "semantic_sufficiency_passed_by_router",
    "controller_approved_gate",
}

RUNTIME_ROLE_KEYS = (
    "project_manager",
    "human_like_reviewer",
    "flowguard_operator",
    "worker",
)

ROLE_CARD_KEYS = ("controller", *RUNTIME_ROLE_KEYS)
