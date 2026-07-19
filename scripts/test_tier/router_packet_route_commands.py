"""Router packet and route FlowPilot test-tier commands."""

from __future__ import annotations

from .command_builders import TierCommand, _py, _unittest, _unittest_isolated_k, _unittest_k

ROUTER_PACKET_COMMANDS = (
    _unittest(
        "router_packet_runtime",
        "tests.test_flowpilot_packet_runtime",
        description="Packet runtime contract tests.",
    ),
    _unittest_k(
        "router_packets_generic_ack_mail",
        "tests.router_runtime.packets",
        patterns=("formal_work_packet_ack", "mail_delivery_receipt"),
        description="Current generic packet ACK and mail-delivery receipt guards.",
    ),
    _unittest_k(
        "router_packets_current_node_direct",
        "tests.router_runtime.packets",
        patterns=(
            "current_node_direct",
            "packet_and_result_reject_envelope_aliases",
        ),
        description="Current-node direct relay and alias guard slice.",
    ),
    _unittest_k(
        "router_packets_current_node_dispatch_relay",
        "tests.router_runtime.packets",
        patterns=("test_current_node_packet_relay_uses_router_direct_dispatch",),
        description="Current-node packet direct-dispatch relay slice.",
    ),
    _unittest_k(
        "router_packets_current_node_dispatch_worker_binding",
        "tests.router_runtime.packets",
        patterns=("test_current_node_worker_packet_requires_active_child_skill_binding_projection",),
        description="Current-node packet worker binding projection slice.",
    ),
    _unittest_k(
        "router_packets_current_node_dispatch_unready_leaf",
        "tests.router_runtime.packets",
        patterns=("test_unready_leaf_cannot_receive_current_node_packet",),
        description="Current-node packet unready leaf guard slice.",
    ),
    _unittest_k(
        "router_packets_result_audit_completion",
        "tests.router_runtime.packets",
        patterns=("test_current_node_completion_requires_reviewer_passed_packet_audit",),
        description="Current-node result completion audit slice.",
    ),
    _unittest_k(
        "router_packets_result_audit_reviewer_map",
        "tests.router_runtime.packets",
        patterns=("test_current_node_reviewer_agent_map_cannot_replace_role_binding_ledger",),
        description="Current-node result reviewer-agent map guard slice.",
    ),
    _unittest_k(
        "router_packets_result_audit_rejection",
        "tests.router_runtime.packets",
        patterns=("test_router_packet_audit_rejection_routes_pm_repair_decision",),
        description="Current-node packet audit rejection repair slice.",
    ),
    _unittest_k(
        "router_packets_result_decision_review_card",
        "tests.router_runtime.packets",
        patterns=("test_current_node_result_decision_requires_review_card_after_result_relay",),
        description="Current-node result decision review-card slice.",
    ),
    _unittest_k(
        "router_packets_result_decision_relay",
        "tests.router_runtime.packets",
        patterns=("test_current_node_result_relay_combines_ledger_check_with_relay",),
        description="Current-node result relay and ledger-check slice.",
    ),
    _unittest_k(
        "router_packets_result_decision_pm_repair",
        "tests.router_runtime.packets",
        patterns=("test_pm_repair_decision_rejects_parent_repair_targeting_current_node_packet",),
        description="Current-node result PM repair target guard slice.",
    ),
    _unittest_k(
        "router_packets_grant_result_requires_write",
        "tests.router_runtime.packets",
        patterns=("test_current_node_result_requires_write_grant",),
        description="Current-node result write-grant guard slice.",
    ),
    _unittest_k(
        "router_packets_grant_unresolved_node_entry",
        "tests.router_runtime.packets",
        patterns=("test_current_node_packet_rejects_unresolved_node_entry_self_interrogation",),
        description="Current-node unresolved node-entry packet guard slice.",
    ),
    _unittest(
        "router_cards",
        "tests.router_runtime.cards",
        description="Router runtime card slice.",
    ),
    _unittest(
        "router_ack_return",
        "tests.router_runtime.ack_return",
        description="ACK and return-event router slice.",
    ),
)

ROUTER_ROUTE_COMMANDS = (
    _unittest(
        "router_boundaries",
        "tests.test_flowpilot_router_boundaries",
        description="Router public boundary and import-contract slice.",
    ),
    _unittest_k(
        "router_route_mutation_draft_policy",
        "tests.router_runtime.route_mutation_draft_activation",
        patterns=("test_pm_route_draft_preserves_role_authored_repair_policy_fields",),
        description="Route-mutation draft repair-policy preservation slice.",
    ),
    _unittest_k(
        "router_route_mutation_draft_activation_reviewed",
        "tests.router_runtime.route_mutation_draft_activation",
        patterns=("test_reviewed_route_activation_uses_pm_draft_without_dummy_fallback",),
        description="Route-mutation reviewed activation slice.",
    ),
    _unittest_k(
        "router_route_mutation_draft_missing_active_node",
        "tests.router_runtime.route_mutation_draft_activation",
        patterns=("test_route_activation_rejects_active_node_missing_from_reviewed_route",),
        description="Route-mutation active-node presence guard slice.",
    ),
    _unittest_k(
        "router_route_mutation_model_miss_refs",
        "tests.router_runtime.route_mutation_model_miss_triage",
        patterns=("test_model_backed_model_miss_triage_requires_flowguard_operator_report_refs",),
        description="Route-mutation model-miss FlowGuard reference slice.",
    ),
    _unittest_k(
        "router_route_mutation_model_miss_unlocks",
        "tests.router_runtime.route_mutation_model_miss_triage",
        patterns=("test_model_backed_model_miss_triage_unlocks_review_repair",),
        description="Route-mutation model-miss unlock slice.",
    ),
    _unittest_k(
        "router_route_mutation_model_miss_non_authorizing",
        "tests.router_runtime.route_mutation_model_miss_triage",
        patterns=("test_non_authorizing_model_miss_decision_does_not_unlock_review_repair",),
        description="Route-mutation non-authorizing model-miss guard slice.",
    ),
    _unittest_k(
        "router_route_mutation_model_miss_out_of_scope",
        "tests.router_runtime.route_mutation_model_miss_triage",
        patterns=("test_out_of_scope_model_miss_triage_unlocks_review_repair_with_reason",),
        description="Route-mutation out-of-scope model-miss reason slice.",
    ),
    _unittest_k(
        "router_route_mutation_model_miss_role_work",
        "tests.router_runtime.route_mutation_model_miss_triage",
        patterns=("test_pm_model_miss_followup_uses_generic_role_work_request_channel",),
        description="Route-mutation model-miss follow-up role-work slice.",
    ),
    _unittest_k(
        "router_route_mutation_model_miss_closed_triage",
        "tests.router_runtime.route_mutation_model_miss_triage",
        patterns=("test_review_block_route_mutation_requires_closed_model_miss_triage",),
        description="Route-mutation closed model-miss triage guard slice.",
    ),
    _unittest_k(
        "router_route_mutation_model_miss_delivery",
        "tests.router_runtime.route_mutation_model_miss_triage",
        patterns=("test_reviewer_block_delivers_model_miss_triage_before_review_repair",),
        description="Route-mutation model-miss delivery ordering slice.",
    ),
    _unittest_k(
        "router_route_mutation_model_miss_stale_wait",
        "tests.router_runtime.route_mutation_model_miss_triage",
        patterns=("test_stale_review_block_route_mutation_wait_is_recomputed_before_pm_triage",),
        description="Route-mutation model-miss stale-wait recompute slice.",
    ),
    _unittest_k(
        "router_route_mutation_acceptance_revise",
        "tests.router_runtime.route_mutation_acceptance_repair",
        patterns=("test_node_acceptance_plan_block_can_be_revised_on_same_node",),
        description="Route-mutation acceptance-plan same-node revision slice.",
    ),
    _unittest_k(
        "router_route_mutation_acceptance_model_miss",
        "tests.router_runtime.route_mutation_acceptance_repair",
        patterns=("test_node_acceptance_plan_block_enters_model_miss_repair_path",),
        description="Route-mutation acceptance-plan model-miss repair slice.",
    ),
    _unittest_k(
        "router_route_mutation_preconditions_final_ledger",
        "tests.router_runtime.route_mutation_preconditions",
        patterns=("test_route_mutation_and_final_ledger_have_required_preconditions",),
        description="Route-mutation final-ledger precondition slice.",
    ),
    _unittest_k(
        "router_route_mutation_preconditions_topology_reset",
        "tests.router_runtime.route_mutation_preconditions",
        patterns=("test_route_mutation_requires_topology_and_resets_route_hard_gates",),
        description="Route-mutation topology reset precondition slice.",
    ),
    _unittest_k(
        "router_route_mutation_preconditions_root_gap",
        "tests.router_runtime.route_mutation_preconditions",
        patterns=("test_route_root_node_entry_gap_requires_replanning_not_repair_node",),
        description="Route-mutation root node-entry gap policy slice.",
    ),
    _unittest(
        "router_route_mutation_transactions",
        "tests.router_runtime.route_mutation_transactions",
        description="Route-mutation repeated repair transaction slice.",
    ),
    _unittest(
        "router_route_mutation_topology",
        "tests.router_runtime.route_mutation_topology",
        description="Route-mutation topology strategy slice.",
    ),
    _unittest(
        "router_route_mutation_sibling_replacement",
        "tests.router_runtime.route_mutation_sibling_replacement",
        description="Route-mutation sibling replacement and stale-proof slice.",
    ),
    _unittest_isolated_k(
        "router_route_mutation_parent_backward",
        "tests.router_runtime.route_mutation_parent_backward",
        patterns=(
            "test_parent_backward_targets_require_current_child_completion_ledgers",
            "test_route_mutation_rejects_unvalidated_authority_dict",
            "test_parent_completion_wrong_path_returns_route_authority_repair_feedback",
            "test_unsupported_route_action_alias_is_rejected_without_translation",
            "test_fallback_route_action_payload_is_rejected_without_translation",
            "test_parent_node_requires_backward_replay_before_completion",
            "test_parent_backward_non_continue_decision_mutates_route_and_requires_rerun",
        ),
        description="Route-mutation parent backward replay and repair slice.",
    ),
    _unittest(
        "router_route_mutation_contracts",
        "tests.test_flowpilot_router_runtime_route_mutation",
        description="Route-mutation contract tests.",
    ),
    _unittest(
        "router_user_flow_diagram",
        "tests.test_flowpilot_user_flow_diagram",
        description="User-flow diagram route display tests.",
    ),
)
