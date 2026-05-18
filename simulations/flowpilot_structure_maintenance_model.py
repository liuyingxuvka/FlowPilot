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


from flowpilot_structure_maintenance_hazards import (
    MODEL_STRUCTURE_HAZARDS,
    STRUCTURE_HAZARDS,
    TESTMESH_HAZARDS,
)
from flowpilot_structure_maintenance_model_catalog import (
    MODEL_PUBLIC_ENTRYPOINTS,
    MODEL_STRUCTURE_MODULES,
    MODEL_STRUCTURE_PARTITIONS,
)
from flowpilot_structure_maintenance_router_catalog import (
    ROUTER_PUBLIC_ENTRYPOINTS,
    ROUTER_STRUCTURE_MODULES,
    ROUTER_STRUCTURE_PARTITIONS,
)
from flowpilot_structure_maintenance_testmesh_catalog import (
    ROUTER_TEST_PARTITIONS,
    ROUTER_TEST_SUITES,
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
