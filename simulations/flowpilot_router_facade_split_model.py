"""FlowGuard model for the FlowPilot router facade and PromptStore split."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
from typing import Any

from flowguard import (
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
    TestSuiteEvidence,
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
    child_module_count: int = 21
    max_child_module_count: int = 24
    micro_module_count: int = 0
    max_micro_module_count: int = 2
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
)


def router_facade_structure_plan() -> StructureMeshPlan:
    return StructureMeshPlan(
        parent_module_id="flowpilot_router_facade_prompt_store_split",
        decision_scope=STRUCTURE_SCOPE_RELEASE,
        required_evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
        partition_items=ROUTER_FACADE_PARTITIONS,
        child_modules=ROUTER_FACADE_MODULES,
        public_entrypoints=ROUTER_FACADE_ENTRYPOINTS,
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
                "install_checks",
                command="python scripts/check_install.py --json",
                result_status=TEST_STATUS_PASSED,
                evidence_tier=EVIDENCE_CONFORMANCE_GREEN,
                result_path="simulations/flowpilot_router_facade_split_results.json",
                owns_state=("install_prompt_assets",),
                release_required=True,
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
        "micro_module_count": evidence.micro_module_count,
    }


def split_hazard_evidence(name: str) -> RouterFacadeSplitEvidence:
    evidence = valid_split_evidence()
    if name == "micro_module_explosion":
        return replace(evidence, child_module_count=940)
    if name == "one_function_file_split":
        return replace(evidence, micro_module_count=940)
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
    "missing_prompt_asset",
    "stale_prompt_hash",
    "unsafe_inline_prompt_fallback",
    "prompt_asset_not_installed",
    "undeclared_prompt_template_variables",
)
