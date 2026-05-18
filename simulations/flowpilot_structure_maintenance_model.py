"""FlowGuard StructureMesh/TestMesh plans for FlowPilot maintenance splits."""

from __future__ import annotations

from dataclasses import replace

from flowguard import (
    CodeStructureRecommendation,
    EVIDENCE_ABSTRACT_GREEN,
    EVIDENCE_CONFORMANCE_GREEN,
    ModuleStructureEvidence,
    PublicEntrypointEvidence,
    STRUCTURE_SCOPE_RELEASE,
    STRUCTURE_SCOPE_ROUTINE,
    TEST_SCOPE_RELEASE,
    TEST_SCOPE_ROUTINE,
    TEST_STATUS_FAILED,
    TEST_STATUS_PASSED,
    TEST_STATUS_TIMEOUT,
    StructureMeshPlan,
    StructurePartitionItem,
    TestMeshPlan,
    TestPartitionItem,
    TestTargetSplitDerivation,
    TestSuiteEvidence,
    TargetModuleRecommendation,
)


ROUTER_PUBLIC_ENTRYPOINTS = (
    PublicEntrypointEvidence(
        "flowpilot_router_public_api",
        old_path="skills/flowpilot/assets/flowpilot_router.py",
        new_path="skills/flowpilot/assets/flowpilot_router.py",
        parity_evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        evidence_path="simulations/flowpilot_structure_maintenance_results.json",
        release_required=True,
    ),
    PublicEntrypointEvidence(
        "flowpilot_router_cli",
        entrypoint_type="cli",
        old_path="python skills/flowpilot/assets/flowpilot_router.py",
        new_path="python skills/flowpilot/assets/flowpilot_router.py",
        parity_evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        evidence_path="simulations/flowpilot_structure_maintenance_results.json",
        release_required=True,
    ),
)

ROUTER_STRUCTURE_PARTITIONS = (
    StructurePartitionItem(
        "route_state_root",
        item_type="state",
        owner_module_id="router_facade",
        ownership="parent",
        description="Root run-state coordination remains visible through the router skeleton.",
    ),
    StructurePartitionItem(
        "router_public_api_allowlist",
        item_type="public_entrypoint",
        owner_module_id="router_facade",
        ownership="parent",
        public_surface=True,
        description="The router skeleton exposes only the supported CLI/runtime allowlist.",
    ),
    StructurePartitionItem(
        "router_owner_export_registry",
        item_type="config",
        owner_module_id="facade_export_manifest",
        old_path="flowpilot_router hand-written compatibility wrappers",
        new_path="flowpilot_router_facade_export_manifest",
    ),
    StructurePartitionItem(
        "router_owner_export_manifest_shards",
        item_type="config",
        owner_module_id="facade_export_manifest",
        old_path="flowpilot_router_facade_export_manifest monolithic registry",
        new_path="flowpilot_router_facade_export_manifest_*",
    ),
    StructurePartitionItem(
        "router_owner_export_installer",
        item_type="function_cluster",
        owner_module_id="facade_exports",
        old_path="flowpilot_router hand-written compatibility wrappers",
        new_path="flowpilot_router_facade_exports",
    ),
    StructurePartitionItem(
        "external_event_intake",
        item_type="function_cluster",
        owner_module_id="external_events",
        public_surface=True,
        old_path="flowpilot_router._record_external_event_unchecked",
        new_path="flowpilot_router_event_dispatcher",
    ),
    StructurePartitionItem(
        "daemon_tick_and_status",
        item_type="function_cluster",
        owner_module_id="daemon_loop",
        old_path="flowpilot_router._router_daemon_tick/run_router_daemon",
        new_path="flowpilot_router_daemon_runtime",
    ),
    StructurePartitionItem(
        "startup_bootloader_actions",
        item_type="function_cluster",
        owner_module_id="bootloader",
        old_path="flowpilot_router.apply_bootloader_action",
        new_path="flowpilot_router_startup_bootloader",
    ),
    StructurePartitionItem(
        "startup_intake_and_display",
        item_type="function_cluster",
        owner_module_id="startup_intake_display",
        old_path="flowpilot_router_startup_flow intake/display helpers",
        new_path="flowpilot_router_startup_intake + flowpilot_router_startup_display",
    ),
    StructurePartitionItem(
        "startup_resume_and_recovery",
        item_type="function_cluster",
        owner_module_id="startup_role_recovery",
        old_path="flowpilot_router_startup_flow resume and role-recovery helpers",
        new_path="flowpilot_router_startup_role_recovery",
    ),
    StructurePartitionItem(
        "startup_closure_and_fact_boundary",
        item_type="function_cluster",
        owner_module_id="startup_closure_fact_boundary",
        old_path="flowpilot_router_startup_flow closure and fact-boundary helpers",
        new_path="flowpilot_router_startup_closure + flowpilot_router_startup_fact_boundary",
    ),
    StructurePartitionItem(
        "router_protocol_catalog",
        item_type="config",
        owner_module_id="protocol_catalog",
        old_path="flowpilot_router schema/action/event/gate catalogs",
        new_path="flowpilot_router_protocol_catalog",
    ),
    StructurePartitionItem(
        "pm_role_work_next_actions",
        item_type="function_cluster",
        owner_module_id="pm_role_work",
        old_path="flowpilot_router._next_pm_role_work_request_action",
        new_path="flowpilot_router_work_packets",
    ),
    StructurePartitionItem(
        "pm_role_work_polish_children",
        item_type="function_cluster",
        owner_module_id="pm_role_work",
        old_path="flowpilot_router_work_packets_pm_role mixed PM role-work helpers",
        new_path="flowpilot_router_work_packets_pm_role_*",
    ),
    StructurePartitionItem(
        "terminal_ledger_writers",
        item_type="function_cluster",
        owner_module_id="terminal_ledger",
        old_path="flowpilot_router._write_final_route_wide_ledger",
        new_path="flowpilot_router_terminal_ledger",
    ),
    StructurePartitionItem(
        "terminal_ledger_polish_children",
        item_type="function_cluster",
        owner_module_id="terminal_ledger",
        old_path="flowpilot_router_terminal_ledger mixed terminal helpers",
        new_path="flowpilot_router_terminal_ledger_*",
    ),
    StructurePartitionItem(
        "controller_receipt_polish_children",
        item_type="function_cluster",
        owner_module_id="controller_scheduler",
        old_path="flowpilot_router_controller_scheduler_receipts mixed receipt helpers",
        new_path="flowpilot_router_controller_scheduler_receipts_*",
    ),
    StructurePartitionItem(
        "action_factory_polish_children",
        item_type="function_cluster",
        owner_module_id="action_factory",
        old_path="flowpilot_router_action_factory mixed action/gate helpers",
        new_path="flowpilot_router_action_factory_*",
    ),
    StructurePartitionItem(
        "control_blocker_repair",
        item_type="function_cluster",
        owner_module_id="control_blockers",
        old_path="flowpilot_router._write_control_blocker_repair_decision",
        new_path="flowpilot_router_events_repair",
    ),
    StructurePartitionItem(
        "packet_prompt_assets",
        item_type="prompt",
        owner_module_id="packet_runtime_contracts",
        old_path="packet_runtime_contracts inline packet/result/output-contract text",
        new_path="runtime_kit/prompts/packets",
    ),
    StructurePartitionItem(
        "packet_runtime_progress",
        item_type="function_cluster",
        owner_module_id="packet_runtime_progress",
        old_path="packet_runtime progress/status helpers",
        new_path="packet_runtime_progress",
    ),
    StructurePartitionItem(
        "packet_runtime_creation",
        item_type="function_cluster",
        owner_module_id="packet_runtime_creation",
        old_path="packet_runtime packet creation and handoff helpers",
        new_path="packet_runtime_creation",
    ),
    StructurePartitionItem(
        "packet_runtime_results",
        item_type="function_cluster",
        owner_module_id="packet_runtime_results",
        old_path="packet_runtime result write/read helpers",
        new_path="packet_runtime_results",
    ),
    StructurePartitionItem(
        "packet_runtime_audit",
        item_type="function_cluster",
        owner_module_id="packet_runtime_audit",
        old_path="packet_runtime ledger/audit helpers",
        new_path="packet_runtime_audit",
    ),
    StructurePartitionItem(
        "packet_runtime_cli",
        item_type="function_cluster",
        owner_module_id="packet_runtime_cli",
        old_path="packet_runtime command parsing and CLI",
        new_path="packet_runtime_cli",
    ),
    StructurePartitionItem(
        "card_runtime_io",
        item_type="function_cluster",
        owner_module_id="card_runtime_io",
        old_path="card_runtime path/hash/json helpers",
        new_path="card_runtime_io",
    ),
    StructurePartitionItem(
        "card_runtime_ledgers",
        item_type="function_cluster",
        owner_module_id="card_runtime_ledgers",
        old_path="card_runtime ledger helpers",
        new_path="card_runtime_ledgers",
    ),
    StructurePartitionItem(
        "card_runtime_envelopes",
        item_type="function_cluster",
        owner_module_id="card_runtime_envelopes",
        old_path="card_runtime envelope validation helpers",
        new_path="card_runtime_envelopes",
    ),
    StructurePartitionItem(
        "card_runtime_ack",
        item_type="function_cluster",
        owner_module_id="card_runtime_ack",
        old_path="card_runtime single-card ACK helpers",
        new_path="card_runtime_ack",
    ),
    StructurePartitionItem(
        "card_runtime_bundle",
        item_type="function_cluster",
        owner_module_id="card_runtime_bundle",
        old_path="card_runtime bundle ACK helpers",
        new_path="card_runtime_bundle",
    ),
    StructurePartitionItem(
        "user_flow_source",
        item_type="function_cluster",
        owner_module_id="user_flow_source",
        old_path="flowpilot_user_flow_diagram source loading helpers",
        new_path="flowpilot_user_flow_source",
    ),
    StructurePartitionItem(
        "user_flow_tree",
        item_type="function_cluster",
        owner_module_id="user_flow_tree",
        old_path="flowpilot_user_flow_diagram tree/topology helpers",
        new_path="flowpilot_user_flow_tree",
    ),
    StructurePartitionItem(
        "user_flow_stage",
        item_type="function_cluster",
        owner_module_id="user_flow_stage",
        old_path="flowpilot_user_flow_diagram stage classification helpers",
        new_path="flowpilot_user_flow_stage",
    ),
    StructurePartitionItem(
        "user_flow_mermaid",
        item_type="function_cluster",
        owner_module_id="user_flow_mermaid",
        old_path="flowpilot_user_flow_diagram Mermaid rendering helpers",
        new_path="flowpilot_user_flow_mermaid",
    ),
    StructurePartitionItem(
        "user_flow_markdown",
        item_type="function_cluster",
        owner_module_id="user_flow_markdown",
        old_path="flowpilot_user_flow_diagram chat Markdown helpers",
        new_path="flowpilot_user_flow_markdown",
    ),
)

ROUTER_STRUCTURE_MODULES = (
    ModuleStructureEvidence(
        "router_facade",
        path="skills/flowpilot/assets/flowpilot_router.py",
        layer="parent",
        owns_functions=(),
        owns_state=("route_state_root",),
        behavior_contracts=("public API allowlist", "CLI skeleton", "owner-export registry installation"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "facade_exports",
        path="skills/flowpilot/assets/flowpilot_router_facade_exports.py",
        owns_functions=("install_facade_exports", "resolve_facade_export"),
        dependencies=("facade_export_manifest", "router_facade"),
        behavior_contracts=("owner lookup resolver", "obsolete hand-written wrapper removal"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "facade_export_manifest",
        path="skills/flowpilot/assets/flowpilot_router_facade_export_manifest.py",
        owns_config=("router_owner_export_registry", "router_owner_export_manifest_shards"),
        behavior_contracts=("transitional owner lookup registry", "public export allowlist authority"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "facade_export_manifest_actions",
        path="skills/flowpilot/assets/flowpilot_router_facade_export_manifest_actions.py",
        owns_config=("router_owner_export_manifest_actions",),
        behavior_contracts=("action export manifest shard",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "facade_export_manifest_controller",
        path="skills/flowpilot/assets/flowpilot_router_facade_export_manifest_controller.py",
        owns_config=("router_owner_export_manifest_controller",),
        behavior_contracts=("controller export manifest shard",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "facade_export_manifest_route",
        path="skills/flowpilot/assets/flowpilot_router_facade_export_manifest_route.py",
        owns_config=("router_owner_export_manifest_route",),
        behavior_contracts=("route export manifest shard",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "facade_export_manifest_startup",
        path="skills/flowpilot/assets/flowpilot_router_facade_export_manifest_startup.py",
        owns_config=("router_owner_export_manifest_startup",),
        behavior_contracts=("startup export manifest shard",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "facade_export_manifest_terminal_work",
        path="skills/flowpilot/assets/flowpilot_router_facade_export_manifest_terminal_work.py",
        owns_config=("router_owner_export_manifest_terminal_work",),
        behavior_contracts=("terminal/work-packet export manifest shard",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "router_cli",
        path="skills/flowpilot/assets/flowpilot_router_cli.py",
        owns_functions=("main", "parse_args"),
        dependencies=("router_facade",),
        behavior_contracts=("CLI command surface", "JSON error envelope"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "controller_runtime",
        path="skills/flowpilot/assets/flowpilot_router_controller_runtime.py",
        owns_functions=("next_action", "apply_action", "record_external_event", "run_until_wait"),
        dependencies=("router_facade", "external_events"),
        behavior_contracts=("high-level runtime API allowlist", "controller action loop"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "artifact_validation",
        path="skills/flowpilot/assets/flowpilot_router_artifact_validation.py",
        owns_functions=("validate_artifact",),
        dependencies=("router_facade",),
        behavior_contracts=("artifact validation public API", "hash validation"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "external_events",
        path="skills/flowpilot/assets/flowpilot_router_event_dispatcher.py",
        owns_functions=("record_external_event_family", "settle_external_event_family"),
        owns_state=("event_log", "wait_action_status"),
        owns_side_effects=("event_ledger_write", "wait_action_close_write"),
        behavior_contracts=("event names", "wait/idempotency facade spine"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "daemon_loop",
        path="skills/flowpilot/assets/flowpilot_router_daemon_runtime.py",
        owns_functions=("router_daemon_tick", "run_router_daemon_loop"),
        owns_state=("daemon_status_record", "standby_snapshot"),
        owns_side_effects=("daemon_status_write",),
        behavior_contracts=("daemon startup", "standby status"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "bootloader",
        path="skills/flowpilot/assets/flowpilot_router_startup_bootloader.py",
        owns_functions=("apply_bootloader_action", "compute_bootloader_action"),
        owns_state=("bootloader_rows", "startup_review_projection"),
        owns_side_effects=("bootloader_row_write",),
        behavior_contracts=("startup ordering", "question stop boundary"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "startup_intake_display",
        path="skills/flowpilot/assets/flowpilot_router_startup_intake.py",
        owns_functions=("validate_startup_answer_payload", "write_startup_display_plan"),
        owns_state=("startup_answers", "startup_display"),
        owns_side_effects=("startup_answer_write", "startup_display_write"),
        behavior_contracts=("startup answer validation", "display projection"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "startup_role_recovery",
        path="skills/flowpilot/assets/flowpilot_router_startup_role_recovery.py",
        owns_functions=("next_resume_action", "next_role_recovery_action"),
        owns_state=("resume_role_recovery", "continuation_bindings"),
        owns_side_effects=("role_recovery_write",),
        behavior_contracts=("resume re-entry", "role recovery persistence"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "startup_closure_fact_boundary",
        path="skills/flowpilot/assets/flowpilot_router_startup_closure.py",
        owns_functions=("startup_closure_reconciliation_status", "write_startup_fact_report"),
        owns_state=("startup_closure_reconciliation", "startup_fact_boundary"),
        owns_side_effects=("startup_fact_write", "closure_reconciliation_write"),
        behavior_contracts=("startup closure reconciliation", "fact-boundary audit"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "protocol_catalog",
        path="skills/flowpilot/assets/flowpilot_router_protocol_catalog.py",
        owns_functions=(
            "_gate_contract_for_id",
            "_gate_contract_for_card",
            "_gate_contract_for_event",
        ),
        owns_config=("router_protocol_catalog",),
        behavior_contracts=(
            "schema/action/event catalogs",
            "gate contract lookup",
            "model gate alias tables",
        ),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "controller_scheduler",
        path="skills/flowpilot/assets/flowpilot_router_controller_scheduler.py",
        owns_functions=(),
        owns_state=("controller_action_rows", "controller_receipts"),
        owns_side_effects=(),
        dependencies=("router_facade",),
        behavior_contracts=("controller action and receipt reconciliation compatibility",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "controller_receipt_writes",
        path="skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_writes.py",
        owns_functions=("_write_controller_action_entry", "_write_controller_receipt"),
        owns_side_effects=("controller_action_write", "controller_receipt_write"),
        dependencies=("controller_scheduler", "router_facade"),
        behavior_contracts=("controller action and receipt writes",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "controller_receipt_effects",
        path="skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_effects.py",
        owns_functions=("_apply_stateful_receipt_postcondition", "_apply_done_controller_receipt_effects"),
        dependencies=("controller_scheduler", "router_facade"),
        behavior_contracts=("controller receipt postcondition effects",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "controller_receipt_pending",
        path="skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_pending.py",
        owns_functions=("_reconcile_pending_controller_action_receipt", "_clear_pending_after_reconciled_controller_receipt"),
        dependencies=("controller_receipt_effects", "router_facade"),
        behavior_contracts=("pending Controller action receipt reconciliation",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "controller_receipt_scheduled",
        path="skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_scheduled.py",
        owns_functions=("_reconcile_scheduled_controller_action_receipts", "_backfill_scheduler_row_from_reconciled_controller_action"),
        dependencies=("controller_receipt_pending", "router_facade"),
        behavior_contracts=("scheduled Controller action reconciliation and scheduler backfill",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "action_factory",
        path="skills/flowpilot/assets/flowpilot_router_action_factory.py",
        owns_functions=("make_action", "_apply_dispatch_recipient_gate"),
        owns_state=("controller_action_envelope", "dispatch_recipient_gate"),
        dependencies=("router_facade",),
        behavior_contracts=("action envelope construction and dispatch-recipient gating",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "action_factory_reconciliation",
        path="skills/flowpilot/assets/flowpilot_router_action_factory_reconciliation.py",
        owns_functions=("_current_scope_pre_review_reconciliation_action", "_apply_formal_work_packet_ack_preflight"),
        dependencies=("action_factory", "router_facade"),
        behavior_contracts=("scope reconciliation and formal packet ACK preflight",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "action_factory_dispatch",
        path="skills/flowpilot/assets/flowpilot_router_action_factory_dispatch.py",
        owns_functions=("_apply_dispatch_recipient_gate", "_dispatch_gate_wait_action"),
        dependencies=("action_factory_reconciliation", "router_facade"),
        behavior_contracts=("dispatch recipient gate and blocker construction",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "action_factory_envelope",
        path="skills/flowpilot/assets/flowpilot_router_action_factory_envelope.py",
        owns_functions=("make_action", "append_history"),
        dependencies=("action_factory_dispatch", "router_facade"),
        behavior_contracts=("action envelope and Controller user-reporting policy",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "pm_role_work",
        path="skills/flowpilot/assets/flowpilot_router_work_packets.py",
        owns_functions=("next_pm_role_work_request_action", "write_pm_role_work_request"),
        owns_state=("pm_role_work_requests", "pm_role_work_results"),
        owns_side_effects=("packet_or_action_write",),
        behavior_contracts=("role authority", "packet contracts"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "pm_role_work_gates",
        path="skills/flowpilot/assets/flowpilot_router_work_packets_pm_role_gates.py",
        owns_functions=("_pm_role_work_gate_mappings_for_decision", "_apply_pm_role_work_gate_mappings"),
        dependencies=("pm_role_work", "router_facade"),
        behavior_contracts=("PM role-work gate mapping and targeted result contracts",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "pm_role_work_writes",
        path="skills/flowpilot/assets/flowpilot_router_work_packets_pm_role_writes.py",
        owns_functions=("_write_pm_role_work_request", "_write_role_work_result_returned", "_write_pm_role_work_result_decision"),
        owns_side_effects=("pm_role_work_request_result_write",),
        dependencies=("pm_role_work_gates", "router_facade"),
        behavior_contracts=("PM role-work request/result/disposition writes",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "pm_role_work_lifecycle",
        path="skills/flowpilot/assets/flowpilot_router_work_packets_pm_role_lifecycle.py",
        owns_functions=("_load_pm_role_work_request_index", "_record_officer_lifecycle_status"),
        owns_state=("pm_role_work_index", "officer_request_lifecycle"),
        dependencies=("router_facade",),
        behavior_contracts=("PM role-work request indexes and officer lifecycle records",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "pm_role_work_actions",
        path="skills/flowpilot/assets/flowpilot_router_work_packets_pm_role_actions.py",
        owns_functions=("_next_pm_role_work_request_action", "_try_reconcile_pm_role_work_results"),
        dependencies=("pm_role_work_lifecycle", "pm_role_work_writes", "router_facade"),
        behavior_contracts=("PM role-work next-action selection and result reconciliation",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "terminal_ledger",
        path="skills/flowpilot/assets/flowpilot_router_terminal_ledger.py",
        owns_functions=("write_final_route_wide_ledger", "write_terminal_backward_replay"),
        owns_state=("final_route_wide_gate_ledger", "terminal_closure_suite"),
        owns_side_effects=("terminal_ledger_write",),
        behavior_contracts=("terminal replay", "closure blocking"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "control_blockers",
        path="skills/flowpilot/assets/flowpilot_router_events_repair.py",
        owns_functions=("write_control_blocker", "write_control_blocker_repair_decision"),
        owns_state=("control_blocker_records", "repair_transactions"),
        owns_side_effects=("control_blocker_write",),
        behavior_contracts=("repair transaction idempotency",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "packet_runtime_contracts",
        path="skills/flowpilot/assets/packet_runtime_contracts.py",
        owns_functions=("packet_identity_boundary", "result_identity_boundary", "output_contract_section"),
        owns_config=("packet_prompt_assets",),
        dependencies=("prompt_store",),
        behavior_contracts=("packet prompt rendering", "output contract text authority"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "terminal_ledger_summary",
        path="skills/flowpilot/assets/flowpilot_router_terminal_ledger_summary.py",
        owns_functions=("_terminal_summary_action", "_write_terminal_summary"),
        owns_side_effects=("terminal_summary_write",),
        dependencies=("terminal_ledger", "router_facade"),
        behavior_contracts=("terminal summary validation and write",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "terminal_ledger_traceability",
        path="skills/flowpilot/assets/flowpilot_router_terminal_ledger_traceability.py",
        owns_functions=("_final_ledger_traceability_issues", "_write_final_route_wide_ledger"),
        owns_side_effects=("final_route_wide_ledger_write",),
        dependencies=("terminal_ledger", "router_facade"),
        behavior_contracts=("final ledger traceability and source-of-truth entries",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "terminal_ledger_closure",
        path="skills/flowpilot/assets/flowpilot_router_terminal_ledger_closure.py",
        owns_functions=("_write_terminal_backward_replay", "_write_terminal_closure_suite"),
        owns_side_effects=("terminal_backward_replay_write", "terminal_closure_suite_write"),
        dependencies=("terminal_ledger_traceability", "router_facade"),
        behavior_contracts=("terminal backward replay and closure suite writes",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "terminal_ledger_recovery",
        path="skills/flowpilot/assets/flowpilot_router_terminal_ledger_recovery.py",
        owns_functions=("reconcile_current_run", "_repair_legacy_material_packet_contracts"),
        owns_side_effects=("terminal_reconciliation_write",),
        dependencies=("terminal_ledger", "router_facade"),
        behavior_contracts=("terminal status recovery and legacy material packet repair",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "packet_runtime_progress",
        path="skills/flowpilot/assets/packet_runtime_progress.py",
        owns_functions=("write_controller_status_packet", "update_controller_progress"),
        owns_state=("packet_runtime_progress",),
        dependencies=("packet_runtime_paths", "packet_runtime_schema"),
        behavior_contracts=("controller status packet writes", "progress validation"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "packet_runtime_creation",
        path="skills/flowpilot/assets/packet_runtime_creation.py",
        owns_functions=("create_packet", "create_user_intake_packet", "build_controller_handoff", "controller_handoff_text"),
        owns_state=("packet_runtime_creation",),
        owns_side_effects=("packet_envelope_body_write",),
        dependencies=("packet_runtime_contracts", "packet_runtime_paths", "packet_runtime_relay"),
        behavior_contracts=("packet envelope/body creation", "controller handoff envelope-only boundary"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "packet_runtime_results",
        path="skills/flowpilot/assets/packet_runtime_results.py",
        owns_functions=("write_result", "read_result_body_for_role"),
        owns_state=("packet_runtime_results",),
        owns_side_effects=("packet_result_write",),
        dependencies=("packet_runtime_contracts", "packet_runtime_paths", "packet_runtime_relay"),
        behavior_contracts=("result envelope/body write", "role-scoped result reads"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "packet_runtime_audit",
        path="skills/flowpilot/assets/packet_runtime_audit.py",
        owns_functions=("audit_barrier_bundles", "audit_packet_chain"),
        owns_state=("packet_runtime_audit",),
        dependencies=("packet_runtime_paths", "packet_runtime_ledger"),
        behavior_contracts=("packet chain audit", "replacement-chain audit"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "packet_runtime_cli",
        path="skills/flowpilot/assets/packet_runtime_cli.py",
        owns_functions=("parse_args", "main"),
        dependencies=("packet_runtime_creation", "packet_runtime_results", "packet_runtime_audit"),
        behavior_contracts=("packet runtime CLI compatibility", "subcommand dispatch"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "card_runtime_io",
        path="skills/flowpilot/assets/card_runtime_io.py",
        owns_functions=("read_json", "write_json", "project_relative", "resolve_project_path"),
        behavior_contracts=("card runtime path and JSON helpers", "stable hash helpers"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "card_runtime_ledgers",
        path="skills/flowpilot/assets/card_runtime_ledgers.py",
        owns_functions=("_load_card_ledger", "_load_return_ledger", "_merge_pending_return_ack"),
        owns_state=("card_runtime_ledgers",),
        dependencies=("card_runtime_io",),
        behavior_contracts=("card ledger reads", "return ledger merge identity"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "card_runtime_envelopes",
        path="skills/flowpilot/assets/card_runtime_envelopes.py",
        owns_functions=("_load_envelope", "_load_bundle_envelope", "_validate_target_identity"),
        dependencies=("card_runtime_io",),
        behavior_contracts=("card envelope validation", "direct router ACK token checks"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "card_runtime_ack",
        path="skills/flowpilot/assets/card_runtime_ack.py",
        owns_functions=("open_card", "submit_card_ack", "validate_card_ack"),
        owns_state=("card_runtime_ack",),
        owns_side_effects=("card_ack_write",),
        dependencies=("card_runtime_envelopes", "card_runtime_ledgers"),
        behavior_contracts=("single-card open and ACK lifecycle", "role/token/receipt validation"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "card_runtime_bundle",
        path="skills/flowpilot/assets/card_runtime_bundle.py",
        owns_functions=("open_card_bundle", "submit_card_bundle_ack", "validate_card_bundle_ack"),
        owns_state=("card_runtime_bundle",),
        owns_side_effects=("card_bundle_ack_write",),
        dependencies=("card_runtime_envelopes", "card_runtime_ledgers"),
        behavior_contracts=("bundle open and ACK lifecycle", "incomplete bundle inspection"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "user_flow_source",
        path="skills/flowpilot/assets/flowpilot_user_flow_source.py",
        owns_functions=("_load_route_source", "_review_display"),
        owns_state=("user_flow_source",),
        behavior_contracts=("route source discovery", "review display loading"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "user_flow_tree",
        path="skills/flowpilot/assets/flowpilot_user_flow_tree.py",
        owns_functions=("_all_route_nodes", "_node_status", "_node_topology"),
        owns_state=("user_flow_tree",),
        behavior_contracts=("route tree flattening", "route topology classification"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "user_flow_stage",
        path="skills/flowpilot/assets/flowpilot_user_flow_stage.py",
        owns_functions=("classify_current_stage",),
        dependencies=("user_flow_tree",),
        behavior_contracts=("current stage classification", "route mutation pending detection"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "user_flow_mermaid",
        path="skills/flowpilot/assets/flowpilot_user_flow_mermaid.py",
        owns_functions=("detect_return_path", "build_mermaid"),
        dependencies=("user_flow_tree", "user_flow_stage"),
        behavior_contracts=("Mermaid route rendering", "return-path display"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "user_flow_markdown",
        path="skills/flowpilot/assets/flowpilot_user_flow_markdown.py",
        owns_functions=("build_chat_markdown",),
        dependencies=("user_flow_mermaid", "user_flow_stage"),
        behavior_contracts=("chat Markdown route summary",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
)

MODEL_PUBLIC_ENTRYPOINTS = (
    PublicEntrypointEvidence(
        "prompt_isolation_model_import",
        old_path="simulations/prompt_isolation_model.py",
        new_path="simulations/prompt_isolation_model.py",
        parity_evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        evidence_path="simulations/prompt_isolation_results.json",
        release_required=True,
    ),
    PublicEntrypointEvidence(
        "cross_plane_friction_model_import",
        old_path="simulations/flowpilot_cross_plane_friction_model.py",
        new_path="simulations/flowpilot_cross_plane_friction_model.py",
        parity_evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        evidence_path="simulations/flowpilot_cross_plane_friction_results.json",
        release_required=True,
    ),
    PublicEntrypointEvidence(
        "persistent_router_daemon_model_import",
        old_path="simulations/flowpilot_persistent_router_daemon_model.py",
        new_path="simulations/flowpilot_persistent_router_daemon_model.py",
        parity_evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        evidence_path="simulations/flowpilot_persistent_router_daemon_results.json",
        release_required=True,
    ),
    PublicEntrypointEvidence(
        "packet_control_plane_model_import",
        old_path="skills/flowpilot/assets/packet_control_plane_model.py",
        new_path="skills/flowpilot/assets/packet_control_plane_model.py",
        parity_evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        evidence_path="skills/flowpilot/assets/packet_control_plane_results.json",
        release_required=True,
    ),
)

MODEL_STRUCTURE_PARTITIONS = (
    StructurePartitionItem(
        "prompt_isolation_public_facade",
        item_type="public_entrypoint",
        owner_module_id="prompt_isolation_facade",
        ownership="parent",
        old_path="prompt_isolation_model",
        new_path="prompt_isolation_model",
    ),
    StructurePartitionItem(
        "prompt_isolation_state",
        item_type="state",
        owner_module_id="prompt_isolation_state",
        old_path="prompt_isolation_model.State",
        new_path="prompt_isolation_model_state",
    ),
    StructurePartitionItem(
        "prompt_isolation_transitions",
        item_type="function_cluster",
        owner_module_id="prompt_isolation_transitions",
        old_path="prompt_isolation_model.next_safe_states",
        new_path="prompt_isolation_model_transitions",
    ),
    StructurePartitionItem(
        "prompt_isolation_invariants",
        item_type="invariant_cluster",
        owner_module_id="prompt_isolation_invariants",
        old_path="prompt_isolation_model.invariant_failures",
        new_path="prompt_isolation_model_invariants",
    ),
    StructurePartitionItem(
        "prompt_isolation_hazards",
        item_type="hazard_cluster",
        owner_module_id="prompt_isolation_hazards",
        old_path="prompt_isolation_model.hazard_states",
        new_path="prompt_isolation_model_hazards",
    ),
    StructurePartitionItem(
        "cross_plane_public_facade",
        item_type="public_entrypoint",
        owner_module_id="cross_plane_facade",
        ownership="parent",
        old_path="flowpilot_cross_plane_friction_model",
        new_path="flowpilot_cross_plane_friction_model",
    ),
    StructurePartitionItem(
        "cross_plane_state",
        item_type="state",
        owner_module_id="cross_plane_state",
        old_path="flowpilot_cross_plane_friction_model.State",
        new_path="flowpilot_cross_plane_friction_model_state",
    ),
    StructurePartitionItem(
        "cross_plane_transitions",
        item_type="function_cluster",
        owner_module_id="cross_plane_transitions",
        old_path="flowpilot_cross_plane_friction_model.next_safe_states",
        new_path="flowpilot_cross_plane_friction_model_transitions",
    ),
    StructurePartitionItem(
        "cross_plane_invariants",
        item_type="invariant_cluster",
        owner_module_id="cross_plane_invariants",
        old_path="flowpilot_cross_plane_friction_model.invariant_failures",
        new_path="flowpilot_cross_plane_friction_model_invariants",
    ),
    StructurePartitionItem(
        "cross_plane_hazards",
        item_type="hazard_cluster",
        owner_module_id="cross_plane_hazards",
        old_path="flowpilot_cross_plane_friction_model.hazard_states",
        new_path="flowpilot_cross_plane_friction_model_hazards",
    ),
    StructurePartitionItem(
        "cross_plane_live_audit",
        item_type="adapter",
        owner_module_id="cross_plane_audit",
        old_path="flowpilot_cross_plane_friction_model.audit_live_run",
        new_path="flowpilot_cross_plane_friction_model_audit",
    ),
    StructurePartitionItem(
        "cross_plane_repair_strategy",
        item_type="strategy",
        owner_module_id="cross_plane_strategy",
        old_path="flowpilot_cross_plane_friction_model.minimal_repair_strategy",
        new_path="flowpilot_cross_plane_friction_model_strategy",
    ),
    StructurePartitionItem(
        "persistent_daemon_public_facade",
        item_type="public_entrypoint",
        owner_module_id="persistent_daemon_facade",
        ownership="parent",
        old_path="flowpilot_persistent_router_daemon_model",
        new_path="flowpilot_persistent_router_daemon_model",
    ),
    StructurePartitionItem(
        "persistent_daemon_state",
        item_type="state",
        owner_module_id="persistent_daemon_state",
        old_path="flowpilot_persistent_router_daemon_model.State",
        new_path="flowpilot_persistent_router_daemon_model_state",
    ),
    StructurePartitionItem(
        "persistent_daemon_transitions",
        item_type="function_cluster",
        owner_module_id="persistent_daemon_transitions",
        old_path="flowpilot_persistent_router_daemon_model.next_safe_states",
        new_path="flowpilot_persistent_router_daemon_model_transitions",
    ),
    StructurePartitionItem(
        "persistent_daemon_invariants",
        item_type="invariant_cluster",
        owner_module_id="persistent_daemon_invariants",
        old_path="flowpilot_persistent_router_daemon_model.invariant_failures",
        new_path="flowpilot_persistent_router_daemon_model_invariants",
    ),
    StructurePartitionItem(
        "persistent_daemon_hazards",
        item_type="hazard_cluster",
        owner_module_id="persistent_daemon_hazards",
        old_path="flowpilot_persistent_router_daemon_model.hazard_states",
        new_path="flowpilot_persistent_router_daemon_model_hazards",
    ),
    StructurePartitionItem(
        "packet_control_plane_public_facade",
        item_type="public_entrypoint",
        owner_module_id="packet_control_plane_facade",
        ownership="parent",
        old_path="packet_control_plane_model",
        new_path="packet_control_plane_model",
    ),
    StructurePartitionItem(
        "packet_control_plane_state",
        item_type="state",
        owner_module_id="packet_control_plane_state",
        old_path="packet_control_plane_model state dataclasses",
        new_path="packet_control_plane_model_state",
    ),
    StructurePartitionItem(
        "packet_control_plane_transitions",
        item_type="function_cluster",
        owner_module_id="packet_control_plane_transitions",
        old_path="packet_control_plane_model transition classes",
        new_path="packet_control_plane_model_transitions",
    ),
    StructurePartitionItem(
        "packet_control_plane_transition_children",
        item_type="function_cluster",
        owner_module_id="packet_control_plane_transitions",
        old_path="packet_control_plane_model_transitions mixed transition classes",
        new_path="packet_control_plane_model_transitions_*",
    ),
    StructurePartitionItem(
        "packet_control_plane_invariants",
        item_type="invariant_cluster",
        owner_module_id="packet_control_plane_invariants",
        old_path="packet_control_plane_model invariants",
        new_path="packet_control_plane_model_invariants",
    ),
)

MODEL_STRUCTURE_MODULES = (
    ModuleStructureEvidence(
        "prompt_isolation_facade",
        path="simulations/prompt_isolation_model.py",
        layer="parent",
        owns_functions=("build_workflow", "next_states", "is_terminal", "is_success"),
        behavior_contracts=("legacy import path", "runner compatibility"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "prompt_isolation_state",
        path="simulations/prompt_isolation_model_state.py",
        owns_functions=("initial_state",),
        owns_state=("prompt_isolation_state",),
        behavior_contracts=("immutable prompt-isolation state shape",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "prompt_isolation_transitions",
        path="simulations/prompt_isolation_model_transitions.py",
        owns_functions=("PromptIsolationStep", "next_safe_states"),
        behavior_contracts=("prompt-isolation transition labels",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "prompt_isolation_invariants",
        path="simulations/prompt_isolation_model_invariants.py",
        owns_functions=("invariant_failures", "prompt_isolation_invariant"),
        behavior_contracts=("prompt-isolation invariant messages",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "prompt_isolation_hazards",
        path="simulations/prompt_isolation_model_hazards.py",
        owns_functions=("hazard_states",),
        behavior_contracts=("prompt-isolation known-bad states",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "cross_plane_facade",
        path="simulations/flowpilot_cross_plane_friction_model.py",
        layer="parent",
        owns_functions=("build_workflow", "next_states", "is_terminal", "is_success"),
        behavior_contracts=("legacy import path", "runner compatibility"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "cross_plane_state",
        path="simulations/flowpilot_cross_plane_friction_model_state.py",
        owns_functions=("initial_state",),
        owns_state=("cross_plane_state",),
        behavior_contracts=("cross-plane state shape and constants",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "cross_plane_transitions",
        path="simulations/flowpilot_cross_plane_friction_model_transitions.py",
        owns_functions=("CrossPlaneReconciliationStep", "next_safe_states"),
        behavior_contracts=("cross-plane transition labels",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "cross_plane_invariants",
        path="simulations/flowpilot_cross_plane_friction_model_invariants.py",
        owns_functions=("invariant_failures",),
        behavior_contracts=("cross-plane invariant messages",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "cross_plane_hazards",
        path="simulations/flowpilot_cross_plane_friction_model_hazards.py",
        owns_functions=("hazard_states", "repair_solution_state"),
        behavior_contracts=("cross-plane known-bad states",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "cross_plane_audit",
        path="simulations/flowpilot_cross_plane_friction_model_audit.py",
        owns_functions=("audit_live_run", "state_from_findings"),
        behavior_contracts=("envelope-only live audit adapter",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "cross_plane_strategy",
        path="simulations/flowpilot_cross_plane_friction_model_strategy.py",
        owns_functions=("minimal_repair_strategy",),
        behavior_contracts=("minimal repair action table",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "persistent_daemon_facade",
        path="simulations/flowpilot_persistent_router_daemon_model.py",
        layer="parent",
        owns_functions=("build_workflow", "next_states", "is_terminal", "is_success"),
        behavior_contracts=("legacy import path", "runner compatibility"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "persistent_daemon_state",
        path="simulations/flowpilot_persistent_router_daemon_model_state.py",
        owns_functions=("initial_state",),
        owns_state=("persistent_daemon_state",),
        behavior_contracts=("persistent daemon state shape",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "persistent_daemon_transitions",
        path="simulations/flowpilot_persistent_router_daemon_model_transitions.py",
        owns_functions=("PersistentRouterDaemonStep", "next_safe_states"),
        behavior_contracts=("persistent daemon transition labels",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "persistent_daemon_invariants",
        path="simulations/flowpilot_persistent_router_daemon_model_invariants.py",
        owns_functions=("invariant_failures",),
        behavior_contracts=("persistent daemon invariant messages",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "persistent_daemon_hazards",
        path="simulations/flowpilot_persistent_router_daemon_model_hazards.py",
        owns_functions=("hazard_states",),
        behavior_contracts=("persistent daemon known-bad states",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "packet_control_plane_facade",
        path="skills/flowpilot/assets/packet_control_plane_model.py",
        layer="parent",
        owns_functions=("build_workflow",),
        behavior_contracts=("legacy packet control-plane model import path", "runner compatibility"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "packet_control_plane_state",
        path="skills/flowpilot/assets/packet_control_plane_model_state.py",
        owns_functions=("_packet_from_id",),
        owns_state=("packet_control_plane_state",),
        behavior_contracts=("packet control-plane immutable state shape", "case dataclass identity"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "packet_control_plane_transitions",
        path="skills/flowpilot/assets/packet_control_plane_model_transitions.py",
        owns_functions=(
            "PMIssuePacket",
            "PacketRuntimeWrite",
            "RouterDirectDispatch",
            "ReviewerResult",
            "PMAdvance",
        ),
        dependencies=("packet_control_plane_state",),
        behavior_contracts=("packet control-plane transition labels", "packet lifecycle progress cases"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "packet_control_plane_transitions_issue_resume",
        path="skills/flowpilot/assets/packet_control_plane_model_transitions_issue_resume.py",
        owns_functions=("PMIssuePacket", "HeartbeatResumeLoad", "ControllerAskPMOnResume", "PMResumeDecision"),
        dependencies=("packet_control_plane_state",),
        behavior_contracts=("packet issue and heartbeat resume transition labels",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "packet_control_plane_transitions_packet_relay",
        path="skills/flowpilot/assets/packet_control_plane_model_transitions_packet_relay.py",
        owns_functions=("PacketRuntimeWrite", "ControllerReminderCheck", "ControllerEnvelopeOnlyHandoff", "ControllerEnvelopeRelay"),
        dependencies=("packet_control_plane_state",),
        behavior_contracts=("packet runtime write and Controller relay transition labels",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "packet_control_plane_transitions_dispatch_results",
        path="skills/flowpilot/assets/packet_control_plane_model_transitions_dispatch_results.py",
        owns_functions=("RouterDirectDispatch", "WorkerOrControllerResult", "ControllerResultRelay"),
        dependencies=("packet_control_plane_state",),
        behavior_contracts=("dispatch and result relay transition labels",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "packet_control_plane_transitions_review_pm",
        path="skills/flowpilot/assets/packet_control_plane_model_transitions_review_pm.py",
        owns_functions=("ReviewerResultEnvelopeCheck", "ReviewerResult", "PMRepairAfterInvalidOrigin", "PMAdvance"),
        dependencies=("packet_control_plane_state", "packet_control_plane_invariants"),
        behavior_contracts=("reviewer and PM outcome transition labels",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
    ModuleStructureEvidence(
        "packet_control_plane_invariants",
        path="skills/flowpilot/assets/packet_control_plane_model_invariants.py",
        owns_functions=("no_advance_from_controller_artifact", "advance_requires_review_pass"),
        dependencies=("packet_control_plane_state",),
        behavior_contracts=("packet control-plane invariant checks", "known stuck-loop blockers"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
    ),
)

ROUTER_TEST_PARTITIONS = (
    TestPartitionItem("startup_bootstrap", owner_suite_id="router_startup_runtime"),
    TestPartitionItem("foreground_controller", owner_suite_id="router_foreground_controller"),
    TestPartitionItem("packet_prompt_assets", owner_suite_id="router_prompt_store"),
    TestPartitionItem("packet_runtime", owner_suite_id="router_packet_runtime"),
    TestPartitionItem("packet_runtime_progress", owner_suite_id="router_packet_runtime"),
    TestPartitionItem("packet_runtime_creation", owner_suite_id="router_packet_runtime"),
    TestPartitionItem("packet_runtime_results", owner_suite_id="router_packet_runtime"),
    TestPartitionItem("packet_runtime_audit", owner_suite_id="router_packet_runtime"),
    TestPartitionItem("packet_runtime_cli", owner_suite_id="router_packet_runtime"),
    TestPartitionItem("packets", owner_suite_id="router_packets"),
    TestPartitionItem("cards", owner_suite_id="router_cards"),
    TestPartitionItem("card_runtime_io", owner_suite_id="router_card_runtime"),
    TestPartitionItem("card_runtime_ledgers", owner_suite_id="router_card_runtime"),
    TestPartitionItem("card_runtime_envelopes", owner_suite_id="router_card_runtime"),
    TestPartitionItem("card_runtime_ack", owner_suite_id="router_card_runtime"),
    TestPartitionItem("card_runtime_bundle", owner_suite_id="router_card_runtime"),
    TestPartitionItem("ack_return", owner_suite_id="router_ack_return"),
    TestPartitionItem("route_boundaries", owner_suite_id="router_boundaries"),
    TestPartitionItem("route_mutation_draft_activation", owner_suite_id="router_route_mutation_draft_activation"),
    TestPartitionItem("route_mutation_model_miss_triage", owner_suite_id="router_route_mutation_model_miss_triage"),
    TestPartitionItem("route_mutation_acceptance_repair", owner_suite_id="router_route_mutation_acceptance_repair"),
    TestPartitionItem("route_mutation_preconditions", owner_suite_id="router_route_mutation_preconditions"),
    TestPartitionItem("route_mutation_transactions", owner_suite_id="router_route_mutation_transactions"),
    TestPartitionItem("route_mutation_topology", owner_suite_id="router_route_mutation_topology"),
    TestPartitionItem("route_mutation_sibling_replacement", owner_suite_id="router_route_mutation_sibling_replacement"),
    TestPartitionItem("route_mutation_parent_backward", owner_suite_id="router_route_mutation_parent_backward"),
    TestPartitionItem("route_mutation_contracts", owner_suite_id="router_route_mutation_contracts"),
    TestPartitionItem("user_flow_diagram", owner_suite_id="router_user_flow_diagram"),
    TestPartitionItem("user_flow_source", owner_suite_id="router_user_flow_diagram"),
    TestPartitionItem("user_flow_tree", owner_suite_id="router_user_flow_diagram"),
    TestPartitionItem("user_flow_stage", owner_suite_id="router_user_flow_diagram"),
    TestPartitionItem("user_flow_mermaid", owner_suite_id="router_user_flow_diagram"),
    TestPartitionItem("user_flow_markdown", owner_suite_id="router_user_flow_diagram"),
    TestPartitionItem("action_factory_dispatch", owner_suite_id="router_packets"),
    TestPartitionItem("action_factory_envelope", owner_suite_id="router_packets"),
    TestPartitionItem("action_factory_reconciliation", owner_suite_id="router_packets"),
    TestPartitionItem("terminal_final_ledger", owner_suite_id="router_terminal_final_ledger"),
    TestPartitionItem("terminal_replay_summary", owner_suite_id="router_terminal_replay_summary"),
    TestPartitionItem("terminal_node_stop", owner_suite_id="router_terminal_node_stop"),
    TestPartitionItem("closure_dirty_ledgers", owner_suite_id="router_closure_dirty_ledgers"),
    TestPartitionItem("closure_pm_role_work", owner_suite_id="router_closure_pm_role_work"),
    TestPartitionItem("resume_reentry", owner_suite_id="router_resume_reentry"),
    TestPartitionItem("resume_rehydration", owner_suite_id="router_resume_rehydration"),
    TestPartitionItem("resume_role_recovery", owner_suite_id="router_resume_role_recovery"),
    TestPartitionItem("resume_liveness_faults", owner_suite_id="router_resume_liveness_faults"),
    TestPartitionItem("control_blockers_recorded_events", owner_suite_id="router_control_blockers_recorded_events"),
    TestPartitionItem("control_blockers_reissue_retry", owner_suite_id="router_control_blockers_reissue_retry"),
    TestPartitionItem("control_blockers_pm_repair_decisions", owner_suite_id="router_control_blockers_pm_repair_decisions"),
    TestPartitionItem("control_blockers_protocol_transactions", owner_suite_id="router_control_blockers_protocol_transactions"),
    TestPartitionItem("control_blockers_followup_fatal", owner_suite_id="router_control_blockers_followup_fatal"),
    TestPartitionItem("pm_role_work_requests", owner_suite_id="router_pm_role_work_requests"),
    TestPartitionItem("pm_role_work_gates", owner_suite_id="router_pm_role_work_results"),
    TestPartitionItem("pm_role_work_writes", owner_suite_id="router_pm_role_work_results"),
    TestPartitionItem("pm_role_work_lifecycle", owner_suite_id="router_pm_role_work_waits"),
    TestPartitionItem("pm_role_work_actions", owner_suite_id="router_pm_role_work_waits"),
    TestPartitionItem("controller_receipt_writes", owner_suite_id="router_foreground_controller"),
    TestPartitionItem("controller_receipt_effects", owner_suite_id="router_foreground_controller"),
    TestPartitionItem("controller_receipt_pending", owner_suite_id="router_foreground_controller"),
    TestPartitionItem("controller_receipt_scheduled", owner_suite_id="router_foreground_controller"),
    TestPartitionItem("quality_gates_background_manifest", owner_suite_id="router_quality_gates_background_manifest"),
    TestPartitionItem("quality_gates_decisions", owner_suite_id="router_quality_gates_decisions"),
    TestPartitionItem("quality_gates_evidence_artifacts", owner_suite_id="router_quality_gates_evidence_artifacts"),
    TestPartitionItem("quality_gates_route_model", owner_suite_id="router_quality_gates_route_model"),
    TestPartitionItem("quality_gates_node_contracts", owner_suite_id="router_quality_gates_node_contracts"),
    TestPartitionItem("material_modeling_intake", owner_suite_id="router_material_modeling_intake"),
    TestPartitionItem("material_modeling_scan_relay", owner_suite_id="router_material_modeling_scan_relay"),
    TestPartitionItem("material_modeling_modelability", owner_suite_id="router_material_modeling_modelability"),
    TestPartitionItem("bounded_background_fanout", owner_suite_id="router_background_supervisor"),
)

ROUTER_TEST_SUITES = (
    TestSuiteEvidence(
        "router_background_supervisor",
        command="python scripts/run_test_tier.py --tier router --background --background-max-parallel 4 --background-dir tmp/flowguard_background",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=1,
        selected_count=1,
        exit_code=0,
        result_path="tmp/flowguard_background/router_background_supervisor.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("bounded_background_fanout",),
        owns_side_effects=("background_child_launch",),
    ),
    TestSuiteEvidence(
        "router_startup_runtime",
        command="python -m unittest -v tests.test_flowpilot_router_startup_runtime tests.router_runtime.bootstrap_cli tests.router_runtime.startup_bootstrap tests.router_runtime.startup_daemon",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=80,
        selected_count=80,
        exit_code=0,
        result_path="tmp/flowguard_background/router_startup_runtime.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("startup_bootstrap",),
    ),
    TestSuiteEvidence(
        "router_foreground_controller",
        command="python -m unittest -v tests.router_runtime.foreground tests.router_runtime.controller tests.router_runtime.foreground_controller tests.router_runtime.dispatch_gate",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=66,
        selected_count=66,
        exit_code=0,
        result_path="tmp/flowguard_background/router_foreground_controller.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("foreground_controller",),
    ),
    TestSuiteEvidence(
        "router_prompt_store",
        command="python -m unittest -v tests.test_flowpilot_prompt_store",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=7,
        selected_count=7,
        exit_code=0,
        result_path="tmp/flowguard_background/router_prompt_store.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("packet_prompt_assets",),
    ),
    TestSuiteEvidence(
        "router_packet_runtime",
        command="python -m unittest -v tests.test_flowpilot_packet_runtime",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=23,
        selected_count=23,
        exit_code=0,
        result_path="tmp/flowguard_background/router_packet_runtime.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=(
            "packet_runtime",
            "packet_runtime_progress",
            "packet_runtime_creation",
            "packet_runtime_results",
            "packet_runtime_audit",
            "packet_runtime_cli",
        ),
    ),
    TestSuiteEvidence(
        "router_card_runtime",
        command="python -m unittest -v tests.test_flowpilot_card_runtime tests.test_flowpilot_router_runtime_cards",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=10,
        selected_count=10,
        exit_code=0,
        result_path="tmp/flowguard_background/router_card_runtime.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=(
            "card_runtime_io",
            "card_runtime_ledgers",
            "card_runtime_envelopes",
            "card_runtime_ack",
            "card_runtime_bundle",
        ),
    ),
    TestSuiteEvidence(
        "router_packets",
        command="python -m unittest -v tests.router_runtime.packets",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=22,
        selected_count=22,
        exit_code=0,
        result_path="tmp/flowguard_background/router_packets.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("packets",),
    ),
    TestSuiteEvidence(
        "router_cards",
        command="python -m unittest -v tests.router_runtime.cards",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=8,
        selected_count=8,
        exit_code=0,
        result_path="tmp/flowguard_background/router_cards.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("cards",),
    ),
    TestSuiteEvidence(
        "router_ack_return",
        command="python -m unittest -v tests.router_runtime.ack_return",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=15,
        selected_count=15,
        exit_code=0,
        result_path="tmp/flowguard_background/router_ack_return.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("ack_return",),
    ),
    TestSuiteEvidence(
        "router_boundaries",
        command="python -m unittest -v tests.test_flowpilot_router_boundaries",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=18,
        selected_count=18,
        exit_code=0,
        result_path="tmp/flowguard_background/router_boundaries.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("route_boundaries",),
    ),
    TestSuiteEvidence(
        "router_route_mutation_draft_activation",
        command="python -m unittest -v tests.router_runtime.route_mutation_draft_activation",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=3,
        selected_count=3,
        exit_code=0,
        result_path="tmp/flowguard_background/router_route_mutation_draft_activation.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("route_mutation_draft_activation",),
    ),
    TestSuiteEvidence(
        "router_route_mutation_model_miss_triage",
        command="python -m unittest -v tests.router_runtime.route_mutation_model_miss_triage",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=8,
        selected_count=8,
        exit_code=0,
        result_path="tmp/flowguard_background/router_route_mutation_model_miss_triage.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("route_mutation_model_miss_triage",),
    ),
    TestSuiteEvidence(
        "router_route_mutation_acceptance_repair",
        command="python -m unittest -v tests.router_runtime.route_mutation_acceptance_repair",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=2,
        selected_count=2,
        exit_code=0,
        result_path="tmp/flowguard_background/router_route_mutation_acceptance_repair.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("route_mutation_acceptance_repair",),
    ),
    TestSuiteEvidence(
        "router_route_mutation_preconditions",
        command="python -m unittest -v tests.router_runtime.route_mutation_preconditions",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=3,
        selected_count=3,
        exit_code=0,
        result_path="tmp/flowguard_background/router_route_mutation_preconditions.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("route_mutation_preconditions",),
    ),
    TestSuiteEvidence(
        "router_route_mutation_transactions",
        command="python -m unittest -v tests.router_runtime.route_mutation_transactions",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=1,
        selected_count=1,
        exit_code=0,
        result_path="tmp/flowguard_background/router_route_mutation_transactions.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("route_mutation_transactions",),
    ),
    TestSuiteEvidence(
        "router_route_mutation_topology",
        command="python -m unittest -v tests.router_runtime.route_mutation_topology",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=1,
        selected_count=1,
        exit_code=0,
        result_path="tmp/flowguard_background/router_route_mutation_topology.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("route_mutation_topology",),
    ),
    TestSuiteEvidence(
        "router_route_mutation_sibling_replacement",
        command="python -m unittest -v tests.router_runtime.route_mutation_sibling_replacement",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=1,
        selected_count=1,
        exit_code=0,
        result_path="tmp/flowguard_background/router_route_mutation_sibling_replacement.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("route_mutation_sibling_replacement",),
    ),
    TestSuiteEvidence(
        "router_route_mutation_parent_backward",
        command="python -m unittest -v tests.router_runtime.route_mutation_parent_backward",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=3,
        selected_count=3,
        exit_code=0,
        result_path="tmp/flowguard_background/router_route_mutation_parent_backward.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("route_mutation_parent_backward",),
    ),
    TestSuiteEvidence(
        "router_route_mutation_contracts",
        command="python -m unittest -v tests.test_flowpilot_router_runtime_route_mutation",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=6,
        selected_count=6,
        exit_code=0,
        result_path="tmp/flowguard_background/router_route_mutation_contracts.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("route_mutation_contracts",),
    ),
    TestSuiteEvidence(
        "router_user_flow_diagram",
        command="python -m unittest -v tests.test_flowpilot_user_flow_diagram",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=19,
        selected_count=19,
        exit_code=0,
        result_path="tmp/flowguard_background/router_user_flow_diagram.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=(
            "user_flow_diagram",
            "user_flow_source",
            "user_flow_tree",
            "user_flow_stage",
            "user_flow_mermaid",
            "user_flow_markdown",
        ),
    ),
    TestSuiteEvidence(
        "router_terminal_final_ledger",
        command="python -m unittest -v -k test_final_ledger_records_frozen_contract_replay_source_paths -k test_final_ledger_rejects_dirty_pm_suggestion_ledger -k test_final_ledger_rejects_dirty_self_interrogation_index -k test_final_ledger_rejects_missing_source_of_truth_entries_and_contract_replay tests.router_runtime.terminal",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=4,
        selected_count=4,
        exit_code=0,
        result_path="tmp/flowguard_background/router_terminal_final_ledger.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("terminal_final_ledger",),
    ),
    TestSuiteEvidence(
        "router_terminal_replay_summary",
        command="python -m unittest -v -k test_reconcile_recovers_legacy_terminal_closure_state -k test_reconcile_run_recovers_terminal_status_from_current_pointer -k test_terminal_replay_requires_reviewed_segments_and_pm_segment_decisions -k test_terminal_summary_payload_requires_attribution_display_and_run_root_sources tests.router_runtime.terminal",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=4,
        selected_count=4,
        exit_code=0,
        result_path="tmp/flowguard_background/router_terminal_replay_summary.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("terminal_replay_summary",),
    ),
    TestSuiteEvidence(
        "router_terminal_node_stop",
        command="python -m unittest -v -k test_nonterminal_node_completion_does_not_show_completed_node_as_in_progress -k test_user_stop_or_cancel_makes_run_terminal_and_blocks_next_work tests.router_runtime.terminal",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=2,
        selected_count=2,
        exit_code=0,
        result_path="tmp/flowguard_background/router_terminal_node_stop.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("terminal_node_stop",),
    ),
    TestSuiteEvidence(
        "router_closure_dirty_ledgers",
        command="python -m unittest -v -k test_closure_lifecycle_blocks_when_ledgers_are_dirty_after_terminal_replay -k test_dirty_pm_suggestion_ledger_invalidates_terminal_closure_card -k test_terminal_closure_blocks_dirty_defect_ledger_after_terminal_replay tests.router_runtime.closure",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=3,
        selected_count=3,
        exit_code=0,
        result_path="tmp/flowguard_background/router_closure_dirty_ledgers.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("closure_dirty_ledgers",),
    ),
    TestSuiteEvidence(
        "router_closure_pm_role_work",
        command="python -m unittest -v -k test_officer_role_work_writes_authorized_lifecycle_index -k test_pm_terminal_closure_uses_file_backed_contract_and_prior_context tests.router_runtime.closure",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=2,
        selected_count=2,
        exit_code=0,
        result_path="tmp/flowguard_background/router_closure_pm_role_work.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("closure_pm_role_work",),
    ),
    TestSuiteEvidence(
        "router_resume_reentry",
        command="python -m unittest -v -k test_heartbeat_alive_status_still_enters_router_resume_path -k test_resume_reentry_attaches_to_live_owner_after_delayed_heartbeat -k test_resume_reentry_attaches_to_live_router_daemon_and_ledger -k test_resume_reentry_loads_state_before_resume_cards -k test_resume_reentry_marks_dead_daemon_for_restart_after_liveness_check -k test_resume_reentry_preempts_active_control_blocker_until_replay_or_pm_decision tests.router_runtime.resume",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=6,
        selected_count=6,
        exit_code=0,
        result_path="tmp/flowguard_background/router_resume_reentry.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("resume_reentry",),
    ),
    TestSuiteEvidence(
        "router_resume_rehydration",
        command="python -m unittest -v -k test_incomplete_stateful_rehydrate_receipt_becomes_control_blocker -k test_resume_ambiguous_state_blocks_continue_without_recovery_evidence -k test_resume_rehydration_reissues_missing_obligations_before_pm -k test_resume_rehydration_settles_existing_output_without_pm tests.router_runtime.resume",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=4,
        selected_count=4,
        exit_code=0,
        result_path="tmp/flowguard_background/router_resume_rehydration.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("resume_rehydration",),
    ),
    TestSuiteEvidence(
        "router_resume_role_recovery",
        command="python -m unittest -v -k test_load_resume_state_does_not_downgrade_existing_role_recovery_report -k test_role_recovery_reissues_missing_obligations_in_original_order -k test_role_recovery_settles_existing_ack_without_replay_or_pm -k test_role_recovery_settles_existing_output_without_replay_or_pm tests.router_runtime.resume",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=4,
        selected_count=4,
        exit_code=0,
        result_path="tmp/flowguard_background/router_resume_role_recovery.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("resume_role_recovery",),
    ),
    TestSuiteEvidence(
        "router_resume_liveness_faults",
        command="python -m unittest -v -k test_blocked_role_recovery_receipt_reclaims_existing_report -k test_legacy_liveness_fault_no_output_redirects_to_reissue_not_recovery -k test_mid_run_role_liveness_fault_uses_unified_recovery_before_normal_work -k test_role_no_output_escalates_to_pm_after_two_reissues -k test_role_no_output_report_reissues_same_work_before_role_recovery tests.router_runtime.resume",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=5,
        selected_count=5,
        exit_code=0,
        result_path="tmp/flowguard_background/router_resume_liveness_faults.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("resume_liveness_faults",),
    ),
    TestSuiteEvidence(
        "router_control_blockers_recorded_events",
        command="python -m unittest -v -k test_already_recorded_event_can_resolve_delivered_control_blocker -k test_already_recorded_event_does_not_resolve_pm_required_control_blocker -k test_already_recorded_event_resolves_fatal_control_blocker_after_pm_repair_decision tests.router_runtime.control_blockers",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=3,
        selected_count=3,
        exit_code=0,
        result_path="tmp/flowguard_background/router_control_blockers_recorded_events.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("control_blockers_recorded_events",),
    ),
    TestSuiteEvidence(
        "router_control_blockers_reissue_retry",
        command="python -m unittest -v -k test_control_plane_reissue_retry_budget_escalates_to_pm -k test_missing_open_receipt_control_blocker_routes_to_same_reviewer_reissue -k test_pm_semantic_control_blocker_zero_retry_budget_is_exhausted tests.router_runtime.control_blockers",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=3,
        selected_count=3,
        exit_code=0,
        result_path="tmp/flowguard_background/router_control_blockers_reissue_retry.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("control_blockers_reissue_retry",),
    ),
    TestSuiteEvidence(
        "router_control_blockers_pm_repair_decisions",
        command="python -m unittest -v -k test_pm_repair_decision_accepts_registered_rerun_target_and_waits_for_it -k test_pm_repair_decision_can_repeat_for_new_control_blocker -k test_pm_repair_decision_rejects_legacy_event_replay_without_existing_producer -k test_pm_repair_decision_rejects_registered_but_not_receivable_rerun_target -k test_pm_repair_decision_rejects_unregistered_rerun_target_before_wait_write tests.router_runtime.control_blockers",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=5,
        selected_count=5,
        exit_code=0,
        result_path="tmp/flowguard_background/router_control_blockers_pm_repair_decisions.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("control_blockers_pm_repair_decisions",),
    ),
    TestSuiteEvidence(
        "router_control_blockers_protocol_transactions",
        command="python -m unittest -v -k test_operation_replay_repair_transaction_queues_replay_action -k test_repair_transaction_protocol_blocker_registers_followup_blocker -k test_repair_transaction_recheck_blocker_registers_followup_blocker tests.router_runtime.control_blockers",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=3,
        selected_count=3,
        exit_code=0,
        result_path="tmp/flowguard_background/router_control_blockers_protocol_transactions.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("control_blockers_protocol_transactions",),
    ),
    TestSuiteEvidence(
        "router_control_blockers_followup_fatal",
        command="python -m unittest -v -k test_control_blocker_reviewer_followup_rejects_pm_origin -k test_delivered_control_blocker_with_legacy_invalid_wait_falls_back_to_pm_repair_decision -k test_fatal_control_blocker_rejects_pm_ordinary_waiver tests.router_runtime.control_blockers",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=3,
        selected_count=3,
        exit_code=0,
        result_path="tmp/flowguard_background/router_control_blockers_followup_fatal.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("control_blockers_followup_fatal",),
    ),
    TestSuiteEvidence(
        "router_pm_role_work_requests",
        command="python -m unittest -v -k test_pm_role_work_request_requires_valid_recipient_and_contract -k test_pm_role_work_request_rejects_current_node_contract_family -k test_advisory_pm_role_work_wait_is_marked_nonblocking tests.router_runtime.pm_role_work",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=3,
        selected_count=3,
        exit_code=0,
        result_path="tmp/flowguard_background/router_pm_role_work_requests.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("pm_role_work_requests",),
    ),
    TestSuiteEvidence(
        "router_pm_role_work_results",
        command="python -m unittest -v -k test_gate_targeted_pm_role_work_result_requires_mapped_gate_event -k test_strict_pm_role_work_result_rejects_wrong_next_recipient -k test_pm_role_work_existing_result_reconciles_before_wait tests.router_runtime.pm_role_work",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=3,
        selected_count=3,
        exit_code=0,
        result_path="tmp/flowguard_background/router_pm_role_work_results.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("pm_role_work_gates", "pm_role_work_writes"),
    ),
    TestSuiteEvidence(
        "router_pm_role_work_waits",
        command="python -m unittest -v -k test_pm_role_work_batch_waits_for_all_officer_results_before_pm_relay -k test_wait_event_producer_binding_rejects_wrong_target_role tests.router_runtime.pm_role_work",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=2,
        selected_count=2,
        exit_code=0,
        result_path="tmp/flowguard_background/router_pm_role_work_waits.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("pm_role_work_lifecycle", "pm_role_work_actions"),
    ),
    TestSuiteEvidence(
        "router_quality_gates_background_manifest",
        command="python -m unittest -v -k test_background_agents_allow_requires_six_fresh_live_agent_records -k test_child_skill_gate_manifest_block_records_repair_without_approval -k test_child_skill_gate_manifest_repair_pass_clears_active_gate_block -k test_manifest_references_existing_system_cards tests.router_runtime.quality_gates",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=4,
        selected_count=4,
        exit_code=0,
        result_path="tmp/flowguard_background/router_quality_gates_background_manifest.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("quality_gates_background_manifest",),
    ),
    TestSuiteEvidence(
        "router_quality_gates_decisions",
        command="python -m unittest -v -k test_gate_decision_event_records_ledger_and_state -k test_gate_decision_rejects_mechanical_contradictions -k test_gate_decision_same_identity_replay_is_already_recorded -k test_gate_outcome_block_specs_are_registered_and_reset_stale_passes -k test_reviewer_and_officer_gate_event_groups_have_non_pass_outcomes -k test_reviewer_block_events_are_registered_in_external_taxonomy tests.router_runtime.quality_gates",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=6,
        selected_count=6,
        exit_code=0,
        result_path="tmp/flowguard_background/router_quality_gates_decisions.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("quality_gates_decisions",),
    ),
    TestSuiteEvidence(
        "router_quality_gates_evidence_artifacts",
        command="python -m unittest -v -k test_evidence_quality_package_blocks_stale_and_missing_visual_evidence -k test_route_check_reports_require_hard_gate_verdict_fields -k test_route_check_results_require_router_delivered_check_cards -k test_router_owned_check_proof_rejects_self_attested_and_stale_audit -k test_validate_artifact_reports_gate_decision_issues_together -k test_validate_artifact_reports_node_acceptance_missing_fields_together tests.router_runtime.quality_gates",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=6,
        selected_count=6,
        exit_code=0,
        result_path="tmp/flowguard_background/router_quality_gates_evidence_artifacts.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("quality_gates_evidence_artifacts",),
    ),
    TestSuiteEvidence(
        "router_quality_gates_route_model",
        command="python -m unittest -v -k test_model_miss_review_block_flags_stay_in_sync -k test_node_acceptance_plan_requires_pm_high_standard_recheck -k test_process_route_repair_required_blocks_activation_and_reopens_pm_route_draft -k test_root_contract_freeze_requires_clean_self_interrogation_records -k test_route_draft_requires_product_behavior_model_report tests.router_runtime.quality_gates",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=5,
        selected_count=5,
        exit_code=0,
        result_path="tmp/flowguard_background/router_quality_gates_route_model.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("quality_gates_route_model",),
    ),
    TestSuiteEvidence(
        "router_quality_gates_node_contracts",
        command="python -m unittest -v -k test_next_effective_node_returns_parent_before_sibling_module_after_last_child -k test_node_completion_idempotency_is_scoped_to_active_node -k test_role_output_envelope_hash_survives_same_path_envelope_rewrite -k test_single_agent_answer_records_authorized_role_continuity_without_live_agents tests.router_runtime.quality_gates",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=4,
        selected_count=4,
        exit_code=0,
        result_path="tmp/flowguard_background/router_quality_gates_node_contracts.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("quality_gates_node_contracts",),
    ),
    TestSuiteEvidence(
        "router_material_modeling_intake",
        command="python -m unittest -v -k test_pm_material_understanding_accepts_file_backed_memo_payload -k test_material_acceptance_requires_reviewer_sufficiency_and_pm_absorb_card -k test_material_insufficient_event_records_insufficient_state -k test_material_scan_results_event_requires_result_ledger_absorption tests.router_runtime.material_modeling",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=4,
        selected_count=4,
        exit_code=0,
        result_path="tmp/flowguard_background/router_material_modeling_intake.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("material_modeling_intake",),
    ),
    TestSuiteEvidence(
        "router_material_modeling_scan_relay",
        command="python -m unittest -v -k test_material_scan_direct_relay_blocks_body_hash_mismatch -k test_material_scan_direct_relay_blocks_missing_output_contract -k test_material_scan_mechanical_agent_id_gap_reissues_to_worker tests.router_runtime.material_modeling",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=3,
        selected_count=3,
        exit_code=0,
        result_path="tmp/flowguard_background/router_material_modeling_scan_relay.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("material_modeling_scan_relay",),
    ),
    TestSuiteEvidence(
        "router_material_modeling_modelability",
        command="python -m unittest -v -k test_research_required_blocks_product_architecture_until_absorbed -k test_product_architecture_and_root_contract_gate_route_skeleton -k test_process_route_model_canonical_event_writes_compatibility_alias -k test_legacy_product_officer_model_report_does_not_close_modelability_gate -k test_pm_repair_transaction_commits_material_reissue_generation tests.router_runtime.material_modeling",
        result_status=TEST_STATUS_PASSED,
        evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        test_count=5,
        selected_count=5,
        exit_code=0,
        result_path="tmp/flowguard_background/router_material_modeling_modelability.exit.txt",
        log_root="tmp/flowguard_background",
        background=True,
        owns_state=("material_modeling_modelability",),
    ),
)


def _target_modules_from_structure_evidence(
    modules: tuple[ModuleStructureEvidence, ...],
    *,
    public_entrypoints_by_module: dict[str, tuple[str, ...]] | None = None,
) -> tuple[TargetModuleRecommendation, ...]:
    entrypoints = public_entrypoints_by_module or {}
    return tuple(
        TargetModuleRecommendation(
            module_id=module.module_id,
            path=module.path,
            layer=module.layer,
            owns_function_blocks=module.owns_functions,
            owns_state=module.owns_state,
            owns_side_effects=module.owns_side_effects,
            owns_config=module.owns_config,
            public_entrypoints=entrypoints.get(module.module_id, ()),
            validation_boundaries=module.behavior_contracts,
            rationale=(
                "Owns "
                + (", ".join(module.behavior_contracts) if module.behavior_contracts else module.module_id)
                + " within the parent split."
            ),
        )
        for module in modules
    )


def _function_block_map_from_partitions(
    partitions: tuple[StructurePartitionItem, ...],
) -> tuple[tuple[str, str], ...]:
    non_function_types = {
        "state",
        "state_field",
        "side_effect",
        "config",
        "entrypoint",
        "public_entrypoint",
    }
    return tuple(
        (item.item_id, item.owner_module_id)
        for item in partitions
        if item.ownership == "child"
        and item.owner_module_id
        and item.item_type not in non_function_types
    )


def _state_owner_map(
    modules: tuple[ModuleStructureEvidence, ...],
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (state_id, module.module_id)
        for module in modules
        for state_id in module.owns_state
    )


def _side_effect_owner_map(
    modules: tuple[ModuleStructureEvidence, ...],
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (side_effect_id, module.module_id)
        for module in modules
        for side_effect_id in module.owns_side_effects
    )


def _config_owner_map(
    modules: tuple[ModuleStructureEvidence, ...],
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (config_id, module.module_id)
        for module in modules
        for config_id in module.owns_config
    )


def router_target_structure() -> CodeStructureRecommendation:
    return CodeStructureRecommendation(
        recommendation_id="flowpilot_router_structure_target_v2",
        source_model_id="flowpilot_structure_maintenance",
        source_model_path="simulations/flowpilot_structure_maintenance_model.py",
        parent_module_id="flowpilot_router_structure_split",
        source_model_evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        target_modules=_target_modules_from_structure_evidence(
            ROUTER_STRUCTURE_MODULES,
            public_entrypoints_by_module={
                "router_facade": (
                    "flowpilot_router_public_api",
                    "flowpilot_router_cli",
                ),
            },
        ),
        function_block_map=_function_block_map_from_partitions(ROUTER_STRUCTURE_PARTITIONS),
        state_owner_map=_state_owner_map(ROUTER_STRUCTURE_MODULES),
        side_effect_owner_map=_side_effect_owner_map(ROUTER_STRUCTURE_MODULES),
        config_owner_map=_config_owner_map(ROUTER_STRUCTURE_MODULES),
        public_entrypoint_map=(
            ("flowpilot_router_public_api", "router_facade"),
            ("flowpilot_router_cli", "router_facade"),
        ),
        facade_module_id="router_facade",
        validation_boundaries=(
            "router StructureMesh release review",
            "router TestMesh child suites",
            "router public import and CLI facade parity",
        ),
        rationale=(
            "The router target structure preserves a small skeleton/root-state "
            "parent and assigns CLI, runtime API, event, daemon, startup, "
            "packet, terminal, and control blocker regions to child owners."
        ),
        hierarchical_model_used=True,
    )


def model_target_structure() -> CodeStructureRecommendation:
    return CodeStructureRecommendation(
        recommendation_id="flowpilot_model_scripts_structure_target_v2",
        source_model_id="flowpilot_structure_maintenance",
        source_model_path="simulations/flowpilot_structure_maintenance_model.py",
        parent_module_id="flowpilot_model_script_structure_split",
        source_model_evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        target_modules=_target_modules_from_structure_evidence(
            MODEL_STRUCTURE_MODULES,
            public_entrypoints_by_module={
                "prompt_isolation_facade": ("prompt_isolation_model_import",),
                "cross_plane_facade": ("cross_plane_friction_model_import",),
                "persistent_daemon_facade": ("persistent_router_daemon_model_import",),
                "packet_control_plane_facade": ("packet_control_plane_model_import",),
            },
        ),
        function_block_map=_function_block_map_from_partitions(MODEL_STRUCTURE_PARTITIONS),
        state_owner_map=_state_owner_map(MODEL_STRUCTURE_MODULES),
        side_effect_owner_map=_side_effect_owner_map(MODEL_STRUCTURE_MODULES),
        config_owner_map=_config_owner_map(MODEL_STRUCTURE_MODULES),
        public_entrypoint_map=(
            ("prompt_isolation_model_import", "prompt_isolation_facade"),
            ("cross_plane_friction_model_import", "cross_plane_facade"),
            ("persistent_router_daemon_model_import", "persistent_daemon_facade"),
            ("packet_control_plane_model_import", "packet_control_plane_facade"),
        ),
        facade_module_id="prompt_isolation_facade",
        validation_boundaries=(
            "model script import facades",
            "state and transition child model ownership",
            "invariant and hazard child model ownership",
        ),
        rationale=(
            "The model-script target structure keeps legacy simulation import "
            "facades and assigns state, transition, invariant, hazard, audit, "
            "and strategy regions to focused child modules."
        ),
        hierarchical_model_used=True,
    )


def router_target_test_split() -> TestTargetSplitDerivation:
    return TestTargetSplitDerivation(
        source_model_id="flowpilot_structure_maintenance",
        source_model_path="simulations/flowpilot_structure_maintenance_model.py",
        target_suite_ids=tuple(suite.suite_id for suite in ROUTER_TEST_SUITES),
        covered_partition_item_ids=tuple(item.item_id for item in ROUTER_TEST_PARTITIONS),
        state_owner_fields=tuple(
            sorted(
                {
                    state_id
                    for suite in ROUTER_TEST_SUITES
                    for state_id in suite.owns_state
                }
            )
        ),
        side_effect_owner_fields=tuple(
            sorted(
                {
                    side_effect_id
                    for suite in ROUTER_TEST_SUITES
                    for side_effect_id in suite.owns_side_effects
                }
            )
        ),
        rationale=(
            "The router runtime parent gate is split into explicit child suites "
            "for startup, foreground/controller, packet, route mutation, "
            "terminal lifecycle, closure, resume, control-blocker, PM role-work, "
            "quality-gate, and material/modeling shards."
        ),
    )


def router_structure_plan(
    *,
    decision_scope: str = STRUCTURE_SCOPE_RELEASE,
    required_evidence_tier: str = EVIDENCE_CONFORMANCE_GREEN,
) -> StructureMeshPlan:
    return StructureMeshPlan(
        parent_module_id="flowpilot_router_structure_split",
        decision_scope=decision_scope,
        required_evidence_tier=required_evidence_tier,
        partition_items=ROUTER_STRUCTURE_PARTITIONS,
        child_modules=ROUTER_STRUCTURE_MODULES,
        public_entrypoints=ROUTER_PUBLIC_ENTRYPOINTS,
        target_structure=router_target_structure(),
    )


def router_structure_hazard_plan(name: str) -> StructureMeshPlan:
    if name == "missing_partition_owner":
        return replace(
            router_structure_plan(decision_scope=STRUCTURE_SCOPE_ROUTINE),
            partition_items=(
                StructurePartitionItem("external_event_intake", owner_module_id=""),
            ),
        )
    if name == "duplicate_root_state_owner":
        modules = tuple(
            replace(module, owns_state=module.owns_state + ("route_state_root",))
            if module.module_id == "external_events"
            else module
            for module in ROUTER_STRUCTURE_MODULES
        )
        return replace(router_structure_plan(), child_modules=modules)
    if name == "missing_facade":
        modules = tuple(
            replace(module, facade_retained=False)
            if module.module_id == "router_facade"
            else module
            for module in ROUTER_STRUCTURE_MODULES
        )
        return replace(router_structure_plan(), child_modules=modules)
    if name == "removed_entrypoint":
        entrypoints = tuple(
            replace(entrypoint, compatibility_preserved=False, facade_available=False)
            for entrypoint in ROUTER_PUBLIC_ENTRYPOINTS
        )
        return replace(router_structure_plan(), public_entrypoints=entrypoints)
    if name == "stale_parity":
        modules = tuple(
            replace(module, behavior_parity_current=False)
            if module.module_id == "external_events"
            else module
            for module in ROUTER_STRUCTURE_MODULES
        )
        return replace(router_structure_plan(), child_modules=modules)
    if name == "insufficient_release_evidence":
        modules = tuple(
            replace(module, behavior_parity_tier=EVIDENCE_ABSTRACT_GREEN)
            if module.module_id == "external_events"
            else module
            for module in ROUTER_STRUCTURE_MODULES
        )
        return replace(router_structure_plan(), child_modules=modules)
    raise ValueError(f"unknown structure hazard: {name}")


def model_structure_plan(
    *,
    decision_scope: str = STRUCTURE_SCOPE_RELEASE,
    required_evidence_tier: str = EVIDENCE_CONFORMANCE_GREEN,
) -> StructureMeshPlan:
    return StructureMeshPlan(
        parent_module_id="flowpilot_model_script_structure_split",
        decision_scope=decision_scope,
        required_evidence_tier=required_evidence_tier,
        partition_items=MODEL_STRUCTURE_PARTITIONS,
        child_modules=MODEL_STRUCTURE_MODULES,
        public_entrypoints=MODEL_PUBLIC_ENTRYPOINTS,
        target_structure=model_target_structure(),
    )


def model_structure_hazard_plan(name: str) -> StructureMeshPlan:
    if name == "missing_model_partition_owner":
        return replace(
            model_structure_plan(decision_scope=STRUCTURE_SCOPE_ROUTINE),
            partition_items=(
                StructurePartitionItem("prompt_isolation_state", owner_module_id=""),
            ),
        )
    if name == "duplicate_model_state_owner":
        modules = tuple(
            replace(module, owns_state=module.owns_state + ("prompt_isolation_state",))
            if module.module_id == "prompt_isolation_transitions"
            else module
            for module in MODEL_STRUCTURE_MODULES
        )
        return replace(model_structure_plan(), child_modules=modules)
    if name == "missing_model_facade":
        modules = tuple(
            replace(module, facade_retained=False)
            if module.module_id in {
                "prompt_isolation_facade",
                "cross_plane_facade",
                "persistent_daemon_facade",
                "packet_control_plane_facade",
            }
            else module
            for module in MODEL_STRUCTURE_MODULES
        )
        return replace(model_structure_plan(), child_modules=modules)
    if name == "removed_model_entrypoint":
        entrypoints = tuple(
            replace(entrypoint, compatibility_preserved=False, facade_available=False)
            for entrypoint in MODEL_PUBLIC_ENTRYPOINTS
        )
        return replace(model_structure_plan(), public_entrypoints=entrypoints)
    if name == "stale_model_parity":
        modules = tuple(
            replace(module, behavior_parity_current=False)
            if module.module_id == "cross_plane_transitions"
            else module
            for module in MODEL_STRUCTURE_MODULES
        )
        return replace(model_structure_plan(), child_modules=modules)
    if name == "insufficient_model_release_evidence":
        modules = tuple(
            replace(module, behavior_parity_tier=EVIDENCE_ABSTRACT_GREEN)
            if module.module_id == "persistent_daemon_facade"
            else module
            for module in MODEL_STRUCTURE_MODULES
        )
        return replace(model_structure_plan(), child_modules=modules)
    raise ValueError(f"unknown model structure hazard: {name}")


def router_testmesh_plan(
    *,
    decision_scope: str = TEST_SCOPE_RELEASE,
    required_evidence_tier: str = EVIDENCE_CONFORMANCE_GREEN,
) -> TestMeshPlan:
    return TestMeshPlan(
        parent_suite_id="flowpilot_router_runtime_testmesh",
        decision_scope=decision_scope,
        required_evidence_tier=required_evidence_tier,
        partition_items=ROUTER_TEST_PARTITIONS,
        child_suites=ROUTER_TEST_SUITES,
        target_split_derivation=router_target_test_split(),
    )


def router_testmesh_hazard_plan(name: str) -> TestMeshPlan:
    if name == "missing_child_owner":
        return replace(
            router_testmesh_plan(decision_scope=TEST_SCOPE_ROUTINE),
            partition_items=(TestPartitionItem("startup_bootstrap", owner_suite_id=""),),
        )
    if name == "duplicate_state_owner":
        suites = ROUTER_TEST_SUITES + (
            replace(
                ROUTER_TEST_SUITES[1],
                suite_id="router_foreground_duplicate",
                owns_state=("startup_bootstrap",),
            ),
        )
        return replace(router_testmesh_plan(), child_suites=suites)
    if name == "hidden_skipped_tests":
        suites = tuple(
            replace(suite, skipped_count=1, skipped_visible=False)
            if suite.suite_id == "router_cards"
            else suite
            for suite in ROUTER_TEST_SUITES
        )
        return replace(router_testmesh_plan(), child_suites=suites)
    if name == "stale_evidence":
        suites = tuple(
            replace(suite, evidence_current=False)
            if suite.suite_id == "router_route_mutation_contracts"
            else suite
            for suite in ROUTER_TEST_SUITES
        )
        return replace(router_testmesh_plan(), child_suites=suites)
    if name == "timeout_suite":
        suites = tuple(
            replace(suite, result_status=TEST_STATUS_TIMEOUT, exit_code=124)
            if suite.suite_id == "router_material_modeling_modelability"
            else suite
            for suite in ROUTER_TEST_SUITES
        )
        return replace(router_testmesh_plan(), child_suites=suites)
    if name == "progress_only_background":
        suites = tuple(
            replace(
                suite,
                progress_only=True,
                has_exit_artifact=False,
                has_result_artifact=False,
            )
            if suite.suite_id == "router_resume_reentry"
            else suite
            for suite in ROUTER_TEST_SUITES
        )
        return replace(router_testmesh_plan(), child_suites=suites)
    if name == "missing_background_artifact":
        suites = tuple(
            replace(suite, has_exit_artifact=False)
            if suite.suite_id == "router_startup_runtime"
            else suite
            for suite in ROUTER_TEST_SUITES
        )
        return replace(router_testmesh_plan(), child_suites=suites)
    if name == "unbounded_background_fanout":
        suites = tuple(
            replace(suite, result_status=TEST_STATUS_FAILED, exit_code=3221225794)
            if suite.suite_id == "router_background_supervisor"
            else suite
            for suite in ROUTER_TEST_SUITES
        )
        return replace(router_testmesh_plan(), child_suites=suites)
    if name == "release_required_stale":
        suites = ROUTER_TEST_SUITES + (
            TestSuiteEvidence(
                "release_router_parent",
                command="python scripts/run_test_tier.py --tier release --background",
                result_status=TEST_STATUS_PASSED,
                evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
                evidence_current=False,
                release_required=True,
            ),
        )
        return replace(router_testmesh_plan(), child_suites=suites)
    raise ValueError(f"unknown testmesh hazard: {name}")


STRUCTURE_HAZARDS = (
    "missing_partition_owner",
    "duplicate_root_state_owner",
    "missing_facade",
    "removed_entrypoint",
    "stale_parity",
    "insufficient_release_evidence",
)

MODEL_STRUCTURE_HAZARDS = (
    "missing_model_partition_owner",
    "duplicate_model_state_owner",
    "missing_model_facade",
    "removed_model_entrypoint",
    "stale_model_parity",
    "insufficient_model_release_evidence",
)

TESTMESH_HAZARDS = (
    "missing_child_owner",
    "duplicate_state_owner",
    "hidden_skipped_tests",
    "stale_evidence",
    "timeout_suite",
    "progress_only_background",
    "missing_background_artifact",
    "unbounded_background_fanout",
    "release_required_stale",
)
