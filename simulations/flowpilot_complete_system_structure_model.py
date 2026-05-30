"""FlowGuard code-structure recommendation for the complete FlowPilot system."""

from __future__ import annotations

from flowguard import CodeStructureRecommendation, TargetModuleRecommendation


MODEL_ID = "flowpilot_complete_system_structure"


FUNCTION_BLOCKS = (
    "current_run_shell",
    "ledger_event_store",
    "deterministic_router",
    "dynamic_host_driver",
    "responsibility_lease_runtime",
    "sealed_packet_runtime",
    "flowguard_work_order_runtime",
    "independent_review_runtime",
    "route_mutation_runtime",
    "cockpit_status_projection",
    "migration_cutover_runtime",
    "validation_evidence_runtime",
)


def build_recommendation() -> CodeStructureRecommendation:
    target_modules = (
        TargetModuleRecommendation(
            module_id="run_shell",
            path="skills/flowpilot/assets/flowpilot_core_runtime/run_shell.py",
            owns_function_blocks=("current_run_shell", "ledger_event_store"),
            owns_state=("current_pointer", "run_index", "run_root", "events"),
            owns_side_effects=("write_run_shell", "append_event"),
            public_entrypoints=("create_run_shell", "load_run_shell"),
            validation_boundaries=("run_shell_persistence", "old_state_not_authority"),
            rationale="Owns the physical current-run authority boundary and append-only event history.",
        ),
        TargetModuleRecommendation(
            module_id="router",
            path="skills/flowpilot/assets/flowpilot_core_runtime/router.py",
            owns_function_blocks=("deterministic_router", "route_mutation_runtime"),
            owns_state=("active_route", "router_next_action", "route_mutations"),
            owns_side_effects=("emit_next_action", "mark_evidence_stale"),
            public_entrypoints=("router_next_action", "apply_router_event"),
            validation_boundaries=("router_state_machine", "route_mutation_stales_evidence"),
            rationale="Keeps route advancement deterministic and separate from agent work.",
        ),
        TargetModuleRecommendation(
            module_id="host",
            path="skills/flowpilot/assets/flowpilot_core_runtime/host.py",
            owns_function_blocks=("dynamic_host_driver", "responsibility_lease_runtime"),
            owns_state=("leases", "host_runs", "role_memory"),
            owns_side_effects=("start_fake_host", "record_live_host_boundary", "quarantine_late_output"),
            public_entrypoints=("lease_responsibility", "expire_lease", "submit_host_result"),
            validation_boundaries=("lease_lifecycle", "fake_dry_live_evidence_boundary"),
            rationale="Owns dynamic responsibility leases and separates fake, dry-run, and live host confidence.",
        ),
        TargetModuleRecommendation(
            module_id="packets",
            path="skills/flowpilot/assets/flowpilot_core_runtime/packets.py",
            owns_function_blocks=("sealed_packet_runtime",),
            owns_state=("packet_envelopes", "packet_bodies", "result_envelopes", "result_bodies"),
            owns_side_effects=("write_packet_body", "write_result_body", "verify_body_hash"),
            public_entrypoints=("issue_packet", "submit_result", "open_sealed_body_for_role"),
            validation_boundaries=("sealed_body_isolation", "body_hash_mismatch_blocks"),
            rationale="Owns envelope/body separation and hash integrity for task and result packets.",
        ),
        TargetModuleRecommendation(
            module_id="flowguard_orders",
            path="skills/flowpilot/assets/flowpilot_core_runtime/flowguard_orders.py",
            owns_function_blocks=("flowguard_work_order_runtime",),
            owns_state=("work_orders", "flowguard_reports"),
            owns_side_effects=("select_flowguard_skill", "record_proof_artifact"),
            public_entrypoints=("create_flowguard_order", "complete_flowguard_order"),
            validation_boundaries=("modeled_target_scheduler", "wrong_target_rejected"),
            rationale="Owns modeled-target scheduling and report provenance before PM decisions.",
        ),
        TargetModuleRecommendation(
            module_id="review_closure",
            path="skills/flowpilot/assets/flowpilot_core_runtime/review_closure.py",
            owns_function_blocks=("independent_review_runtime", "validation_evidence_runtime"),
            owns_state=("reviews", "validation_evidence", "final_closure"),
            owns_side_effects=("accept_result", "block_result", "write_backward_chain"),
            public_entrypoints=("review_result", "record_validation_evidence", "attempt_final_closure"),
            validation_boundaries=("independent_review", "final_backward_chain"),
            rationale="Owns review, validation evidence, and terminal closure decisions.",
        ),
        TargetModuleRecommendation(
            module_id="cockpit",
            path="skills/flowpilot/assets/flowpilot_core_runtime/cockpit.py",
            owns_function_blocks=("cockpit_status_projection",),
            owns_state=("status_projection", "user_events"),
            owns_side_effects=("render_public_status", "record_user_event"),
            public_entrypoints=("render_status", "submit_cockpit_event"),
            validation_boundaries=("projection_only_ui", "sealed_body_not_rendered"),
            rationale="Owns UI/status projection and keeps Cockpit from becoming authority.",
        ),
        TargetModuleRecommendation(
            module_id="migration",
            path="skills/flowpilot/assets/flowpilot_core_runtime/migration.py",
            owns_function_blocks=("migration_cutover_runtime",),
            owns_state=("imported_evidence", "cutover_gate"),
            owns_side_effects=("classify_old_artifact", "record_cutover_decision"),
            public_entrypoints=("import_old_artifact", "evaluate_cutover_gate"),
            validation_boundaries=("old_artifacts_read_only", "cutover_requires_full_evidence"),
            rationale="Owns old FlowPilot asset import and public-entrypoint cutover evidence.",
        ),
    )
    return CodeStructureRecommendation(
        recommendation_id=MODEL_ID,
        source_model_id="flowpilot_complete_system_development_process",
        source_model_path="simulations/flowpilot_complete_system_development_model.py",
        source_model_evidence_tier="executable_flowguard",
        parent_module_id="skills/flowpilot/assets/flowpilot_core_runtime",
        target_modules=target_modules,
        function_block_map=tuple(
            (block, module.module_id)
            for module in target_modules
            for block in module.owns_function_blocks
        ),
        state_owner_map=tuple(
            (state, module.module_id)
            for module in target_modules
            for state in module.owns_state
        ),
        side_effect_owner_map=tuple(
            (effect, module.module_id)
            for module in target_modules
            for effect in module.owns_side_effects
        ),
        public_entrypoint_map=tuple(
            (entrypoint, module.module_id)
            for module in target_modules
            for entrypoint in module.public_entrypoints
        ),
        facade_module_id="skills/flowpilot/assets/flowpilot_core_runtime/__init__.py",
        validation_boundaries=(
            "run_shell_persistence",
            "router_state_machine",
            "lease_lifecycle",
            "sealed_body_isolation",
            "modeled_target_scheduler",
            "independent_review",
            "projection_only_ui",
            "old_artifacts_read_only",
        ),
        rationale=(
            "The complete system is split by FunctionBlock ownership so tests "
            "can observe input gates, state writes, side effects, and public "
            "entrypoints without treating the old router as authority."
        ),
        hierarchical_model_used=True,
    )


def known_bad_recommendations() -> dict[str, CodeStructureRecommendation]:
    good = build_recommendation()
    modules = list(good.target_modules)
    missing_host = tuple(module for module in modules if module.module_id != "host")
    return {
        "missing_dynamic_host_owner": CodeStructureRecommendation(
            recommendation_id="missing_dynamic_host_owner",
            source_model_id=good.source_model_id,
            parent_module_id=good.parent_module_id,
            target_modules=missing_host,
            function_block_map=tuple(
                item for item in good.function_block_map if item[0] != "dynamic_host_driver"
            ),
            state_owner_map=good.state_owner_map,
            side_effect_owner_map=good.side_effect_owner_map,
            public_entrypoint_map=good.public_entrypoint_map,
            facade_module_id=good.facade_module_id,
            validation_boundaries=good.validation_boundaries,
            rationale="Known-bad: host owner removed.",
            hierarchical_model_used=True,
        ),
        "missing_module_rationale": CodeStructureRecommendation(
            recommendation_id="missing_module_rationale",
            source_model_id=good.source_model_id,
            parent_module_id=good.parent_module_id,
            target_modules=(
                TargetModuleRecommendation(
                    module_id="run_shell",
                    path="skills/flowpilot/assets/flowpilot_core_runtime/run_shell.py",
                    owns_function_blocks=("current_run_shell",),
                    owns_state=("current_pointer",),
                    validation_boundaries=("run_shell_persistence",),
                    rationale="",
                ),
            ),
            function_block_map=good.function_block_map,
            state_owner_map=good.state_owner_map,
            side_effect_owner_map=good.side_effect_owner_map,
            public_entrypoint_map=good.public_entrypoint_map,
            facade_module_id=good.facade_module_id,
            validation_boundaries=good.validation_boundaries,
            rationale="Known-bad: module ownership lacks rationale.",
            hierarchical_model_used=True,
        ),
    }
