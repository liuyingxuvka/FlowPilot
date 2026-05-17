"""FlowGuard model for the FlowPilot router facade and PromptStore split."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
from typing import Any

from flowguard import (
    CodeStructureRecommendation,
    EVIDENCE_CONFORMANCE_GREEN,
    ModuleStructureEvidence,
    PublicEntrypointEvidence,
    STRUCTURE_SCOPE_RELEASE,
    TEST_SCOPE_RELEASE,
    TEST_STATUS_PASSED,
    StructureMeshPlan,
    StructurePartitionItem,
    TestMeshPlan,
    TestPartitionItem,
    TestTargetSplitDerivation,
    TestSuiteEvidence,
    TargetModuleRecommendation,
)


ROOT = Path(__file__).resolve().parents[1]
PROMPT_MANIFEST = ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit" / "prompts" / "manifest.json"


@dataclass(frozen=True)
class PromptAssetEvidence:
    prompt_id: str
    path: str
    sha256: str
    included_in_install_checks: bool = True
    inline_fallback_allowed: bool = False
    template_variables_declared: bool = True


@dataclass(frozen=True)
class RouterFacadeSplitEvidence:
    child_module_count: int = 40
    max_child_module_count: int = 48
    micro_module_count: int = 0
    max_micro_module_count: int = 2
    required_coarse_owner_ids: tuple[str, ...] = (
        "runtime_state",
        "startup_flow",
        "controller_scheduler",
        "controller_repair",
        "action_factory",
        "payload_contracts",
        "lifecycle_requests",
        "route_artifacts",
        "system_cards",
        "expected_waits",
        "self_interrogation",
        "work_packets",
        "events_repair",
        "event_dispatcher",
        "route_frontier",
        "terminal_ledger",
    )
    coarse_owner_ids: tuple[str, ...] = (
        "runtime_state",
        "startup_flow",
        "controller_scheduler",
        "controller_repair",
        "action_factory",
        "payload_contracts",
        "lifecycle_requests",
        "route_artifacts",
        "system_cards",
        "expected_waits",
        "self_interrogation",
        "work_packets",
        "events_repair",
        "event_dispatcher",
        "route_frontier",
        "terminal_ledger",
    )
    prompt_assets: tuple[PromptAssetEvidence, ...] = ()
    background_exit_artifacts_required: bool = True


def _sha256_text(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def prompt_assets_from_manifest() -> tuple[PromptAssetEvidence, ...]:
    import json

    manifest = json.loads(PROMPT_MANIFEST.read_text(encoding="utf-8"))
    return tuple(
        PromptAssetEvidence(
            prompt_id=str(entry["id"]),
            path=str(entry["path"]),
            sha256=str(entry["sha256"]),
        )
        for entry in manifest.get("prompts", [])
    )


ROUTER_FACADE_ENTRYPOINTS = (
    PublicEntrypointEvidence(
        "flowpilot_router_import",
        old_path="skills/flowpilot/assets/flowpilot_router.py",
        new_path="skills/flowpilot/assets/flowpilot_router.py",
        parity_evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        evidence_path="simulations/flowpilot_router_facade_split_results.json",
        release_required=True,
    ),
    PublicEntrypointEvidence(
        "flowpilot_router_cli",
        entrypoint_type="cli",
        old_path="python skills/flowpilot/assets/flowpilot_router.py",
        new_path="python skills/flowpilot/assets/flowpilot_router.py",
        parity_evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        evidence_path="simulations/flowpilot_router_facade_split_results.json",
        release_required=True,
    ),
)

ROUTER_FACADE_PARTITIONS = (
    StructurePartitionItem(
        "public_router_facade",
        item_type="public_entrypoint",
        owner_module_id="router_facade",
        ownership="parent",
        public_surface=True,
    ),
    StructurePartitionItem(
        "route_state_root",
        item_type="state",
        owner_module_id="router_facade",
        ownership="parent",
    ),
    StructurePartitionItem(
        "prompt_manifest_loading",
        item_type="function_cluster",
        owner_module_id="prompt_store",
        old_path="flowpilot_router inline prompt literals",
        new_path="flowpilot_prompt_store",
    ),
    StructurePartitionItem(
        "prompt_assets",
        item_type="config",
        owner_module_id="prompt_assets",
        old_path="flowpilot_router inline strings",
        new_path="runtime_kit/prompts",
    ),
    StructurePartitionItem(
        "card_post_ack_policy",
        item_type="prompt",
        owner_module_id="prompt_delivery",
        new_path="runtime_kit/prompts/cards",
    ),
    StructurePartitionItem(
        "controller_table_prompt",
        item_type="prompt",
        owner_module_id="prompt_delivery",
        new_path="runtime_kit/prompts/controller",
    ),
    StructurePartitionItem(
        "startup_heartbeat_prompt",
        item_type="prompt",
        owner_module_id="prompt_delivery",
        new_path="runtime_kit/prompts/startup",
    ),
    StructurePartitionItem(
        "controller_ledger_paths",
        item_type="function_cluster",
        owner_module_id="controller_ledger",
        old_path="flowpilot_router controller ledger path helpers",
        new_path="flowpilot_router_controller_ledger",
    ),
    StructurePartitionItem(
        "router_scheduler_projection",
        item_type="function_cluster",
        owner_module_id="controller_ledger",
        old_path="flowpilot_router scheduler progress/barrier helpers",
        new_path="flowpilot_router_controller_ledger",
    ),
    StructurePartitionItem(
        "card_delivery_ledgers",
        item_type="function_cluster",
        owner_module_id="card_delivery",
        old_path="flowpilot_router card/return ledger helpers",
        new_path="flowpilot_router_card_delivery",
    ),
    StructurePartitionItem(
        "card_return_settlement",
        item_type="function_cluster",
        owner_module_id="card_returns",
        old_path="flowpilot_router ACK return settlement helpers",
        new_path="flowpilot_router_card_returns",
    ),
    StructurePartitionItem(
        "role_io_protocol",
        item_type="function_cluster",
        owner_module_id="role_io_protocol",
        old_path="flowpilot_router role I/O protocol helpers",
        new_path="flowpilot_router_role_io_protocol",
    ),
    StructurePartitionItem(
        "event_identity",
        item_type="function_cluster",
        owner_module_id="event_identity",
        old_path="flowpilot_router event payload/idempotency helpers",
        new_path="flowpilot_router_event_identity",
    ),
    StructurePartitionItem(
        "daemon_runtime",
        item_type="function_cluster",
        owner_module_id="daemon_runtime",
        old_path="flowpilot_router daemon lock/status/tick helpers",
        new_path="flowpilot_router_daemon_runtime",
    ),
    StructurePartitionItem(
        "runtime_state",
        item_type="function_cluster",
        owner_module_id="runtime_state",
        old_path="flowpilot_router run/bootstrap state helpers",
        new_path="flowpilot_router_runtime_state",
    ),
    StructurePartitionItem(
        "router_protocol_catalog",
        item_type="config",
        owner_module_id="protocol_catalog",
        old_path="flowpilot_router top-level schema/action/event/gate catalogs",
        new_path="flowpilot_router_protocol_catalog",
    ),
    StructurePartitionItem(
        "startup_flow",
        item_type="function_cluster",
        owner_module_id="startup_flow",
        old_path="flowpilot_router startup/bootloader/resume phase bodies",
        new_path="flowpilot_router_startup_flow",
    ),
    StructurePartitionItem(
        "self_interrogation",
        item_type="function_cluster",
        owner_module_id="self_interrogation",
        old_path="flowpilot_router self-interrogation status helpers",
        new_path="flowpilot_router_self_interrogation",
    ),
    StructurePartitionItem(
        "payload_contracts",
        item_type="function_cluster",
        owner_module_id="payload_contracts",
        old_path="flowpilot_router payload contract builders",
        new_path="flowpilot_router_payload_contracts",
    ),
    StructurePartitionItem(
        "controller_scheduler",
        item_type="function_cluster",
        owner_module_id="controller_scheduler",
        old_path="flowpilot_router controller scheduler/receipt/standby bodies",
        new_path="flowpilot_router_controller_scheduler",
    ),
    StructurePartitionItem(
        "controller_repair",
        item_type="function_cluster",
        owner_module_id="controller_repair",
        old_path="flowpilot_router controller repair and postcondition reconciliation helpers",
        new_path="flowpilot_router_controller_repair",
    ),
    StructurePartitionItem(
        "action_factory",
        item_type="function_cluster",
        owner_module_id="action_factory",
        old_path="flowpilot_router action factory and dispatch-recipient gate helpers",
        new_path="flowpilot_router_action_factory",
    ),
    StructurePartitionItem(
        "work_packets",
        item_type="function_cluster",
        owner_module_id="work_packets",
        old_path="flowpilot_router material/research/current-node/PM packet bodies",
        new_path="flowpilot_router_work_packets",
    ),
    StructurePartitionItem(
        "route_artifacts",
        item_type="function_cluster",
        owner_module_id="route_artifacts",
        old_path="flowpilot_router PM-authored route/product/node artifact writers",
        new_path="flowpilot_router_route_artifacts",
    ),
    StructurePartitionItem(
        "events_repair",
        item_type="function_cluster",
        owner_module_id="events_repair",
        old_path="flowpilot_router control blocker and repair transaction bodies",
        new_path="flowpilot_router_events_repair",
    ),
    StructurePartitionItem(
        "lifecycle_requests",
        item_type="function_cluster",
        owner_module_id="lifecycle_requests",
        old_path="flowpilot_router run lifecycle request and protocol-dead-end helpers",
        new_path="flowpilot_router_lifecycle_requests",
    ),
    StructurePartitionItem(
        "event_dispatcher",
        item_type="function_cluster",
        owner_module_id="event_dispatcher",
        old_path="flowpilot_router external event dispatcher body",
        new_path="flowpilot_router_event_dispatcher",
    ),
    StructurePartitionItem(
        "system_cards",
        item_type="function_cluster",
        owner_module_id="system_cards",
        old_path="flowpilot_router system-card action selection and delivery commit helpers",
        new_path="flowpilot_router_system_cards",
    ),
    StructurePartitionItem(
        "expected_waits",
        item_type="function_cluster",
        owner_module_id="expected_waits",
        old_path="flowpilot_router expected role wait and pending event reconciliation helpers",
        new_path="flowpilot_router_expected_waits",
    ),
    StructurePartitionItem(
        "route_frontier",
        item_type="function_cluster",
        owner_module_id="route_frontier",
        old_path="flowpilot_router route/frontier/node completion bodies",
        new_path="flowpilot_router_route_frontier",
    ),
    StructurePartitionItem(
        "terminal_ledger",
        item_type="function_cluster",
        owner_module_id="terminal_ledger",
        old_path="flowpilot_router terminal ledger/replay/closure bodies",
        new_path="flowpilot_router_terminal_ledger",
    ),
)

ROUTER_FACADE_MODULES = (
    ModuleStructureEvidence(
        "router_facade",
        path="skills/flowpilot/assets/flowpilot_router.py",
        layer="parent",
        owns_functions=("main", "next_action", "apply_action", "record_external_event"),
        owns_state=("route_state_root",),
        behavior_contracts=("public imports", "CLI", "root run-state persistence"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "prompt_store",
        path="skills/flowpilot/assets/flowpilot_prompt_store.py",
        owns_functions=("load_prompt_manifest", "load_prompt_text", "render_prompt_text"),
        owns_config=("prompt_manifest",),
        behavior_contracts=("strict prompt rendering", "hash validation", "no inline fallback"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "prompt_delivery",
        path="skills/flowpilot/assets/flowpilot_router_prompt_delivery.py",
        owns_functions=("card_checkin_instruction", "controller_table_prompt", "startup_heartbeat_prompt"),
        behavior_contracts=("card ACK instruction", "controller table prompt", "heartbeat prompt rendering"),
        dependencies=("prompt_store",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "prompt_assets",
        path="skills/flowpilot/assets/runtime_kit/prompts",
        owns_config=("prompt_assets",),
        behavior_contracts=("runtime-kit copy", "install-check inclusion", "content hash authority"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "controller_ledger",
        path="skills/flowpilot/assets/flowpilot_router_controller_ledger.py",
        owns_functions=("controller_action_ledger_path", "router_scheduler_progress_class", "prepare_router_scheduled_action"),
        owns_config=("controller_ledger_schemas",),
        behavior_contracts=("ledger path compatibility", "scheduler progress projection", "facade wrappers"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "card_delivery",
        path="skills/flowpilot/assets/flowpilot_router_card_delivery.py",
        owns_functions=("read_card_ledger", "read_return_event_ledger", "card_return_event_for_card"),
        owns_state=("card_delivery_ledgers",),
        behavior_contracts=("card ledger schema", "return event mapping", "delivery attempt identity"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "card_returns",
        path="skills/flowpilot/assets/flowpilot_router_card_returns.py",
        owns_functions=(
            "_pending_return_records",
            "_next_pending_card_return_action",
            "_apply_card_return_event_check",
            "_run_router_return_settlement_finalizers",
        ),
        owns_state=("card_return_settlement",),
        dependencies=("card_delivery", "router_facade"),
        behavior_contracts=(
            "ACK wait settlement",
            "ACK does not complete output-bearing work",
            "startup user-intake release remains mail-delivery gated",
        ),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "role_io_protocol",
        path="skills/flowpilot/assets/flowpilot_router_role_io_protocol.py",
        owns_functions=("role_io_protocol_payload", "append_role_io_protocol_injections", "role_io_protocol_receipt_for_agent"),
        owns_state=("role_io_protocol",),
        behavior_contracts=("role lifecycle protocol hash", "injection receipts", "role output envelope authority"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "event_identity",
        path="skills/flowpilot/assets/flowpilot_router_event_identity.py",
        owns_functions=(
            "_normalize_record_event_payload",
            "_scoped_event_identity",
            "_check_scoped_event_retry_budget",
            "_already_recorded_external_event_result",
        ),
        owns_state=("event_identity",),
        dependencies=("router_facade",),
        behavior_contracts=(
            "event envelope validation",
            "external event idempotency",
            "retry budget enforcement",
            "already-recorded event replay",
        ),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "daemon_runtime",
        path="skills/flowpilot/assets/flowpilot_router_daemon_runtime.py",
        owns_functions=(
            "_acquire_router_daemon_lock",
            "_write_router_daemon_status",
            "_router_daemon_tick",
            "run_router_daemon",
            "stop_router_daemon",
        ),
        owns_state=("daemon_runtime",),
        dependencies=("controller_ledger", "router_facade"),
        behavior_contracts=(
            "daemon lock ownership",
            "daemon status lifecycle",
            "bounded queue fill",
            "foreground console hidden by tier runner",
        ),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "runtime_state",
        path="skills/flowpilot/assets/flowpilot_router_runtime_state.py",
        owns_functions=("new_bootstrap_state", "new_run_state", "load_run_state", "save_run_state"),
        owns_state=("bootstrap_state", "run_state", "continuation_quarantine"),
        dependencies=("router_facade",),
        behavior_contracts=("run state shape", "bootstrap state persistence", "runtime state compatibility wrappers"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "protocol_catalog",
        path="skills/flowpilot/assets/flowpilot_router_protocol_catalog.py",
        owns_functions=(
            "_public_gate_contract",
            "_gate_contract_for_id",
            "_gate_contract_for_card",
            "_gate_contract_for_event",
            "_gate_completion_wait_group",
        ),
        owns_config=("router_protocol_catalog",),
        behavior_contracts=(
            "schema constants",
            "boot and system-card catalogs",
            "external event metadata",
            "gate contract tables",
            "model gate alias tables",
        ),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "startup_flow",
        path="skills/flowpilot/assets/flowpilot_router_startup_flow.py",
        owns_functions=("compute_bootloader_action", "apply_bootloader_action", "_next_resume_action", "_next_startup_display_action"),
        owns_state=("startup_bootloader", "startup_answers", "resume_role_recovery"),
        dependencies=("runtime_state", "controller_scheduler", "router_facade"),
        behavior_contracts=("startup bootloader action ordering", "startup/resume phase action selection", "role recovery persistence"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "controller_scheduler",
        path="skills/flowpilot/assets/flowpilot_router_controller_scheduler.py",
        owns_functions=("_write_controller_action_entry", "_reconcile_controller_receipts", "foreground_controller_standby", "controller_patrol_timer"),
        owns_state=("router_scheduler_ledger", "controller_action_rows", "controller_receipts", "foreground_standby"),
        dependencies=("controller_ledger", "router_facade"),
        behavior_contracts=("controller receipt reconciliation", "scheduler row lifecycle", "standby/patrol status compatibility"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "controller_repair",
        path="skills/flowpilot/assets/flowpilot_router_controller_repair.py",
        owns_functions=(
            "_close_waiting_controller_actions_for_external_event",
            "_fold_mail_delivery_postcondition",
            "_schedule_controller_deliverable_repair",
            "_reclaim_router_owned_postcondition_from_artifact",
        ),
        owns_state=("controller_postcondition_repairs",),
        dependencies=("controller_scheduler", "events_repair", "router_facade"),
        behavior_contracts=(
            "controller receipt repair",
            "mail delivery postcondition folding",
            "router-owned postcondition reclaim",
        ),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "action_factory",
        path="skills/flowpilot/assets/flowpilot_router_action_factory.py",
        owns_functions=("make_action", "_dispatch_gate_wait_action", "_apply_dispatch_recipient_gate"),
        owns_state=("controller_action_envelope", "dispatch_recipient_gate"),
        dependencies=("system_cards", "work_packets", "router_facade"),
        behavior_contracts=("action envelope construction", "dispatch-recipient gating", "formal work ACK preflight"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "work_packets",
        path="skills/flowpilot/assets/flowpilot_router_work_packets.py",
        owns_functions=("_next_material_packet_action", "_next_research_packet_action", "_next_current_node_packet_action", "_next_pm_role_work_request_action"),
        owns_state=("packet_ledger", "parallel_packet_batches", "pm_role_work_index", "current_node_packet_records"),
        dependencies=("route_frontier", "router_facade"),
        behavior_contracts=("packet relay lifecycle", "PM role-work lifecycle", "current-node packet absorption"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "route_artifacts",
        path="skills/flowpilot/assets/flowpilot_router_route_artifacts.py",
        owns_functions=(
            "_write_product_function_architecture",
            "_write_root_acceptance_contract",
            "_write_node_acceptance_plan",
            "_write_evidence_quality_package",
        ),
        owns_state=("route_artifact_records", "acceptance_contracts", "node_acceptance_plans"),
        dependencies=("route_frontier", "work_packets", "router_facade"),
        behavior_contracts=("PM route artifact writes", "node acceptance plan validation", "evidence package persistence"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "events_repair",
        path="skills/flowpilot/assets/flowpilot_router_events_repair.py",
        owns_functions=("_write_control_blocker", "_next_control_blocker_action", "_write_control_blocker_repair_decision", "_finalize_repair_transaction_outcome"),
        owns_state=("active_control_blocker", "repair_transactions", "gate_decisions"),
        dependencies=("event_identity", "work_packets", "router_facade"),
        behavior_contracts=("control blocker materialization", "repair transaction finalization", "gate decision validation"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "lifecycle_requests",
        path="skills/flowpilot/assets/flowpilot_router_lifecycle_requests.py",
        owns_functions=("_write_run_lifecycle_request", "_write_protocol_dead_end_lifecycle", "_try_write_control_blocker_for_exception"),
        owns_state=("run_lifecycle_requests", "protocol_dead_end_records"),
        dependencies=("events_repair", "terminal_ledger", "router_facade"),
        behavior_contracts=("lifecycle request persistence", "protocol dead-end blocking", "exception-to-blocker routing"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "event_dispatcher",
        path="skills/flowpilot/assets/flowpilot_router_event_dispatcher.py",
        owns_functions=("_record_external_event_unchecked",),
        owns_state=("external_event_dispatch",),
        dependencies=("events_repair", "route_frontier", "terminal_ledger", "work_packets", "router_facade"),
        behavior_contracts=("external event dispatch compatibility", "wait-action settlement", "event finalizer delegation"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "system_cards",
        path="skills/flowpilot/assets/flowpilot_router_system_cards.py",
        owns_functions=(
            "_next_system_card_action",
            "_next_system_card_bundle_action",
            "_commit_system_card_delivery_artifact",
            "_commit_system_card_bundle_delivery_artifact",
        ),
        owns_state=("system_card_delivery_actions", "system_card_bundle_delivery_actions"),
        dependencies=("card_delivery", "card_returns", "router_facade"),
        behavior_contracts=("system-card action ordering", "bundle delivery commit", "direct ACK token construction"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "expected_waits",
        path="skills/flowpilot/assets/flowpilot_router_expected_waits.py",
        owns_functions=(
            "_expected_role_decision_wait_action",
            "_pending_expected_external_event_groups",
            "_reconcile_pending_role_wait_from_packet_status",
            "_record_router_reconciled_external_event",
        ),
        owns_state=("expected_role_waits", "pending_event_groups"),
        dependencies=("event_dispatcher", "work_packets", "router_facade"),
        behavior_contracts=("role decision wait construction", "pending event grouping", "packet-status wait reconciliation"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "route_frontier",
        path="skills/flowpilot/assets/flowpilot_router_route_frontier.py",
        owns_functions=("_active_frontier", "_legal_next_action_context", "_mark_frontier_node_completed", "_write_node_completion_ledger"),
        owns_state=("execution_frontier", "route_state_snapshots", "node_completion_ledger"),
        dependencies=("router_facade",),
        behavior_contracts=("route/frontier projection", "legal next-action context", "node completion lifecycle"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "payload_contracts",
        path="skills/flowpilot/assets/flowpilot_router_payload_contracts.py",
        owns_functions=("_payload_contract", "_startup_answers_payload_contract", "_pm_terminal_closure_payload_contract"),
        owns_config=("payload_contract_builders",),
        dependencies=("protocol_catalog", "router_facade"),
        behavior_contracts=("role payload contract builders", "display payload contract builders", "PM decision payload contracts"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "self_interrogation",
        path="skills/flowpilot/assets/flowpilot_router_self_interrogation.py",
        owns_functions=("_self_interrogation_status", "_self_interrogation_record_issues", "_require_clean_self_interrogation"),
        owns_state=("self_interrogation_index", "pm_suggestion_ledger"),
        dependencies=("router_facade",),
        behavior_contracts=("self-interrogation issue status", "PM suggestion ledger cleanliness", "startup self-check gating"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "terminal_ledger",
        path="skills/flowpilot/assets/flowpilot_router_terminal_ledger.py",
        owns_functions=("_write_final_route_wide_ledger", "_write_terminal_backward_replay", "_write_terminal_closure_suite", "reconcile_current_run"),
        owns_state=("final_route_wide_ledger", "terminal_backward_replay", "terminal_closure_suite"),
        dependencies=("route_frontier", "runtime_state", "router_facade"),
        behavior_contracts=("terminal ledger traceability", "closure suite persistence", "terminal status reconciliation"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
)


ROUTER_FACADE_TARGET_RATIONALES = {
    "router_facade": "Retains public import, CLI, and root state coordination while delegating owned regions.",
    "prompt_store": "Owns prompt manifest loading, template rendering, and prompt hash authority.",
    "prompt_delivery": "Owns prompt-backed delivery text used by cards, controller tables, and startup heartbeats.",
    "prompt_assets": "Owns external prompt asset files and install-time prompt freshness evidence.",
    "controller_ledger": "Owns controller ledger paths and scheduler projection helper contracts.",
    "card_delivery": "Owns card ledger read/write contract and delivery attempt identity helpers.",
    "card_returns": "Owns ACK return settlement and output-bearing work clearance rules.",
    "role_io_protocol": "Owns role I/O envelope protocol, injection receipts, and lifecycle hash authority.",
    "event_identity": "Owns event idempotency and scoped retry-budget behavior.",
    "daemon_runtime": "Owns daemon lock, status, and tick lifecycle helpers.",
    "runtime_state": "Owns bootstrap and run-state factories plus persistence wrappers.",
    "protocol_catalog": "Owns router schemas, action catalogs, event metadata, gate contracts, and alias tables.",
    "startup_flow": "Owns startup, bootloader, resume, and role-recovery action bodies.",
    "controller_scheduler": "Owns controller scheduling, receipt reconciliation, standby, and patrol behavior.",
    "controller_repair": "Owns controller deliverable repair, postcondition reclaim, and mail-delivery folding.",
    "action_factory": "Owns action envelope construction and dispatch-recipient gate policy.",
    "work_packets": "Owns material, research, current-node, and PM role-work packet flow.",
    "route_artifacts": "Owns PM route, product, node-acceptance, and evidence artifact writes.",
    "events_repair": "Owns control blockers, repair transactions, and gate-decision validation.",
    "lifecycle_requests": "Owns run lifecycle requests, protocol dead-end records, and exception blocker routing.",
    "event_dispatcher": "Owns external event dispatch routing and event-finalizer delegation.",
    "system_cards": "Owns system-card action selection, bundle delivery, and direct ACK tokens.",
    "expected_waits": "Owns expected role waits, pending event grouping, and stale-wait reconciliation.",
    "route_frontier": "Owns route/frontier projection and node-completion lifecycle.",
    "payload_contracts": "Owns payload contract builder helpers for startup, PM, display, and terminal actions.",
    "self_interrogation": "Owns self-interrogation status, issue, and PM suggestion cleanliness helpers.",
    "terminal_ledger": "Owns terminal ledger, replay, closure, and reconciliation outputs.",
}


ROUTER_FACADE_FUNCTION_BLOCK_MAP = (
    ("prompt_manifest_loading", "prompt_store"),
    ("card_post_ack_policy", "prompt_delivery"),
    ("controller_table_prompt", "prompt_delivery"),
    ("startup_heartbeat_prompt", "prompt_delivery"),
    ("controller_ledger_paths", "controller_ledger"),
    ("router_scheduler_projection", "controller_ledger"),
    ("card_delivery_ledgers", "card_delivery"),
    ("card_return_settlement", "card_returns"),
    ("role_io_protocol", "role_io_protocol"),
    ("event_identity", "event_identity"),
    ("daemon_runtime", "daemon_runtime"),
    ("runtime_state", "runtime_state"),
    ("_public_gate_contract", "protocol_catalog"),
    ("_gate_contract_for_id", "protocol_catalog"),
    ("_gate_contract_for_card", "protocol_catalog"),
    ("_gate_contract_for_event", "protocol_catalog"),
    ("_gate_completion_wait_group", "protocol_catalog"),
    ("startup_flow", "startup_flow"),
    ("self_interrogation", "self_interrogation"),
    ("payload_contracts", "payload_contracts"),
    ("controller_scheduler", "controller_scheduler"),
    ("controller_repair", "controller_repair"),
    ("action_factory", "action_factory"),
    ("work_packets", "work_packets"),
    ("route_artifacts", "route_artifacts"),
    ("events_repair", "events_repair"),
    ("lifecycle_requests", "lifecycle_requests"),
    ("event_dispatcher", "event_dispatcher"),
    ("system_cards", "system_cards"),
    ("expected_waits", "expected_waits"),
    ("route_frontier", "route_frontier"),
    ("terminal_ledger", "terminal_ledger"),
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


def router_facade_target_structure() -> CodeStructureRecommendation:
    return CodeStructureRecommendation(
        recommendation_id="flowpilot_router_facade_target_structure_v2",
        source_model_id="flowpilot_router_facade_prompt_store_split",
        source_model_path="simulations/flowpilot_router_facade_split_model.py",
        parent_module_id="flowpilot_router_facade_prompt_store_split",
        source_model_evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        target_modules=tuple(
            TargetModuleRecommendation(
                module_id=module.module_id,
                path=module.path,
                layer=module.layer,
                owns_function_blocks=module.owns_functions,
                owns_state=module.owns_state,
                owns_side_effects=module.owns_side_effects,
                owns_config=module.owns_config,
                public_entrypoints=(
                    ("flowpilot_router_import", "flowpilot_router_cli")
                    if module.module_id == "router_facade"
                    else ()
                ),
                validation_boundaries=module.behavior_contracts,
                rationale=ROUTER_FACADE_TARGET_RATIONALES[module.module_id],
            )
            for module in ROUTER_FACADE_MODULES
        ),
        function_block_map=ROUTER_FACADE_FUNCTION_BLOCK_MAP,
        state_owner_map=_state_owner_map(ROUTER_FACADE_MODULES),
        side_effect_owner_map=_side_effect_owner_map(ROUTER_FACADE_MODULES),
        config_owner_map=_config_owner_map(ROUTER_FACADE_MODULES),
        public_entrypoint_map=(
            ("public_router_facade", "router_facade"),
            ("flowpilot_router_import", "router_facade"),
            ("flowpilot_router_cli", "router_facade"),
        ),
        facade_module_id="router_facade",
        validation_boundaries=(
            "prompt store unit tests",
            "router boundary tests",
            "router runtime child suites",
            "install prompt asset audit",
        ),
        rationale=(
            "FlowGuard target structure keeps the router facade as the public "
            "boundary and assigns prompt, runtime, startup, packet, repair, "
            "route, and terminal ownership to coarse child modules."
        ),
        hierarchical_model_used=True,
    )


def router_facade_structure_plan() -> StructureMeshPlan:
    return StructureMeshPlan(
        parent_module_id="flowpilot_router_facade_prompt_store_split",
        decision_scope=STRUCTURE_SCOPE_RELEASE,
        required_evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        partition_items=ROUTER_FACADE_PARTITIONS,
        child_modules=ROUTER_FACADE_MODULES,
        public_entrypoints=ROUTER_FACADE_ENTRYPOINTS,
        target_structure=router_facade_target_structure(),
    )


def router_facade_testmesh_plan() -> TestMeshPlan:
    return TestMeshPlan(
        parent_suite_id="flowpilot_router_facade_prompt_store_testmesh",
        decision_scope=TEST_SCOPE_RELEASE,
        required_evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        partition_items=(
            TestPartitionItem("prompt_store", owner_suite_id="prompt_store_unit"),
            TestPartitionItem("router_facade_prompt_delivery", owner_suite_id="router_boundaries"),
            TestPartitionItem("card_return_settlement", owner_suite_id="router_ack_return"),
            TestPartitionItem("event_identity", owner_suite_id="event_contract"),
            TestPartitionItem("daemon_runtime", owner_suite_id="startup_daemon"),
            TestPartitionItem("runtime_state", owner_suite_id="startup_runtime"),
            TestPartitionItem("router_protocol_catalog", owner_suite_id="router_quality_gates"),
            TestPartitionItem("startup_flow", owner_suite_id="startup_runtime"),
            TestPartitionItem("self_interrogation", owner_suite_id="startup_runtime"),
            TestPartitionItem("payload_contracts", owner_suite_id="router_boundaries"),
            TestPartitionItem("controller_scheduler", owner_suite_id="controller_runtime"),
            TestPartitionItem("controller_repair", owner_suite_id="controller_runtime"),
            TestPartitionItem("action_factory", owner_suite_id="dispatch_gate_runtime"),
            TestPartitionItem("work_packets", owner_suite_id="packet_runtime"),
            TestPartitionItem("route_artifacts", owner_suite_id="route_runtime"),
            TestPartitionItem("events_repair", owner_suite_id="repair_runtime"),
            TestPartitionItem("lifecycle_requests", owner_suite_id="terminal_runtime"),
            TestPartitionItem("event_dispatcher", owner_suite_id="event_dispatch_runtime"),
            TestPartitionItem("system_cards", owner_suite_id="system_card_runtime"),
            TestPartitionItem("expected_waits", owner_suite_id="event_dispatch_runtime"),
            TestPartitionItem("route_frontier", owner_suite_id="route_runtime"),
            TestPartitionItem("terminal_ledger", owner_suite_id="terminal_runtime"),
            TestPartitionItem("install_prompt_assets", owner_suite_id="install_checks"),
        ),
        child_suites=(
            TestSuiteEvidence(
                "prompt_store_unit",
                command="python -m pytest tests/test_flowpilot_prompt_store.py -q",
                result_status=TEST_STATUS_PASSED,
                evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
                result_path="simulations/flowpilot_router_facade_split_results.json",
                owns_state=("prompt_store",),
                release_required=True,
            ),
            TestSuiteEvidence(
                "router_boundaries",
                command="python -m unittest tests.test_flowpilot_router_boundaries",
                result_status=TEST_STATUS_PASSED,
                evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
                result_path="simulations/flowpilot_router_facade_split_results.json",
                owns_state=("router_facade_prompt_delivery",),
                release_required=True,
            ),
            TestSuiteEvidence(
                "router_ack_return",
                command="python -m pytest tests/router_runtime/ack_return.py -q",
                result_status=TEST_STATUS_PASSED,
                evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
                result_path="simulations/flowpilot_router_facade_split_results.json",
                owns_state=("card_return_settlement",),
                release_required=True,
            ),
            TestSuiteEvidence(
                "event_contract",
                command="python simulations/run_flowpilot_event_contract_checks.py --json-out simulations/flowpilot_event_contract_results.json",
                result_status=TEST_STATUS_PASSED,
                evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
                result_path="simulations/flowpilot_router_facade_split_results.json",
                owns_state=("event_identity",),
                release_required=True,
            ),
            TestSuiteEvidence(
                "startup_daemon",
                command="python -m pytest tests/router_runtime/startup_daemon.py -q",
                result_status=TEST_STATUS_PASSED,
                evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
                result_path="simulations/flowpilot_router_facade_split_results.json",
                owns_state=("daemon_runtime",),
                release_required=True,
            ),
            TestSuiteEvidence(
                "startup_runtime",
                command="python -m unittest tests.test_flowpilot_router_startup_runtime tests.router_runtime.bootstrap_cli tests.router_runtime.startup_bootstrap tests.router_runtime.resume",
                result_status=TEST_STATUS_PASSED,
                evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
                result_path="simulations/flowpilot_router_facade_split_results.json",
                owns_state=("runtime_state", "startup_flow"),
                release_required=True,
            ),
            TestSuiteEvidence(
                "router_quality_gates",
                command="python -m unittest tests.router_runtime.quality_gates",
                result_status=TEST_STATUS_PASSED,
                evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
                result_path="simulations/flowpilot_router_facade_split_results.json",
                owns_state=("router_protocol_catalog",),
                release_required=True,
            ),
            TestSuiteEvidence(
                "controller_runtime",
                command="python -m unittest tests.router_runtime.controller tests.router_runtime.foreground_controller",
                result_status=TEST_STATUS_PASSED,
                evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
                result_path="simulations/flowpilot_router_facade_split_results.json",
                owns_state=("controller_scheduler",),
                release_required=True,
            ),
            TestSuiteEvidence(
                "dispatch_gate_runtime",
                command="python -m unittest tests.router_runtime.dispatch_gate",
                result_status=TEST_STATUS_PASSED,
                evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
                result_path="simulations/flowpilot_router_facade_split_results.json",
                owns_state=("action_factory",),
                release_required=True,
            ),
            TestSuiteEvidence(
                "system_card_runtime",
                command="python -m unittest tests.router_runtime.cards tests.router_runtime.ack_return",
                result_status=TEST_STATUS_PASSED,
                evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
                result_path="simulations/flowpilot_router_facade_split_results.json",
                owns_state=("system_cards",),
                release_required=True,
            ),
            TestSuiteEvidence(
                "packet_runtime",
                command="python -m unittest tests.router_runtime.packets tests.router_runtime.material_modeling tests.router_runtime.pm_role_work",
                result_status=TEST_STATUS_PASSED,
                evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
                result_path="simulations/flowpilot_router_facade_split_results.json",
                owns_state=("work_packets",),
                release_required=True,
            ),
            TestSuiteEvidence(
                "repair_runtime",
                command="python -m unittest tests.router_runtime.control_blockers",
                result_status=TEST_STATUS_PASSED,
                evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
                result_path="simulations/flowpilot_router_facade_split_results.json",
                owns_state=("events_repair",),
                release_required=True,
            ),
            TestSuiteEvidence(
                "event_dispatch_runtime",
                command="python simulations/run_flowpilot_event_contract_checks.py --json-out simulations/flowpilot_event_contract_results.json",
                result_status=TEST_STATUS_PASSED,
                evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
                result_path="simulations/flowpilot_router_facade_split_results.json",
                owns_state=("event_dispatcher",),
                release_required=True,
            ),
            TestSuiteEvidence(
                "route_runtime",
                command="python -m unittest tests.router_runtime.route_mutation_transactions tests.router_runtime.route_mutation_preconditions tests.router_runtime.route_mutation_topology tests.router_runtime.route_mutation_sibling_replacement",
                result_status=TEST_STATUS_PASSED,
                evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
                result_path="simulations/flowpilot_router_facade_split_results.json",
                owns_state=("route_frontier",),
                release_required=True,
            ),
            TestSuiteEvidence(
                "terminal_runtime",
                command="python -m unittest tests.router_runtime.terminal tests.router_runtime.closure",
                result_status=TEST_STATUS_PASSED,
                evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
                result_path="simulations/flowpilot_router_facade_split_results.json",
                owns_state=("terminal_ledger",),
                release_required=True,
            ),
            TestSuiteEvidence(
                "install_checks",
                command="python scripts/check_install.py --json",
                result_status=TEST_STATUS_PASSED,
                evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
                result_path="simulations/flowpilot_router_facade_split_results.json",
                owns_state=("install_prompt_assets",),
                release_required=True,
            ),
        ),
        target_split_derivation=TestTargetSplitDerivation(
            source_model_id="flowpilot_router_facade_prompt_store_split",
            source_model_path="simulations/flowpilot_router_facade_split_model.py",
            target_suite_ids=(
                "prompt_store_unit",
                "router_boundaries",
                "router_ack_return",
                "event_contract",
                "startup_daemon",
                "startup_runtime",
                "system_card_runtime",
                "router_quality_gates",
                "controller_runtime",
                "dispatch_gate_runtime",
                "packet_runtime",
                "repair_runtime",
                "event_dispatch_runtime",
                "route_runtime",
                "terminal_runtime",
                "install_checks",
            ),
            covered_partition_item_ids=(
                "prompt_store",
                "router_facade_prompt_delivery",
                "card_return_settlement",
                "event_identity",
                "daemon_runtime",
                "runtime_state",
                "router_protocol_catalog",
                "startup_flow",
                "self_interrogation",
                "payload_contracts",
                "controller_repair",
                "action_factory",
                "system_cards",
                "expected_waits",
                "route_artifacts",
                "lifecycle_requests",
                "controller_scheduler",
                "work_packets",
                "events_repair",
                "event_dispatcher",
                "route_frontier",
                "terminal_ledger",
                "install_prompt_assets",
            ),
            state_owner_fields=(
                "prompt_store",
                "router_facade_prompt_delivery",
                "card_return_settlement",
                "event_identity",
                "daemon_runtime",
                "runtime_state",
                "router_protocol_catalog",
                "startup_flow",
                "self_interrogation",
                "payload_contracts",
                "controller_repair",
                "action_factory",
                "system_cards",
                "expected_waits",
                "route_artifacts",
                "lifecycle_requests",
                "controller_scheduler",
                "work_packets",
                "events_repair",
                "event_dispatcher",
                "route_frontier",
                "terminal_ledger",
                "install_prompt_assets",
            ),
            rationale=(
                "Router facade release confidence is derived from focused child "
                "suites that cover prompt storage, prompt delivery, ACK returns, "
                "event identity, runtime/startup, controller, packets, repair, "
                "route, terminal, and install asset boundaries."
            ),
        ),
    )


def valid_split_evidence() -> RouterFacadeSplitEvidence:
    return RouterFacadeSplitEvidence(prompt_assets=prompt_assets_from_manifest())


def review_split_evidence(evidence: RouterFacadeSplitEvidence) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    if evidence.child_module_count > evidence.max_child_module_count:
        findings.append(
            {
                "code": "micro_module_explosion",
                "severity": "blocker",
                "message": "router split has too many child modules for the current maintenance wave",
            }
        )
    if evidence.micro_module_count > evidence.max_micro_module_count:
        findings.append(
            {
                "code": "one_function_file_split",
                "severity": "blocker",
                "message": "split creates one-function files instead of cohesive behavior owners",
            }
        )
    missing_coarse_owners = sorted(set(evidence.required_coarse_owner_ids) - set(evidence.coarse_owner_ids))
    if missing_coarse_owners:
        findings.append(
            {
                "code": "missing_coarse_phase_owner",
                "severity": "blocker",
                "missing_owner_ids": missing_coarse_owners,
                "message": "coarse router split is missing required phase owner modules",
            }
        )
    for asset in evidence.prompt_assets:
        if asset.inline_fallback_allowed:
            findings.append(
                {
                    "code": "unsafe_inline_prompt_fallback",
                    "severity": "blocker",
                    "prompt_id": asset.prompt_id,
                    "message": "prompt rendering allows stale inline fallback text",
                }
            )
        if not asset.included_in_install_checks:
            findings.append(
                {
                    "code": "prompt_asset_not_installed",
                    "severity": "blocker",
                    "prompt_id": asset.prompt_id,
                    "message": "prompt asset is not included in install checks",
                }
            )
        if not asset.template_variables_declared:
            findings.append(
                {
                    "code": "undeclared_prompt_template_variables",
                    "severity": "blocker",
                    "prompt_id": asset.prompt_id,
                    "message": "prompt template variables are not manifest-declared",
                }
            )
        path = ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit" / asset.path
        if not path.exists():
            findings.append(
                {
                    "code": "missing_prompt_asset",
                    "severity": "blocker",
                    "prompt_id": asset.prompt_id,
                    "path": asset.path,
                    "message": "prompt manifest references a missing asset",
                }
            )
        elif _sha256_text(path) != asset.sha256:
            findings.append(
                {
                    "code": "stale_prompt_hash",
                    "severity": "blocker",
                    "prompt_id": asset.prompt_id,
                    "path": asset.path,
                    "message": "prompt manifest hash does not match the prompt asset",
                }
            )
    return {
        "ok": not findings,
        "findings": findings,
        "asset_count": len(evidence.prompt_assets),
        "child_module_count": evidence.child_module_count,
        "coarse_owner_count": len(evidence.coarse_owner_ids),
        "micro_module_count": evidence.micro_module_count,
    }


def split_hazard_evidence(name: str) -> RouterFacadeSplitEvidence:
    evidence = valid_split_evidence()
    if name == "micro_module_explosion":
        return replace(evidence, child_module_count=940)
    if name == "one_function_file_split":
        return replace(evidence, micro_module_count=940)
    if name == "missing_coarse_phase_owner":
        return replace(evidence, coarse_owner_ids=evidence.coarse_owner_ids[:-1])
    if name == "missing_prompt_asset":
        assets = evidence.prompt_assets + (
            PromptAssetEvidence("known_bad.missing", "prompts/missing.md", "bad"),
        )
        return replace(evidence, prompt_assets=assets)
    if name == "stale_prompt_hash":
        first = replace(evidence.prompt_assets[0], sha256="bad")
        return replace(evidence, prompt_assets=(first, *evidence.prompt_assets[1:]))
    if name == "unsafe_inline_prompt_fallback":
        first = replace(evidence.prompt_assets[0], inline_fallback_allowed=True)
        return replace(evidence, prompt_assets=(first, *evidence.prompt_assets[1:]))
    if name == "prompt_asset_not_installed":
        first = replace(evidence.prompt_assets[0], included_in_install_checks=False)
        return replace(evidence, prompt_assets=(first, *evidence.prompt_assets[1:]))
    if name == "undeclared_prompt_template_variables":
        first = replace(evidence.prompt_assets[0], template_variables_declared=False)
        return replace(evidence, prompt_assets=(first, *evidence.prompt_assets[1:]))
    raise ValueError(f"unknown split hazard: {name}")


SPLIT_HAZARDS = (
    "micro_module_explosion",
    "one_function_file_split",
    "missing_coarse_phase_owner",
    "missing_prompt_asset",
    "stale_prompt_hash",
    "unsafe_inline_prompt_fallback",
    "prompt_asset_not_installed",
    "undeclared_prompt_template_variables",
)
