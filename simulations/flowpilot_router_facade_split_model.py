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
ROUTER_EXPORT_REGISTRY_PATH = (
    ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_router_facade_export_registry.py"
)
ROUTER_EXPORT_REGISTRY_DATA_PATH = (
    ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit" / "router_facade_owner_exports.json"
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
    child_module_count: int = 292
    max_child_module_count: int = 320
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


from flowpilot_router_facade_split_catalog import (
    ROUTER_FACADE_ENTRYPOINTS,
    ROUTER_FACADE_MODULES,
    ROUTER_FACADE_PARTITIONS,
)
from flowpilot_router_facade_split_targets import (
    ROUTER_FACADE_FUNCTION_BLOCK_MAP,
    ROUTER_FACADE_TARGET_RATIONALES,
    SPLIT_HAZARDS,
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
        and ROUTER_EXPORT_MANIFEST_PATH.exists()
        and ROUTER_EXPORT_REGISTRY_PATH.exists()
        and ROUTER_EXPORT_REGISTRY_DATA_PATH.exists(),
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
