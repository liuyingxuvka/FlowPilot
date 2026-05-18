"""FlowGuard model for the FlowPilot router facade and PromptStore split."""

from __future__ import annotations

import ast
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
ROUTER_PATH = ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_router.py"
ROUTER_EXPORTS_PATH = ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_router_facade_exports.py"
ROUTER_EXPORT_MANIFEST_PATH = (
    ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_router_facade_export_manifest.py"
)

ROUTER_PUBLIC_API_ALLOWLIST = (
    "main",
    "parse_args",
    "next_action",
    "apply_action",
    "apply_controller_action",
    "record_external_event",
    "record_controller_action_receipt",
    "run_until_wait",
    "run_router_daemon",
    "stop_router_daemon",
    "foreground_controller_standby",
    "controller_patrol_timer",
    "reconcile_current_run",
    "validate_artifact",
    "write_role_output_envelope",
    "RouterError",
    "RouterLedgerCorruptionError",
    "RouterLedgerWriteInProgress",
)


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
    child_module_count: int = 102
    max_child_module_count: int = 123
    micro_module_count: int = 0
    max_micro_module_count: int = 2
    facade_line_count: int = 448
    max_facade_line_count: int = 800
    facade_top_level_function_count: int = 0
    max_facade_top_level_function_count: int = 0
    obsolete_compat_wrapper_count: int = 0
    max_obsolete_compat_wrapper_count: int = 0
    owner_export_registry_declared: bool = True
    public_api_whitelist: tuple[str, ...] = ROUTER_PUBLIC_API_ALLOWLIST
    required_public_api_names: tuple[str, ...] = ROUTER_PUBLIC_API_ALLOWLIST
    required_coarse_owner_ids: tuple[str, ...] = (
        "runtime_state",
        "startup_flow",
        "startup_bootloader",
        "startup_intake",
        "startup_display",
        "startup_role_recovery",
        "startup_closure",
        "startup_fact_boundary",
        "startup_support",
        "controller_scheduler",
        "controller_runtime",
        "controller_repair",
        "action_factory",
        "payload_contracts",
        "lifecycle_requests",
        "lifecycle_support",
        "control_transactions",
        "route_artifacts",
        "route_completion_support",
        "system_cards",
        "expected_waits",
        "self_interrogation",
        "proof_validation",
        "model_gate_state",
        "child_skill_capability",
        "role_output_bridge",
        "pm_role_followup",
        "internal_actions",
        "artifact_validation",
        "cli",
        "facade_exports",
        "work_packets",
        "events_repair",
        "event_dispatcher",
        "route_frontier",
        "terminal_ledger",
    )
    coarse_owner_ids: tuple[str, ...] = (
        "runtime_state",
        "startup_flow",
        "startup_bootloader",
        "startup_intake",
        "startup_display",
        "startup_role_recovery",
        "startup_closure",
        "startup_fact_boundary",
        "startup_support",
        "controller_scheduler",
        "controller_runtime",
        "controller_repair",
        "action_factory",
        "payload_contracts",
        "lifecycle_requests",
        "lifecycle_support",
        "control_transactions",
        "route_artifacts",
        "route_completion_support",
        "system_cards",
        "expected_waits",
        "self_interrogation",
        "proof_validation",
        "model_gate_state",
        "child_skill_capability",
        "role_output_bridge",
        "pm_role_followup",
        "internal_actions",
        "artifact_validation",
        "cli",
        "facade_exports",
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
        "flowpilot_router_public_api",
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
        "public_api_allowlist",
        item_type="public_entrypoint",
        owner_module_id="router_facade",
        ownership="parent",
        public_surface=True,
    ),
    StructurePartitionItem(
        "owner_export_registry",
        item_type="config",
        owner_module_id="facade_export_manifest",
        old_path="flowpilot_router hand-written private compatibility wrappers",
        new_path="flowpilot_router_facade_export_manifest",
    ),
    StructurePartitionItem(
        "owner_export_installer",
        item_type="function_cluster",
        owner_module_id="facade_exports",
        old_path="flowpilot_router hand-written private compatibility wrappers",
        new_path="flowpilot_router_facade_exports",
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
        "packet_identity_prompt",
        item_type="prompt",
        owner_module_id="prompt_assets",
        old_path="packet_runtime_contracts inline packet identity text",
        new_path="runtime_kit/prompts/packets",
    ),
    StructurePartitionItem(
        "packet_result_identity_prompt",
        item_type="prompt",
        owner_module_id="prompt_assets",
        old_path="packet_runtime_contracts inline result identity text",
        new_path="runtime_kit/prompts/packets",
    ),
    StructurePartitionItem(
        "packet_output_contract_prompt",
        item_type="prompt",
        owner_module_id="prompt_assets",
        old_path="packet_runtime_contracts inline output contract text",
        new_path="runtime_kit/prompts/packets",
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
        "startup_bootloader",
        item_type="function_cluster",
        owner_module_id="startup_bootloader",
        old_path="flowpilot_router_startup_flow bootloader action bodies",
        new_path="flowpilot_router_startup_bootloader",
    ),
    StructurePartitionItem(
        "startup_intake",
        item_type="function_cluster",
        owner_module_id="startup_intake",
        old_path="flowpilot_router_startup_flow intake and answer bodies",
        new_path="flowpilot_router_startup_intake",
    ),
    StructurePartitionItem(
        "startup_display",
        item_type="function_cluster",
        owner_module_id="startup_display",
        old_path="flowpilot_router_startup_flow display and route-sign bodies",
        new_path="flowpilot_router_startup_display",
    ),
    StructurePartitionItem(
        "startup_role_recovery",
        item_type="function_cluster",
        owner_module_id="startup_role_recovery",
        old_path="flowpilot_router_startup_flow resume and role-recovery bodies",
        new_path="flowpilot_router_startup_role_recovery",
    ),
    StructurePartitionItem(
        "startup_closure",
        item_type="function_cluster",
        owner_module_id="startup_closure",
        old_path="flowpilot_router_startup_flow startup closure reconciliation bodies",
        new_path="flowpilot_router_startup_closure",
    ),
    StructurePartitionItem(
        "startup_fact_boundary",
        item_type="function_cluster",
        owner_module_id="startup_fact_boundary",
        old_path="flowpilot_router_startup_flow startup fact and boundary audit bodies",
        new_path="flowpilot_router_startup_fact_boundary",
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
        behavior_contracts=("owner export installation", "no hand-written wrapper bodies in router skeleton"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "facade_export_manifest",
        path="skills/flowpilot/assets/flowpilot_router_facade_export_manifest.py",
        owns_config=("owner_export_registry",),
        behavior_contracts=("transitional owner export registry", "public export allowlist authority"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "facade_export_manifest_actions",
        path="skills/flowpilot/assets/flowpilot_router_facade_export_manifest_actions.py",
        owns_config=("owner_export_manifest_actions",),
        behavior_contracts=("action-domain owner export registry shard",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "facade_export_manifest_controller",
        path="skills/flowpilot/assets/flowpilot_router_facade_export_manifest_controller.py",
        owns_config=("owner_export_manifest_controller",),
        behavior_contracts=("controller-domain owner export registry shard",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "facade_export_manifest_route",
        path="skills/flowpilot/assets/flowpilot_router_facade_export_manifest_route.py",
        owns_config=("owner_export_manifest_route",),
        behavior_contracts=("route-domain owner export registry shard",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "facade_export_manifest_startup",
        path="skills/flowpilot/assets/flowpilot_router_facade_export_manifest_startup.py",
        owns_config=("owner_export_manifest_startup",),
        behavior_contracts=("startup-domain owner export registry shard",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "facade_export_manifest_terminal_work",
        path="skills/flowpilot/assets/flowpilot_router_facade_export_manifest_terminal_work.py",
        owns_config=("owner_export_manifest_terminal_work",),
        behavior_contracts=("terminal/work-packet owner export registry shard",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "cli",
        path="skills/flowpilot/assets/flowpilot_router_cli.py",
        owns_functions=("parse_args", "main"),
        dependencies=("router_facade", "controller_runtime"),
        behavior_contracts=("CLI command surface", "JSON error envelope", "runtime writer settlement"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "controller_runtime",
        path="skills/flowpilot/assets/flowpilot_router_controller_runtime.py",
        owns_functions=("next_action", "compute_controller_action", "apply_action", "apply_controller_action", "run_until_wait", "record_external_event"),
        owns_state=("controller_runtime_loop",),
        dependencies=("action_factory", "action_handlers", "action_providers", "event_dispatcher", "router_facade"),
        behavior_contracts=("next action loop", "controller apply loop", "external event entrypoint", "safe run-until-wait folding"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "artifact_validation",
        path="skills/flowpilot/assets/flowpilot_router_artifact_validation.py",
        owns_functions=("validate_artifact", "_validate_hash_if_present", "_validate_role_output_hash_if_present"),
        dependencies=("packet_runtime", "role_output_bridge", "router_facade"),
        behavior_contracts=("artifact validation CLI/API", "hash validation", "role output envelope validation"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "control_transactions",
        path="skills/flowpilot/assets/flowpilot_router_control_transactions.py",
        owns_functions=("_control_transaction_registry_issues", "_validate_control_transaction_requirements"),
        owns_config=("control_transaction_registry",),
        behavior_contracts=("control transaction registry validation", "output contract coverage"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "internal_actions",
        path="skills/flowpilot/assets/flowpilot_router_internal_actions.py",
        owns_functions=("_consume_router_internal_mechanical_action", "_action_is_router_internal_mechanical"),
        owns_state=("router_internal_mechanical_events",),
        dependencies=("startup_flow", "router_facade"),
        behavior_contracts=("internal mechanical action guard", "manifest/ledger check folding", "mechanical audit write"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "role_output_bridge",
        path="skills/flowpilot/assets/flowpilot_router_role_output_bridge.py",
        owns_functions=("write_role_output_envelope", "_try_reconcile_startup_fact_role_output_ledger"),
        owns_state=("role_output_bridge_records",),
        dependencies=("role_output_runtime", "system_cards", "router_facade"),
        behavior_contracts=("role output envelope bridge", "startup fact role-output reconciliation", "prompt delivery context repair"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "startup_support",
        path="skills/flowpilot/assets/flowpilot_router_startup_support.py",
        owns_functions=("_ensure_startup_run_state", "load_manifest_from_run", "manifest_card"),
        owns_state=("startup_run_state_creation",),
        dependencies=("runtime_state", "prompt_store", "router_facade"),
        behavior_contracts=("startup run state creation", "prompt manifest lookup", "startup event digest helpers"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "lifecycle_support",
        path="skills/flowpilot/assets/flowpilot_router_lifecycle_support.py",
        owns_functions=("_write_host_heartbeat_binding", "_reset_resume_cycle_for_wakeup"),
        owns_state=("lifecycle_support_records",),
        dependencies=("lifecycle_requests", "router_facade"),
        behavior_contracts=("heartbeat binding write", "resume cycle reset", "lifecycle record paths"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "child_skill_capability",
        path="skills/flowpilot/assets/flowpilot_router_child_skill_capability.py",
        owns_functions=("_approve_child_skill_manifest_for_route", "_sync_capability_evidence"),
        owns_state=("child_skill_capability_evidence",),
        dependencies=("route_artifacts", "router_facade"),
        behavior_contracts=("child-skill manifest approval", "capability evidence sync"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "route_completion_support",
        path="skills/flowpilot/assets/flowpilot_router_route_completion_support.py",
        owns_functions=("_active_node_completion_write_missing", "_node_completion_event_advanced_to_next_node"),
        owns_state=("route_completion_support",),
        dependencies=("route_frontier", "router_facade"),
        behavior_contracts=("active node completion helper paths", "resume completion predicates"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "model_gate_state",
        path="skills/flowpilot/assets/flowpilot_router_model_gate_state.py",
        owns_functions=("_sync_model_gate_alias_flags", "_require_single_active_model_miss_review_block"),
        owns_state=("model_gate_alias_flags",),
        behavior_contracts=("model gate alias flag sync", "model-miss block uniqueness"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "pm_role_followup",
        path="skills/flowpilot/assets/flowpilot_router_pm_role_followup.py",
        owns_functions=("_validate_pm_role_work_request_against_followup", "_pm_role_work_channel_open"),
        dependencies=("work_packets", "events_repair", "router_facade"),
        behavior_contracts=("PM role-work follow-up validation", "model-miss follow-up channel check"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "proof_validation",
        path="skills/flowpilot/assets/flowpilot_router_proof_validation.py",
        owns_functions=("_validate_router_owned_check_proof",),
        dependencies=("self_interrogation", "packet_runtime", "router_facade"),
        behavior_contracts=("router-owned proof validation", "non-self-attested evidence requirement"),
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
        owns_functions=(),
        owns_state=(),
        dependencies=("startup_bootloader", "startup_intake", "startup_display", "startup_role_recovery", "startup_closure", "startup_fact_boundary"),
        behavior_contracts=("startup owner-module binding", "startup group ownership boundary"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "startup_bootloader",
        path="skills/flowpilot/assets/flowpilot_router_startup_bootloader.py",
        owns_functions=("compute_bootloader_action", "apply_bootloader_action", "_next_bootloader_open_action"),
        owns_state=("startup_bootloader",),
        dependencies=("runtime_state", "payload_contracts", "router_facade"),
        behavior_contracts=("bootloader action ordering", "daemon-control bootstrap", "startup question stop boundary"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "startup_intake",
        path="skills/flowpilot/assets/flowpilot_router_startup_intake.py",
        owns_functions=("_validate_startup_answer_payload", "_materialize_startup_intake_answers", "_ensure_startup_intake_ui"),
        owns_state=("startup_answers", "startup_intake_ui"),
        dependencies=("startup_support", "router_facade"),
        behavior_contracts=("startup answer validation", "intake UI materialization", "deterministic bootstrap seed"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "startup_display",
        path="skills/flowpilot/assets/flowpilot_router_startup_display.py",
        owns_functions=("_next_startup_display_action", "_write_startup_display_plan", "_ensure_route_sign_display_sync"),
        owns_state=("startup_display", "route_sign_display"),
        dependencies=("startup_support", "payload_contracts", "router_facade"),
        behavior_contracts=("startup display plan", "user dialogue projection", "route sign synchronization"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "startup_role_recovery",
        path="skills/flowpilot/assets/flowpilot_router_startup_role_recovery.py",
        owns_functions=("_next_resume_action", "_next_role_recovery_action", "_record_role_spawn_intent"),
        owns_state=("resume_role_recovery", "role_spawn_intents", "continuation_bindings"),
        dependencies=("controller_scheduler", "runtime_state", "router_facade"),
        behavior_contracts=("resume action selection", "role recovery persistence", "continuation binding rehydration"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "startup_closure",
        path="skills/flowpilot/assets/flowpilot_router_startup_closure.py",
        owns_functions=("_startup_closure_reconciliation_status", "_next_startup_closure_action"),
        owns_state=("startup_closure_reconciliation", "heartbeat_host_binding"),
        dependencies=("lifecycle_support", "terminal_ledger", "router_facade"),
        behavior_contracts=("startup closure reconciliation", "heartbeat binding readiness", "dirty closure invalidation"),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "startup_fact_boundary",
        path="skills/flowpilot/assets/flowpilot_router_startup_fact_boundary.py",
        owns_functions=("_next_startup_fact_boundary_action", "_next_startup_mechanical_audit_action", "_write_startup_fact_report"),
        owns_state=("startup_fact_boundary", "startup_mechanical_audit", "controller_boundary_confirmation"),
        dependencies=("controller_boundary", "role_output_bridge", "router_facade"),
        behavior_contracts=("startup fact audit", "controller boundary confirmation", "mechanical audit repair actions"),
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
        "controller_scheduler_receipt_writes",
        path="skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_writes.py",
        owns_functions=("_write_controller_action_entry", "_write_controller_receipt"),
        owns_side_effects=("controller_action_receipt_write",),
        dependencies=("controller_scheduler", "router_facade"),
        behavior_contracts=("controller action and receipt write helpers",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "controller_scheduler_receipt_effects",
        path="skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_effects.py",
        owns_functions=("_apply_stateful_receipt_postcondition", "_apply_done_controller_receipt_effects"),
        dependencies=("controller_scheduler_receipt_writes", "router_facade"),
        behavior_contracts=("Controller receipt postcondition effects",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "controller_scheduler_receipt_pending",
        path="skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_pending.py",
        owns_functions=("_reconcile_pending_controller_action_receipt", "_clear_pending_after_reconciled_controller_receipt"),
        dependencies=("controller_scheduler_receipt_effects", "router_facade"),
        behavior_contracts=("pending Controller action receipt reconciliation",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "controller_scheduler_receipt_scheduled",
        path="skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_scheduled.py",
        owns_functions=("_reconcile_scheduled_controller_action_receipts", "_backfill_scheduler_row_from_reconciled_controller_action"),
        dependencies=("controller_scheduler_receipt_pending", "router_facade"),
        behavior_contracts=("scheduled Controller action reconciliation and scheduler backfill",),
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
        "action_factory_reconciliation",
        path="skills/flowpilot/assets/flowpilot_router_action_factory_reconciliation.py",
        owns_functions=("_current_scope_pre_review_reconciliation_action", "_apply_formal_work_packet_ack_preflight"),
        dependencies=("action_factory", "router_facade"),
        behavior_contracts=("scope reconciliation waits and formal work packet ACK preflight",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "action_factory_dispatch",
        path="skills/flowpilot/assets/flowpilot_router_action_factory_dispatch.py",
        owns_functions=("_apply_dispatch_recipient_gate", "_dispatch_gate_wait_action"),
        dependencies=("action_factory_reconciliation", "router_facade"),
        behavior_contracts=("dispatch recipient gate and blocker helpers",),
        behavior_parity_tier=EVIDENCE_CONFORMANCE_GREEN,
        release_required=True,
    ),
    ModuleStructureEvidence(
        "action_factory_envelope",
        path="skills/flowpilot/assets/flowpilot_router_action_factory_envelope.py",
        owns_functions=("make_action", "append_history", "_controller_user_reporting_policy"),
        dependencies=("action_factory_dispatch", "router_facade"),
        behavior_contracts=("action envelope and Controller user-reporting policy",),
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
        "pm_role_work_gates",
        path="skills/flowpilot/assets/flowpilot_router_work_packets_pm_role_gates.py",
        owns_functions=("_pm_role_work_gate_mappings_for_decision", "_apply_pm_role_work_gate_mappings"),
        dependencies=("work_packets", "router_facade"),
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
        owns_state=("pm_role_work_request_index", "officer_request_lifecycle"),
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
)


ROUTER_FACADE_TARGET_RATIONALES = {
    "router_facade": "Keeps the executable router file as a small public skeleton with no behavior bodies.",
    "facade_exports": "Owns the registry resolver and installer for transitional internal lookups.",
    "facade_export_manifest": "Owns the explicit transitional owner-export registry that replaces hand-written wrappers.",
    "facade_export_manifest_actions": "Owns action-domain owner-export registry rows.",
    "facade_export_manifest_controller": "Owns controller-domain owner-export registry rows.",
    "facade_export_manifest_route": "Owns route-domain owner-export registry rows.",
    "facade_export_manifest_startup": "Owns startup-domain owner-export registry rows.",
    "facade_export_manifest_terminal_work": "Owns terminal and work-packet owner-export registry rows.",
    "cli": "Owns command parsing and CLI JSON/error envelope behavior.",
    "controller_runtime": "Owns the high-level next/apply/event controller loop entrypoints.",
    "artifact_validation": "Owns artifact validation and hash checks exposed through the CLI/API.",
    "control_transactions": "Owns control transaction registry validation and contract coverage.",
    "internal_actions": "Owns Router-internal mechanical action guards and consumption.",
    "role_output_bridge": "Owns role-output envelope bridge behavior and startup fact reconciliation.",
    "startup_support": "Owns startup run-state support and prompt manifest/card lookup helpers.",
    "lifecycle_support": "Owns heartbeat binding and lifecycle support helpers moved out of the skeleton.",
    "child_skill_capability": "Owns child-skill manifest approval and capability evidence sync.",
    "route_completion_support": "Owns active-node completion helper paths and resume predicates.",
    "model_gate_state": "Owns model gate alias flag sync and model-miss block checks.",
    "pm_role_followup": "Owns PM role-work follow-up validation for model-miss repair flows.",
    "proof_validation": "Owns router-owned proof validation.",
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
    "startup_flow": "Groups startup owner-module binding without retaining action bodies.",
    "startup_bootloader": "Owns bootloader action ordering and daemon-control bootstrap behavior.",
    "startup_intake": "Owns startup answer validation, intake UI materialization, and bootstrap seed capture.",
    "startup_display": "Owns startup display plans, user-dialogue projection, and route-sign synchronization.",
    "startup_role_recovery": "Owns resume, role recovery, role spawn normalization, and continuation binding rehydration.",
    "startup_closure": "Owns startup closure reconciliation and heartbeat binding readiness checks.",
    "startup_fact_boundary": "Owns startup fact audit, controller-boundary confirmation, and mechanical-audit repair actions.",
    "controller_scheduler": "Owns controller scheduling, receipt reconciliation, standby, and patrol behavior.",
    "controller_scheduler_receipt_writes": "Owns Controller action and receipt write helpers.",
    "controller_scheduler_receipt_effects": "Owns Controller receipt postcondition effect helpers.",
    "controller_scheduler_receipt_pending": "Owns pending Controller action receipt reconciliation helpers.",
    "controller_scheduler_receipt_scheduled": "Owns scheduled Controller action reconciliation and scheduler backfill helpers.",
    "controller_repair": "Owns controller deliverable repair, postcondition reclaim, and mail-delivery folding.",
    "action_factory": "Owns action envelope construction and dispatch-recipient gate policy.",
    "action_factory_reconciliation": "Owns scope reconciliation wait and ACK preflight helpers.",
    "action_factory_dispatch": "Owns dispatch-recipient gate and blocker helpers.",
    "action_factory_envelope": "Owns final action envelope construction and Controller user-reporting policy.",
    "work_packets": "Owns material, research, current-node, and PM role-work packet flow.",
    "pm_role_work_gates": "Owns PM role-work gate mapping and targeted result contract helpers.",
    "pm_role_work_writes": "Owns PM role-work request, result, and disposition writes.",
    "pm_role_work_lifecycle": "Owns PM role-work request indexes and officer lifecycle records.",
    "pm_role_work_actions": "Owns PM role-work next-action selection and result reconciliation.",
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
    "terminal_ledger_summary": "Owns terminal summary validation and writes.",
    "terminal_ledger_traceability": "Owns final ledger traceability and source-of-truth entries.",
    "terminal_ledger_closure": "Owns terminal backward replay and closure suite writes.",
    "terminal_ledger_recovery": "Owns terminal status recovery and legacy packet repair.",
}


ROUTER_FACADE_FUNCTION_BLOCK_MAP = (
    ("public_api_allowlist", "router_facade"),
    ("owner_export_registry", "facade_export_manifest"),
    ("owner_export_manifest_actions", "facade_export_manifest_actions"),
    ("owner_export_manifest_controller", "facade_export_manifest_controller"),
    ("owner_export_manifest_route", "facade_export_manifest_route"),
    ("owner_export_manifest_startup", "facade_export_manifest_startup"),
    ("owner_export_manifest_terminal_work", "facade_export_manifest_terminal_work"),
    ("owner_export_installer", "facade_exports"),
    ("parse_args", "cli"),
    ("main", "cli"),
    ("next_action", "controller_runtime"),
    ("apply_action", "controller_runtime"),
    ("apply_controller_action", "controller_runtime"),
    ("record_external_event", "controller_runtime"),
    ("run_until_wait", "controller_runtime"),
    ("validate_artifact", "artifact_validation"),
    ("control_transaction_registry", "control_transactions"),
    ("router_internal_mechanical_actions", "internal_actions"),
    ("role_output_bridge", "role_output_bridge"),
    ("startup_support", "startup_support"),
    ("lifecycle_support", "lifecycle_support"),
    ("child_skill_capability", "child_skill_capability"),
    ("route_completion_support", "route_completion_support"),
    ("model_gate_state", "model_gate_state"),
    ("pm_role_followup", "pm_role_followup"),
    ("proof_validation", "proof_validation"),
    ("prompt_manifest_loading", "prompt_store"),
    ("card_post_ack_policy", "prompt_delivery"),
    ("controller_table_prompt", "prompt_delivery"),
    ("startup_heartbeat_prompt", "prompt_delivery"),
    ("packet_identity_prompt", "prompt_assets"),
    ("packet_result_identity_prompt", "prompt_assets"),
    ("packet_output_contract_prompt", "prompt_assets"),
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
    ("startup_flow_group", "startup_flow"),
    ("startup_bootloader", "startup_bootloader"),
    ("startup_intake", "startup_intake"),
    ("startup_display", "startup_display"),
    ("startup_role_recovery", "startup_role_recovery"),
    ("startup_closure", "startup_closure"),
    ("startup_fact_boundary", "startup_fact_boundary"),
    ("self_interrogation", "self_interrogation"),
    ("payload_contracts", "payload_contracts"),
    ("controller_scheduler", "controller_scheduler"),
    ("controller_receipt_writes", "controller_scheduler_receipt_writes"),
    ("controller_receipt_effects", "controller_scheduler_receipt_effects"),
    ("controller_receipt_pending", "controller_scheduler_receipt_pending"),
    ("controller_receipt_scheduled", "controller_scheduler_receipt_scheduled"),
    ("controller_repair", "controller_repair"),
    ("action_factory", "action_factory"),
    ("action_factory_reconciliation", "action_factory_reconciliation"),
    ("action_factory_dispatch", "action_factory_dispatch"),
    ("action_factory_envelope", "action_factory_envelope"),
    ("work_packets", "work_packets"),
    ("pm_role_work_gates", "pm_role_work_gates"),
    ("pm_role_work_writes", "pm_role_work_writes"),
    ("pm_role_work_lifecycle", "pm_role_work_lifecycle"),
    ("pm_role_work_actions", "pm_role_work_actions"),
    ("route_artifacts", "route_artifacts"),
    ("events_repair", "events_repair"),
    ("lifecycle_requests", "lifecycle_requests"),
    ("event_dispatcher", "event_dispatcher"),
    ("system_cards", "system_cards"),
    ("expected_waits", "expected_waits"),
    ("route_frontier", "route_frontier"),
    ("terminal_ledger", "terminal_ledger"),
    ("terminal_ledger_summary", "terminal_ledger_summary"),
    ("terminal_ledger_traceability", "terminal_ledger_traceability"),
    ("terminal_ledger_closure", "terminal_ledger_closure"),
    ("terminal_ledger_recovery", "terminal_ledger_recovery"),
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
                    ("flowpilot_router_public_api", "flowpilot_router_cli")
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
            ("flowpilot_router_public_api", "router_facade"),
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
            "FlowGuard target structure keeps the router file as a public "
            "skeleton with an explicit API allowlist and assigns prompt, "
            "runtime, startup, packet, repair, route, and terminal ownership "
            "to child modules."
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
            TestPartitionItem("public_api_allowlist", owner_suite_id="router_boundaries"),
            TestPartitionItem("owner_export_registry", owner_suite_id="router_boundaries"),
            TestPartitionItem("owner_export_manifest", owner_suite_id="install_checks"),
            TestPartitionItem("owner_export_manifest_actions", owner_suite_id="install_checks"),
            TestPartitionItem("owner_export_manifest_controller", owner_suite_id="install_checks"),
            TestPartitionItem("owner_export_manifest_route", owner_suite_id="install_checks"),
            TestPartitionItem("owner_export_manifest_startup", owner_suite_id="install_checks"),
            TestPartitionItem("owner_export_manifest_terminal_work", owner_suite_id="install_checks"),
            TestPartitionItem("packet_prompt_assets", owner_suite_id="install_checks"),
            TestPartitionItem("cli", owner_suite_id="startup_runtime"),
            TestPartitionItem("controller_runtime", owner_suite_id="controller_runtime"),
            TestPartitionItem("artifact_validation", owner_suite_id="router_boundaries"),
            TestPartitionItem("control_transactions", owner_suite_id="install_checks"),
            TestPartitionItem("internal_actions", owner_suite_id="controller_runtime"),
            TestPartitionItem("role_output_bridge", owner_suite_id="router_boundaries"),
            TestPartitionItem("startup_support", owner_suite_id="startup_runtime"),
            TestPartitionItem("lifecycle_support", owner_suite_id="event_dispatch_runtime"),
            TestPartitionItem("child_skill_capability", owner_suite_id="route_runtime"),
            TestPartitionItem("route_completion_support", owner_suite_id="route_runtime"),
            TestPartitionItem("model_gate_state", owner_suite_id="event_dispatch_runtime"),
            TestPartitionItem("pm_role_followup", owner_suite_id="packet_runtime"),
            TestPartitionItem("proof_validation", owner_suite_id="router_boundaries"),
            TestPartitionItem("card_return_settlement", owner_suite_id="router_ack_return"),
            TestPartitionItem("event_identity", owner_suite_id="event_contract"),
            TestPartitionItem("daemon_runtime", owner_suite_id="startup_daemon"),
            TestPartitionItem("runtime_state", owner_suite_id="startup_runtime"),
            TestPartitionItem("router_protocol_catalog", owner_suite_id="router_quality_gates"),
            TestPartitionItem("startup_flow", owner_suite_id="startup_runtime"),
            TestPartitionItem("startup_bootloader", owner_suite_id="startup_runtime"),
            TestPartitionItem("startup_intake", owner_suite_id="startup_runtime"),
            TestPartitionItem("startup_display", owner_suite_id="startup_runtime"),
            TestPartitionItem("startup_role_recovery", owner_suite_id="startup_runtime"),
            TestPartitionItem("startup_closure", owner_suite_id="startup_runtime"),
            TestPartitionItem("startup_fact_boundary", owner_suite_id="startup_runtime"),
            TestPartitionItem("self_interrogation", owner_suite_id="startup_runtime"),
            TestPartitionItem("payload_contracts", owner_suite_id="router_boundaries"),
            TestPartitionItem("controller_scheduler", owner_suite_id="controller_runtime"),
            TestPartitionItem("controller_scheduler_receipt_writes", owner_suite_id="controller_runtime"),
            TestPartitionItem("controller_scheduler_receipt_effects", owner_suite_id="controller_runtime"),
            TestPartitionItem("controller_scheduler_receipt_pending", owner_suite_id="controller_runtime"),
            TestPartitionItem("controller_scheduler_receipt_scheduled", owner_suite_id="controller_runtime"),
            TestPartitionItem("controller_repair", owner_suite_id="controller_runtime"),
            TestPartitionItem("action_factory", owner_suite_id="dispatch_gate_runtime"),
            TestPartitionItem("action_factory_reconciliation", owner_suite_id="dispatch_gate_runtime"),
            TestPartitionItem("action_factory_dispatch", owner_suite_id="dispatch_gate_runtime"),
            TestPartitionItem("action_factory_envelope", owner_suite_id="dispatch_gate_runtime"),
            TestPartitionItem("work_packets", owner_suite_id="packet_runtime"),
            TestPartitionItem("pm_role_work_gates", owner_suite_id="packet_runtime"),
            TestPartitionItem("pm_role_work_writes", owner_suite_id="packet_runtime"),
            TestPartitionItem("pm_role_work_lifecycle", owner_suite_id="packet_runtime"),
            TestPartitionItem("pm_role_work_actions", owner_suite_id="packet_runtime"),
            TestPartitionItem("route_artifacts", owner_suite_id="route_runtime"),
            TestPartitionItem("events_repair", owner_suite_id="repair_runtime"),
            TestPartitionItem("lifecycle_requests", owner_suite_id="terminal_runtime"),
            TestPartitionItem("event_dispatcher", owner_suite_id="event_dispatch_runtime"),
            TestPartitionItem("system_cards", owner_suite_id="system_card_runtime"),
            TestPartitionItem("expected_waits", owner_suite_id="event_dispatch_runtime"),
            TestPartitionItem("route_frontier", owner_suite_id="route_runtime"),
            TestPartitionItem("terminal_ledger", owner_suite_id="terminal_runtime"),
            TestPartitionItem("terminal_ledger_summary", owner_suite_id="terminal_runtime"),
            TestPartitionItem("terminal_ledger_traceability", owner_suite_id="terminal_runtime"),
            TestPartitionItem("terminal_ledger_closure", owner_suite_id="terminal_runtime"),
            TestPartitionItem("terminal_ledger_recovery", owner_suite_id="terminal_runtime"),
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
                owns_state=("install_prompt_assets", "owner_export_manifest", "packet_prompt_assets"),
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
                "public_api_allowlist",
                "owner_export_registry",
                "owner_export_manifest",
                "owner_export_manifest_actions",
                "owner_export_manifest_controller",
                "owner_export_manifest_route",
                "owner_export_manifest_startup",
                "owner_export_manifest_terminal_work",
                "packet_prompt_assets",
                "cli",
                "controller_runtime",
                "artifact_validation",
                "control_transactions",
                "internal_actions",
                "role_output_bridge",
                "startup_support",
                "lifecycle_support",
                "child_skill_capability",
                "route_completion_support",
                "model_gate_state",
                "pm_role_followup",
                "proof_validation",
                "card_return_settlement",
                "event_identity",
                "daemon_runtime",
                "runtime_state",
                "router_protocol_catalog",
                "startup_flow",
                "startup_bootloader",
                "startup_intake",
                "startup_display",
                "startup_role_recovery",
                "startup_closure",
                "startup_fact_boundary",
                "self_interrogation",
                "payload_contracts",
                "controller_repair",
                "action_factory",
                "action_factory_reconciliation",
                "action_factory_dispatch",
                "action_factory_envelope",
                "system_cards",
                "expected_waits",
                "route_artifacts",
                "lifecycle_requests",
                "controller_scheduler",
                "controller_scheduler_receipt_writes",
                "controller_scheduler_receipt_effects",
                "controller_scheduler_receipt_pending",
                "controller_scheduler_receipt_scheduled",
                "work_packets",
                "pm_role_work_gates",
                "pm_role_work_writes",
                "pm_role_work_lifecycle",
                "pm_role_work_actions",
                "events_repair",
                "event_dispatcher",
                "route_frontier",
                "terminal_ledger",
                "terminal_ledger_summary",
                "terminal_ledger_traceability",
                "terminal_ledger_closure",
                "terminal_ledger_recovery",
                "install_prompt_assets",
                "owner_export_manifest",
                "packet_prompt_assets",
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
                "startup_bootloader",
                "startup_intake",
                "startup_display",
                "startup_role_recovery",
                "startup_closure",
                "startup_fact_boundary",
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
                "owner_export_manifest",
                "packet_prompt_assets",
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
    router_text = ROUTER_PATH.read_text(encoding="utf-8")
    router_tree = ast.parse(router_text)
    facade_top_level_function_count = sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for node in router_tree.body
    )
    return RouterFacadeSplitEvidence(
        child_module_count=len(tuple((ROOT / "skills" / "flowpilot" / "assets").glob("flowpilot_router*.py"))),
        facade_line_count=router_text.count("\n") + 1,
        facade_top_level_function_count=facade_top_level_function_count,
        owner_export_registry_declared=ROUTER_EXPORTS_PATH.exists()
        and ROUTER_EXPORT_MANIFEST_PATH.exists(),
        prompt_assets=prompt_assets_from_manifest(),
    )


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
    if evidence.facade_line_count > evidence.max_facade_line_count:
        findings.append(
            {
                "code": "facade_line_budget_exceeded",
                "severity": "blocker",
                "line_count": evidence.facade_line_count,
                "max_line_count": evidence.max_facade_line_count,
                "message": "router skeleton is too large to remain a readable public entrypoint",
            }
        )
    if evidence.facade_top_level_function_count > evidence.max_facade_top_level_function_count:
        findings.append(
            {
                "code": "facade_function_budget_exceeded",
                "severity": "blocker",
                "function_count": evidence.facade_top_level_function_count,
                "max_function_count": evidence.max_facade_top_level_function_count,
                "message": "router skeleton still owns behavior functions instead of delegating to owner modules",
            }
        )
    if evidence.obsolete_compat_wrapper_count > evidence.max_obsolete_compat_wrapper_count:
        findings.append(
            {
                "code": "retained_obsolete_compat_wrapper",
                "severity": "blocker",
                "wrapper_count": evidence.obsolete_compat_wrapper_count,
                "message": "obsolete hand-written compatibility wrappers remain in the router skeleton",
            }
        )
    if not evidence.owner_export_registry_declared:
        findings.append(
            {
                "code": "owner_export_registry_missing",
                "severity": "blocker",
                "message": "router skeleton needs an explicit owner-export registry for transitional internal lookups",
            }
        )
    missing_public_api = sorted(set(evidence.required_public_api_names) - set(evidence.public_api_whitelist))
    if missing_public_api:
        findings.append(
            {
                "code": "missing_public_api_whitelist_entry",
                "severity": "blocker",
                "missing_names": missing_public_api,
                "message": "router public API whitelist is missing required CLI/runtime names",
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
        "facade_line_count": evidence.facade_line_count,
        "facade_top_level_function_count": evidence.facade_top_level_function_count,
        "micro_module_count": evidence.micro_module_count,
        "obsolete_compat_wrapper_count": evidence.obsolete_compat_wrapper_count,
        "public_api_whitelist_count": len(evidence.public_api_whitelist),
    }


def split_hazard_evidence(name: str) -> RouterFacadeSplitEvidence:
    evidence = valid_split_evidence()
    if name == "micro_module_explosion":
        return replace(evidence, child_module_count=940)
    if name == "one_function_file_split":
        return replace(evidence, micro_module_count=940)
    if name == "missing_coarse_phase_owner":
        return replace(evidence, coarse_owner_ids=evidence.coarse_owner_ids[:-1])
    if name == "facade_line_budget_exceeded":
        return replace(evidence, facade_line_count=4096)
    if name == "facade_function_budget_exceeded":
        return replace(evidence, facade_top_level_function_count=73)
    if name == "retained_obsolete_compat_wrapper":
        return replace(evidence, obsolete_compat_wrapper_count=1)
    if name == "owner_export_registry_missing":
        return replace(evidence, owner_export_registry_declared=False)
    if name == "missing_public_api_whitelist_entry":
        return replace(evidence, public_api_whitelist=evidence.public_api_whitelist[1:])
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
    "facade_line_budget_exceeded",
    "facade_function_budget_exceeded",
    "retained_obsolete_compat_wrapper",
    "owner_export_registry_missing",
    "missing_public_api_whitelist_entry",
    "missing_prompt_asset",
    "stale_prompt_hash",
    "unsafe_inline_prompt_fallback",
    "prompt_asset_not_installed",
    "undeclared_prompt_template_variables",
)
