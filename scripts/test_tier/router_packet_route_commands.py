"""Router packet and route FlowPilot test-tier commands."""

from __future__ import annotations

from .command_builders import TierCommand, _py, _unittest, _unittest_k

ROUTER_PACKET_COMMANDS = (
    _unittest(
        "router_packet_runtime",
        "tests.test_flowpilot_packet_runtime",
        description="Packet runtime contract tests.",
    ),
    _unittest_k(
        "router_packets_material",
        "tests.router_runtime.packets",
        patterns=(
            "material_work_packet",
            "material_scan_accepts",
            "reconcile_current_run_recovers_material_scan_phase",
            "record_event_accepts_material",
            "record_event_rejects_manual_material",
            "material_scan_packet_and_result_relays",
            "material_scan_packet_body_event",
            "formal_work_packet_ack",
            "mail_delivery_receipt",
        ),
        description="Router material packet, scan, and ACK preflight slice.",
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
        "router_packets_current_node_dispatch",
        "tests.router_runtime.packets",
        patterns=(
            "current_node_packet_relay",
            "current_node_worker_packet",
            "unready_leaf",
        ),
        description="Current-node packet dispatch and readiness slice.",
    ),
    _unittest_k(
        "router_packets_current_node_result_audit",
        "tests.router_runtime.packets",
        patterns=(
            "current_node_completion",
            "router_packet_audit",
        ),
        description="Current-node result audit and reviewer-pass slice.",
    ),
    _unittest_k(
        "router_packets_current_node_result_decision",
        "tests.router_runtime.packets",
        patterns=(
            "current_node_result_relay",
            "current_node_result_decision",
            "pm_repair_decision_rejects_parent",
        ),
        description="Current-node result relay, decision, and PM repair slice.",
    ),
    _unittest_k(
        "router_packets_batch_and_grants",
        "tests.router_runtime.packets",
        patterns=(
            "material_scan_existing_results",
            "material_scan_partial_batch",
            "material_scan_full_batch_wait_current_work_names_all_missing_roles",
            "current_node_result_requires_write_grant",
            "current_node_packet_rejects_unresolved",
        ),
        description="Packet batch reconciliation and write-grant guard slice.",
    ),
    TierCommand(
        name="router_packet_result_family",
        command=_py("-m", "unittest", "-v", "tests.router_runtime.packet_result_family"),
        description="Packet-result family durable-envelope reconciliation slice.",
        long_running=True,
        background_recommended=True,
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
    _unittest(
        "router_route_mutation_draft_activation",
        "tests.router_runtime.route_mutation_draft_activation",
        description="Route-mutation draft preservation and activation guard slice.",
    ),
    _unittest(
        "router_route_mutation_model_miss_triage",
        "tests.router_runtime.route_mutation_model_miss_triage",
        description="Route-mutation reviewer-block and model-miss triage slice.",
    ),
    _unittest(
        "router_route_mutation_acceptance_repair",
        "tests.router_runtime.route_mutation_acceptance_repair",
        description="Node acceptance-plan route-repair slice.",
    ),
    _unittest(
        "router_route_mutation_preconditions",
        "tests.router_runtime.route_mutation_preconditions",
        description="Route-mutation precondition and final-ledger guard slice.",
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
    _unittest(
        "router_route_mutation_parent_backward",
        "tests.router_runtime.route_mutation_parent_backward",
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
