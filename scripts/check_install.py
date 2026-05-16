"""Lightweight self-check for the FlowPilot skill package."""

from __future__ import annotations

import importlib
import contextlib
import io
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ROLE_OUTPUT_BINDING_REQUIRED_FIELDS = {
    "runtime_channel",
    "output_type",
    "body_schema_version",
    "expected_return_envelope",
    "default_subdir",
    "default_filename_prefix",
    "path_key",
    "hash_key",
    "router_event_mode",
}


def _role_output_runtime_binding_issues(flowpilot_router, role_output_runtime):
    registry_path = ROOT / "skills/flowpilot/assets/runtime_kit/contracts/contract_index.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    runtime_specs = getattr(role_output_runtime, "OUTPUT_TYPE_SPECS", {})
    router_events = set(getattr(flowpilot_router, "EXTERNAL_EVENTS", {}))
    issues = []
    for item in registry.get("contracts", []):
        if not isinstance(item, dict) or item.get("runtime_channel") != "role_output_runtime":
            continue
        contract_id = str(item.get("contract_id") or "")
        missing = sorted(field for field in ROLE_OUTPUT_BINDING_REQUIRED_FIELDS if not item.get(field))
        if missing:
            issues.append(f"{contract_id}: missing runtime binding fields {missing}")
            continue
        if item.get("expected_return_envelope") != "role_output_envelope":
            issues.append(f"{contract_id}: expected_return_envelope must be role_output_envelope")
        if item.get("router_event_mode") == "fixed":
            router_event = str(item.get("router_event") or "")
            if router_event not in router_events:
                issues.append(f"{contract_id}: fixed router_event is not registered: {router_event}")
        elif item.get("router_event_mode") != "router_supplied":
            issues.append(f"{contract_id}: router_event_mode must be fixed or router_supplied")
        output_types = [item.get("output_type"), *item.get("output_type_aliases", [])]
        for output_type in [str(value) for value in output_types if value]:
            spec = runtime_specs.get(output_type)
            if spec is None:
                issues.append(f"{contract_id}: runtime missing output_type {output_type}")
                continue
            comparisons = {
                "contract_id": contract_id,
                "body_schema_version": item.get("body_schema_version"),
                "path_key": item.get("path_key"),
                "hash_key": item.get("hash_key"),
                "default_subdir": item.get("default_subdir"),
                "default_filename_prefix": item.get("default_filename_prefix"),
            }
            for attr, expected in comparisons.items():
                if getattr(spec, attr, None) != expected:
                    issues.append(f"{contract_id}: {output_type}.{attr} does not match registry")
            if tuple(str(role) for role in item.get("recipient_roles", [])) != getattr(spec, "allowed_roles", ()):
                issues.append(f"{contract_id}: {output_type}.allowed_roles does not match registry")
            expected_event = item.get("router_event") if item.get("router_event_mode") == "fixed" else None
            if getattr(spec, "event_name", None) != expected_event:
                issues.append(f"{contract_id}: {output_type}.event_name does not match registry")
    return issues


REQUIRED_FILES = [
    "README.md",
    "CHANGELOG.md",
    "VERSION",
    "AGENTS.md",
    "HANDOFF.md",
    "docs/project_brief.md",
    "docs/design_decisions.md",
    "docs/flowguard_preflight_findings.md",
    "docs/flowguard_model_mesh_plan.md",
    "docs/stable_heartbeat_plan_frontier_findings.md",
    "docs/protocol.md",
    "docs/schema.md",
    "docs/verification.md",
    "docs/reviewer_fact_audit.md",
    "docs/flowpilot_clean_rebuild_plan.md",
    "docs/flowpilot_control_table_prompt_registry_migration_plan.md",
    "docs/flowpilot_control_transaction_registry_plan.md",
    "docs/flowpilot_legal_next_action_policy_plan.md",
    "docs/flowpilot_startup_optimization_plan.md",
    "docs/startup_intake_ui_integration_plan.md",
    "docs/flowpilot_route_replanning_policy_plan.md",
    "docs/legacy_to_router_equivalence.md",
    "docs/legacy_to_router_equivalence.json",
    "docs/barrier_bundle_equivalence.md",
    "docs/legacy_prompt_to_cards_matrix.md",
    "docs/legacy_prompt_to_cards_matrix.json",
    "docs/flowpilot_ten_step_migration_status.json",
    "flowpilot.dependencies.json",
    "assets/brand/README.md",
    "assets/brand/flowpilot-icon-default.png",
    "assets/brand/source/flowpilot-icon-generated-source.png",
    "skills/flowpilot/SKILL.md",
    "skills/flowpilot/DEPENDENCIES.md",
    "skills/flowpilot/assets/barrier_bundle.py",
    "skills/flowpilot/assets/flowpilot_router_card_settlement.py",
    "skills/flowpilot/assets/flowpilot_router_controller_boundary.py",
    "skills/flowpilot/assets/flowpilot_router_controller_reconciliation.py",
    "skills/flowpilot/assets/flowpilot_router_dispatch_gate.py",
    "skills/flowpilot/assets/flowpilot_router_errors.py",
    "skills/flowpilot/assets/flowpilot_router_io.py",
    "skills/flowpilot/assets/flowpilot_router_protocol_tables.py",
    "skills/flowpilot/assets/flowpilot_router_startup_daemon.py",
    "skills/flowpilot/assets/flowpilot_router_terminal.py",
    "skills/flowpilot/assets/flowpilot_router.py",
    "skills/flowpilot/assets/packet_runtime.py",
    "skills/flowpilot/assets/role_output_runtime.py",
    "skills/flowpilot/assets/brand/flowpilot-icon-default.png",
    "skills/flowpilot/assets/ui/startup_intake/flowpilot_startup_intake.ps1",
    "skills/flowpilot/assets/runtime_kit/manifest.json",
    "skills/flowpilot/assets/runtime_kit/README.md",
    "skills/flowpilot/assets/runtime_kit/control_transaction_registry.json",
    "skills/flowpilot/assets/runtime_kit/route_action_policy_registry.json",
    "skills/flowpilot/assets/runtime_kit/contracts/contract_index.json",
    "skills/flowpilot/assets/runtime_kit/quality_pack_catalog.json",
    "skills/flowpilot/assets/runtime_kit/cards/system/startup_banner.md",
    "skills/flowpilot/assets/runtime_kit/cards/system/controller_resume_reentry.md",
    "skills/flowpilot/assets/runtime_kit/cards/roles/controller.md",
    "skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md",
    "skills/flowpilot/assets/runtime_kit/cards/roles/human_like_reviewer.md",
    "skills/flowpilot/assets/runtime_kit/cards/roles/process_flowguard_officer.md",
    "skills/flowpilot/assets/runtime_kit/cards/roles/product_flowguard_officer.md",
    "skills/flowpilot/assets/runtime_kit/cards/roles/worker_a.md",
    "skills/flowpilot/assets/runtime_kit/cards/roles/worker_b.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_output_contract_catalog.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_controller_reset_duty.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_phase_map.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_child_skill_gate_manifest.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_child_skill_selection.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_dependency_policy.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_material_absorb_or_research.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_material_understanding.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_material_scan.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_node_acceptance_plan.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_parent_backward_targets.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_parent_segment_decision.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_research_absorb_or_mutate.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_research_package.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_startup_activation.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_startup_intake.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_resume_decision.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_product_architecture.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_root_contract.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_route_skeleton.md",
    "skills/flowpilot/assets/runtime_kit/cards/officers/route_process_check.md",
    "skills/flowpilot/assets/runtime_kit/cards/officers/route_product_check.md",
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/route_challenge.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_current_node_loop.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_evidence_quality_package.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_model_miss_triage.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_review_repair.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_final_ledger.md",
    "skills/flowpilot/assets/runtime_kit/cards/phases/pm_closure.md",
    "skills/flowpilot/assets/runtime_kit/cards/events/pm_reviewer_report.md",
    "skills/flowpilot/assets/runtime_kit/cards/events/pm_node_started.md",
    "skills/flowpilot/assets/runtime_kit/cards/events/pm_reviewer_blocked.md",
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/dispatch_request.md",
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/material_sufficiency.md",
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/child_skill_gate_manifest_review.md",
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/current_node_dispatch.md",
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/evidence_quality_review.md",
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/final_backward_replay.md",
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/product_architecture_challenge.md",
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/node_acceptance_plan_review.md",
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/parent_backward_replay.md",
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/research_direct_source_check.md",
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/root_contract_challenge.md",
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/startup_fact_check.md",
    "skills/flowpilot/assets/runtime_kit/cards/reviewer/worker_result_review.md",
    "skills/flowpilot/assets/runtime_kit/cards/roles/worker_research_report.md",
    "skills/flowpilot/assets/runtime_kit/cards/officers/product_architecture_modelability.md",
    "skills/flowpilot/assets/runtime_kit/cards/officers/child_skill_conformance_model.md",
    "skills/flowpilot/assets/runtime_kit/cards/officers/child_skill_product_fit.md",
    "skills/flowpilot/assets/runtime_kit/cards/officers/root_contract_modelability.md",
    "skills/flowpilot/references/protocol.md",
    "skills/flowpilot/references/installation_contract.md",
    "skills/flowpilot/references/failure_modes.md",
    "skills/autonomous-concept-ui-redesign/SKILL.md",
    "skills/autonomous-concept-ui-redesign/references/dependency-map.md",
    "skills/autonomous-concept-ui-redesign/references/concept-brief.md",
    "skills/autonomous-concept-ui-redesign/references/design-search.md",
    "skills/autonomous-concept-ui-redesign/references/divergence-review.md",
    "skills/autonomous-concept-ui-redesign/references/functional-framing.md",
    "skills/autonomous-concept-ui-redesign/references/layout-geometry-qa.md",
    "skills/autonomous-concept-ui-redesign/references/platform-notes.md",
    "skills/autonomous-concept-ui-redesign/references/run-report-template.md",
    "skills/autonomous-concept-ui-redesign/references/visual-qa-loop.md",
    "skills/autonomous-concept-ui-redesign/scripts/app_icon_asset_check.py",
    "templates/flowpilot/README.md",
    "templates/flowpilot/current.template.json",
    "templates/flowpilot/index.template.json",
    "templates/flowpilot/runs/run-001/run.template.json",
    "templates/flowpilot/state.template.json",
    "templates/flowpilot/crew_ledger.template.json",
    "templates/flowpilot/crew_memory/role_memory.template.json",
    "templates/flowpilot/crew_memory/crew_rehydration_report.template.json",
    "templates/flowpilot/material_intake_packet.template.json",
    "templates/flowpilot/pm_material_understanding.template.json",
    "templates/flowpilot/child_skill_gate_manifest.template.json",
    "templates/flowpilot/research_package.template.json",
    "templates/flowpilot/research_worker_report.template.json",
    "templates/flowpilot/research_reviewer_report.template.json",
    "templates/flowpilot/product_function_architecture.template.json",
    "templates/flowpilot/root_acceptance_contract.template.json",
    "templates/flowpilot/standard_scenario_pack.template.json",
    "templates/flowpilot/node_acceptance_plan.template.json",
    "templates/flowpilot/parent_backward_targets.template.json",
    "templates/flowpilot/parent_backward_replay.template.json",
    "templates/flowpilot/packet_ledger.template.json",
    "templates/flowpilot/packets/packet_envelope.template.json",
    "templates/flowpilot/packets/packet_body.template.md",
    "templates/flowpilot/packets/result_envelope.template.json",
    "templates/flowpilot/packets/result_body.template.md",
    "templates/flowpilot/packets/controller_status_packet.template.json",
    "templates/flowpilot/packets/packet_chain_audit.template.json",
    "templates/flowpilot/flowguard_modeling_request.template.json",
    "templates/flowpilot/flowguard_modeling_report.template.json",
    "templates/flowpilot/flowguard_model_miss_request.template.json",
    "templates/flowpilot/flowguard_model_miss_report.template.json",
    "templates/flowpilot/role_approval.template.json",
    "templates/flowpilot/human_review.template.json",
    "templates/flowpilot/review_release_order.template.json",
    "templates/flowpilot/continuation_evidence.template.json",
    "templates/flowpilot/defects/defect_ledger.template.json",
    "templates/flowpilot/defects/defect_event.template.json",
    "templates/flowpilot/evidence/evidence_ledger.template.json",
    "templates/flowpilot/evidence/evidence_event.template.json",
    "templates/flowpilot/generated_resource_ledger.template.json",
    "templates/flowpilot/generated_resource_event.template.json",
    "templates/flowpilot/activity_stream.template.json",
    "templates/flowpilot/activity_event.template.json",
    "templates/flowpilot/pause_snapshot.template.json",
    "templates/flowpilot/final_route_wide_gate_ledger.template.json",
    "templates/flowpilot/barrier_bundle.template.json",
    "templates/flowpilot/terminal_human_backward_replay_map.template.json",
    "templates/flowpilot/terminal_closure_suite.template.json",
    "templates/flowpilot/output_contract.template.json",
    "templates/flowpilot/flowpilot_skill_improvement_observation.template.json",
    "templates/flowpilot/flowpilot_skill_improvement_report.template.json",
    "templates/flowpilot/execution_frontier.template.json",
    "templates/flowpilot/startup_review.template.json",
    "templates/flowpilot/startup_pm_gate.template.json",
    "templates/flowpilot/capabilities.template.json",
    "templates/flowpilot/contract.template.md",
    "templates/flowpilot/routes/route-001/flow.template.json",
    "templates/flowpilot/routes/route-001/flow.template.md",
    "templates/flowpilot/routes/route-001/nodes/node-001-start/node.template.json",
    "templates/flowpilot/heartbeats/hb.template.json",
    "templates/flowpilot/diagrams/user-flow-diagram.template.mmd",
    "templates/flowpilot/diagrams/user-flow-diagram.template.md",
    "templates/flowpilot/checkpoints/checkpoint.template.json",
    "templates/flowpilot/capabilities/capability-evidence.template.json",
    "templates/flowpilot/experiments/experiment-001/experiment.template.json",
    "templates/flowpilot/task-models/README.md",
    "examples/minimal/README.md",
    "examples/minimal/task.md",
    "simulations/meta_model.py",
    "simulations/run_meta_checks.py",
    "simulations/flowpilot_parent_responsibility_ledger.json",
    "simulations/flowpilot_thin_parent_checks.py",
    "simulations/meta_thin_parent_results.json",
    "simulations/capability_model.py",
    "simulations/run_capability_checks.py",
    "simulations/capability_thin_parent_results.json",
    "simulations/user_flow_diagram_model.py",
    "simulations/run_user_flow_diagram_checks.py",
    "simulations/user_flow_diagram_results.json",
    "simulations/defect_governance_model.py",
    "simulations/run_defect_governance_checks.py",
    "simulations/defect_governance_results.json",
    "simulations/startup_pm_review_model.py",
    "simulations/run_startup_pm_review_checks.py",
    "simulations/startup_pm_review_results.json",
    "simulations/barrier_equivalence_model.py",
    "simulations/run_barrier_equivalence_checks.py",
    "simulations/barrier_equivalence_results.json",
    "simulations/router_next_recipient_model.py",
    "simulations/run_router_next_recipient_checks.py",
    "simulations/router_next_recipient_results.json",
    "simulations/prompt_isolation_model.py",
    "simulations/run_prompt_isolation_checks.py",
    "simulations/prompt_isolation_results.json",
    "docs/reviewer_only_gate_simplification_plan.md",
    "simulations/flowpilot_reviewer_only_gate_model.py",
    "simulations/run_flowpilot_reviewer_only_gate_checks.py",
    "simulations/flowpilot_reviewer_only_gate_results.json",
    "simulations/card_instruction_coverage_model.py",
    "simulations/run_card_instruction_coverage_checks.py",
    "simulations/card_instruction_coverage_results.json",
    "simulations/flowpilot_resume_model.py",
    "simulations/run_flowpilot_resume_checks.py",
    "simulations/flowpilot_resume_results.json",
    "simulations/flowpilot_daemon_liveness_model.py",
    "simulations/run_flowpilot_daemon_liveness_checks.py",
    "simulations/flowpilot_daemon_liveness_results.json",
    "simulations/flowpilot_router_loop_model.py",
    "simulations/run_flowpilot_router_loop_checks.py",
    "simulations/flowpilot_router_loop_results.json",
    "simulations/flowpilot_control_plane_friction_model.py",
    "simulations/run_flowpilot_control_plane_friction_checks.py",
    "simulations/flowpilot_control_plane_friction_results.json",
    "simulations/flowpilot_event_contract_model.py",
    "simulations/run_flowpilot_event_contract_checks.py",
    "simulations/flowpilot_event_contract_results.json",
    "simulations/flowpilot_event_capability_registry_model.py",
    "simulations/run_flowpilot_event_capability_registry_checks.py",
    "simulations/flowpilot_event_capability_registry_results.json",
    "simulations/flowpilot_cross_plane_friction_model.py",
    "simulations/run_flowpilot_cross_plane_friction_checks.py",
    "simulations/flowpilot_cross_plane_friction_results.json",
    "simulations/flowpilot_model_mesh_model.py",
    "simulations/run_flowpilot_model_mesh_checks.py",
    "simulations/flowpilot_model_mesh_results.json",
    "simulations/flowpilot_model_hierarchy_model.py",
    "simulations/run_flowpilot_model_hierarchy_checks.py",
    "simulations/flowpilot_model_hierarchy_results.json",
    "simulations/flowpilot_control_transaction_registry_model.py",
    "simulations/run_flowpilot_control_transaction_registry_checks.py",
    "simulations/flowpilot_control_transaction_registry_results.json",
    "simulations/flowpilot_legal_next_action_model.py",
    "simulations/run_flowpilot_legal_next_action_checks.py",
    "simulations/flowpilot_legal_next_action_results.json",
    "simulations/flowpilot_output_contract_model.py",
    "simulations/run_output_contract_checks.py",
    "simulations/flowpilot_output_contract_results.json",
    "simulations/flowpilot_router_action_contract_model.py",
    "simulations/run_router_action_contract_checks.py",
    "simulations/flowpilot_router_action_contract_results.json",
    "simulations/flowpilot_packet_lifecycle_model.py",
    "simulations/run_flowpilot_packet_lifecycle_checks.py",
    "simulations/flowpilot_packet_lifecycle_results.json",
    "simulations/flowpilot_command_refinement_model.py",
    "simulations/run_command_refinement_checks.py",
    "simulations/flowpilot_command_refinement_results.json",
    "simulations/flowpilot_planning_quality_model.py",
    "simulations/run_flowpilot_planning_quality_checks.py",
    "simulations/flowpilot_planning_quality_results.json",
    "simulations/flowpilot_reviewer_active_challenge_model.py",
    "simulations/run_flowpilot_reviewer_active_challenge_checks.py",
    "simulations/flowpilot_reviewer_active_challenge_results.json",
    "simulations/flowpilot_startup_optimization_model.py",
    "simulations/run_flowpilot_startup_optimization_checks.py",
    "simulations/flowpilot_startup_optimization_results.json",
    "simulations/flowpilot_startup_intake_ui_model.py",
    "simulations/run_flowpilot_startup_intake_ui_checks.py",
    "simulations/flowpilot_startup_intake_ui_results.json",
    "simulations/flowpilot_protocol_contract_conformance_model.py",
    "simulations/run_protocol_contract_conformance_checks.py",
    "simulations/protocol_contract_conformance_model_only_results.json",
    "simulations/protocol_contract_conformance_results.json",
    "simulations/flowpilot_repair_transaction_model.py",
    "simulations/run_flowpilot_repair_transaction_checks.py",
    "simulations/flowpilot_repair_transaction_results.json",
    "simulations/flowpilot_route_replanning_policy_model.py",
    "simulations/run_flowpilot_route_replanning_policy_checks.py",
    "simulations/flowpilot_route_replanning_policy_results.json",
    "simulations/flowpilot_role_output_runtime_model.py",
    "simulations/run_flowpilot_role_output_runtime_checks.py",
    "simulations/flowpilot_role_output_runtime_results.json",
    "simulations/release_tooling_model.py",
    "simulations/run_release_tooling_checks.py",
    "simulations/release_tooling_results.json",
    "scripts/check_runtime_card_capability_reminders.py",
    "scripts/install_flowpilot.py",
    "scripts/audit_local_install_sync.py",
    "scripts/check_public_release.py",
    "scripts/flowpilot_paths.py",
    "scripts/flowpilot_defects.py",
    "scripts/flowpilot_lifecycle.py",
    "scripts/flowpilot_packets.py",
    "scripts/flowpilot_outputs.py",
    "scripts/flowpilot_runtime.py",
    "scripts/flowpilot_user_flow_diagram.py",
    "scripts/smoke_autopilot.py",
    "skills/flowpilot/assets/flowpilot_runtime.py",
    "skills/flowpilot/assets/flowpilot_paths.py",
    "skills/flowpilot/assets/flowpilot_user_flow_diagram.py",
    "tests/test_flowpilot_router_boundaries.py",
    "tests/test_flowpilot_router_runtime.py",
    "tests/test_flowpilot_router_runtime_ack_return.py",
    "tests/test_flowpilot_router_runtime_controller.py",
    "tests/test_flowpilot_router_runtime_dispatch_gate.py",
    "tests/test_flowpilot_router_runtime_startup_daemon.py",
    "tests/test_flowpilot_router_runtime_terminal.py",
    "tests/test_flowpilot_barrier_bundle.py",
    "tests/test_flowpilot_card_instruction_coverage.py",
    "tests/test_flowpilot_output_contracts.py",
    "tests/test_flowpilot_planning_quality.py",
    "tests/test_flowpilot_reviewer_active_challenge.py",
    "tests/test_flowpilot_role_output_runtime.py",
]

JSON_FILES = [
    "flowpilot.dependencies.json",
    "docs/legacy_to_router_equivalence.json",
    "docs/legacy_prompt_to_cards_matrix.json",
    "docs/flowpilot_ten_step_migration_status.json",
    "skills/flowpilot/assets/runtime_kit/manifest.json",
    "skills/flowpilot/assets/runtime_kit/control_transaction_registry.json",
    "skills/flowpilot/assets/runtime_kit/route_action_policy_registry.json",
    "skills/flowpilot/assets/runtime_kit/contracts/contract_index.json",
    "skills/flowpilot/assets/runtime_kit/quality_pack_catalog.json",
    "simulations/release_tooling_results.json",
    "simulations/barrier_equivalence_results.json",
    "simulations/router_next_recipient_results.json",
    "simulations/user_flow_diagram_results.json",
    "simulations/prompt_isolation_results.json",
    "simulations/flowpilot_reviewer_only_gate_results.json",
    "simulations/card_instruction_coverage_results.json",
    "simulations/flowpilot_resume_results.json",
    "simulations/flowpilot_daemon_liveness_results.json",
    "simulations/flowpilot_router_loop_results.json",
    "simulations/flowpilot_control_plane_friction_results.json",
    "simulations/flowpilot_event_contract_results.json",
    "simulations/flowpilot_event_capability_registry_results.json",
    "simulations/flowpilot_cross_plane_friction_results.json",
    "simulations/flowpilot_model_mesh_results.json",
    "simulations/flowpilot_model_hierarchy_results.json",
    "simulations/flowpilot_parent_responsibility_ledger.json",
    "simulations/meta_thin_parent_results.json",
    "simulations/capability_thin_parent_results.json",
    "simulations/flowpilot_control_transaction_registry_results.json",
    "simulations/flowpilot_legal_next_action_results.json",
    "simulations/flowpilot_output_contract_results.json",
    "simulations/flowpilot_router_action_contract_results.json",
    "simulations/flowpilot_packet_lifecycle_results.json",
    "simulations/flowpilot_command_refinement_results.json",
    "simulations/flowpilot_planning_quality_results.json",
    "simulations/flowpilot_reviewer_active_challenge_results.json",
    "simulations/flowpilot_startup_optimization_results.json",
    "simulations/protocol_contract_conformance_model_only_results.json",
    "simulations/protocol_contract_conformance_results.json",
    "simulations/flowpilot_role_output_runtime_results.json",
    "simulations/flowpilot_route_replanning_policy_results.json",
    "templates/flowpilot/current.template.json",
    "templates/flowpilot/index.template.json",
    "templates/flowpilot/runs/run-001/run.template.json",
    "templates/flowpilot/capabilities.template.json",
    "templates/flowpilot/state.template.json",
    "templates/flowpilot/crew_ledger.template.json",
    "templates/flowpilot/crew_memory/role_memory.template.json",
    "templates/flowpilot/crew_memory/crew_rehydration_report.template.json",
    "templates/flowpilot/material_intake_packet.template.json",
    "templates/flowpilot/pm_material_understanding.template.json",
    "templates/flowpilot/child_skill_gate_manifest.template.json",
    "templates/flowpilot/research_package.template.json",
    "templates/flowpilot/research_worker_report.template.json",
    "templates/flowpilot/research_reviewer_report.template.json",
    "templates/flowpilot/product_function_architecture.template.json",
    "templates/flowpilot/root_acceptance_contract.template.json",
    "templates/flowpilot/standard_scenario_pack.template.json",
    "templates/flowpilot/node_acceptance_plan.template.json",
    "templates/flowpilot/parent_backward_targets.template.json",
    "templates/flowpilot/parent_backward_replay.template.json",
    "templates/flowpilot/packet_ledger.template.json",
    "templates/flowpilot/packets/packet_envelope.template.json",
    "templates/flowpilot/packets/result_envelope.template.json",
    "templates/flowpilot/packets/controller_status_packet.template.json",
    "templates/flowpilot/packets/packet_chain_audit.template.json",
    "templates/flowpilot/flowguard_modeling_request.template.json",
    "templates/flowpilot/flowguard_modeling_report.template.json",
    "templates/flowpilot/flowguard_model_miss_request.template.json",
    "templates/flowpilot/flowguard_model_miss_report.template.json",
    "templates/flowpilot/role_approval.template.json",
    "templates/flowpilot/human_review.template.json",
    "templates/flowpilot/review_release_order.template.json",
    "templates/flowpilot/continuation_evidence.template.json",
    "templates/flowpilot/defects/defect_ledger.template.json",
    "templates/flowpilot/defects/defect_event.template.json",
    "templates/flowpilot/evidence/evidence_ledger.template.json",
    "templates/flowpilot/evidence/evidence_event.template.json",
    "templates/flowpilot/generated_resource_ledger.template.json",
    "templates/flowpilot/generated_resource_event.template.json",
    "templates/flowpilot/activity_stream.template.json",
    "templates/flowpilot/activity_event.template.json",
    "templates/flowpilot/pause_snapshot.template.json",
    "templates/flowpilot/final_route_wide_gate_ledger.template.json",
    "templates/flowpilot/barrier_bundle.template.json",
    "templates/flowpilot/terminal_human_backward_replay_map.template.json",
    "templates/flowpilot/terminal_closure_suite.template.json",
    "templates/flowpilot/output_contract.template.json",
    "templates/flowpilot/flowpilot_skill_improvement_observation.template.json",
    "templates/flowpilot/flowpilot_skill_improvement_report.template.json",
    "templates/flowpilot/execution_frontier.template.json",
    "templates/flowpilot/startup_review.template.json",
    "templates/flowpilot/startup_pm_gate.template.json",
    "templates/flowpilot/routes/route-001/flow.template.json",
    "templates/flowpilot/routes/route-001/nodes/node-001-start/node.template.json",
    "templates/flowpilot/heartbeats/hb.template.json",
    "templates/flowpilot/checkpoints/checkpoint.template.json",
    "templates/flowpilot/capabilities/capability-evidence.template.json",
    "templates/flowpilot/experiments/experiment-001/experiment.template.json",
    "simulations/defect_governance_results.json",
    "simulations/flowpilot_repair_transaction_results.json",
]

OPTIONAL_RUNTIME_JSON_FILES = [
    ".flowpilot/current.json",
    ".flowpilot/index.json",
    ".flowpilot/runs/run-001/capabilities.json",
    ".flowpilot/runs/run-001/state.json",
    ".flowpilot/runs/run-001/execution_frontier.json",
    ".flowpilot/runs/run-001/routes/route-001/flow.json",
    ".flowpilot/capabilities.json",
    ".flowpilot/state.json",
    ".flowpilot/execution_frontier.json",
    ".flowpilot/routes/route-001/flow.json",
]

RETIRED_PATHS = [
    "docs/external_watchdog_loop_findings.md",
    "scripts/flowpilot_busy_lease.py",
    "scripts/flowpilot_global_supervisor.py",
    "scripts/flowpilot_run_with_busy_lease.py",
    "scripts/flowpilot_watchdog.py",
    "scripts/register_windows_watchdog_task.ps1",
    "templates/flowpilot/heartbeats/global-watchdog-supervisor.prompt.md",
    "templates/flowpilot/watchdog/watchdog.template.json",
]

STARTUP_INTAKE_PS1_SOURCE_FILES = [
    "skills/flowpilot/assets/ui/startup_intake/flowpilot_startup_intake.ps1",
    "docs/ui/startup_intake_desktop_preview/flowpilot_startup_intake.ps1",
]

UTF8_BOM = b"\xef\xbb\xbf"


def main() -> int:
    result: dict[str, object] = {"ok": True, "checks": []}

    try:
        flowguard = importlib.import_module("flowguard")
        result["checks"].append(
            {
                "name": "flowguard_import",
                "ok": True,
                "schema_version": getattr(flowguard, "SCHEMA_VERSION", "unknown"),
            }
        )
    except Exception as exc:  # pragma: no cover - diagnostic script
        result["ok"] = False
        result["checks"].append(
            {"name": "flowguard_import", "ok": False, "error": repr(exc)}
        )

    for relpath in REQUIRED_FILES:
        exists = (ROOT / relpath).exists()
        result["checks"].append({"name": f"file:{relpath}", "ok": exists})
        if not exists:
            result["ok"] = False

    for relpath in STARTUP_INTAKE_PS1_SOURCE_FILES:
        path = ROOT / relpath
        exists = path.exists()
        data = path.read_bytes() if exists else b""
        contains_non_ascii = any(byte >= 0x80 for byte in data)
        has_utf8_bom = data.startswith(UTF8_BOM)
        ok = exists and (not contains_non_ascii or has_utf8_bom)
        result["checks"].append(
            {
                "name": f"powershell_source_encoding:{relpath}",
                "ok": ok,
                "exists": exists,
                "contains_non_ascii": contains_non_ascii,
                "utf8_bom": has_utf8_bom,
            }
        )
        if not ok:
            result["ok"] = False

    skill_path = ROOT / "skills/flowpilot/SKILL.md"
    if skill_path.exists():
        text = skill_path.read_text(encoding="utf-8")
        has_name = "\nname: flowpilot\n" in f"\n{text}"
        result["checks"].append({"name": "skill_name:flowpilot", "ok": has_name})
        if not has_name:
            result["ok"] = False
        small_router_launcher = (
            len(text.splitlines()) < 120
            and "flowpilot_router.py" in text
            and "Do not read FlowPilot reference files" in text
            and "Final Route-Wide Gate Ledger" not in text
        )
        result["checks"].append(
            {"name": "flowpilot_skill_is_small_router_launcher", "ok": small_router_launcher}
        )
        if not small_router_launcher:
            result["ok"] = False
        daemon_first_startup = all(
            term in text
            for term in (
                "minimal run shell, current pointer, and run index",
                "starts or attaches the built-in one-second Router daemon",
                "daemon then schedules startup UI, role startup, heartbeat, and Controller-core handoff rows",
                "same two-table rule as later runtime work",
                "current startup-scope rows, receipts, required postconditions",
            )
        )
        result["checks"].append(
            {"name": "flowpilot_skill_daemon_first_startup_guidance", "ok": daemon_first_startup}
        )
        if not daemon_first_startup:
            result["ok"] = False

    try:
        dependencies = json.loads((ROOT / "flowpilot.dependencies.json").read_text(encoding="utf-8"))
        by_name = {item.get("name"): item for item in dependencies.get("dependencies", [])}
        bootstrap_ok = (
            by_name.get("flowguard", {}).get("required") is True
            and by_name.get("flowguard", {}).get("source", {}).get("kind") == "github_python_package"
            and by_name.get("flowguard", {}).get("install", {}).get("requires_explicit_flag")
            == "--install-flowguard"
            and by_name.get("model-first-function-flow", {}).get("required") is True
            and by_name.get("grill-me", {}).get("required") is True
            and "Dependency Bootstrap" in (ROOT / "skills/flowpilot/SKILL.md").read_text(encoding="utf-8")
            and (ROOT / "skills/flowpilot/DEPENDENCIES.md").exists()
        )
        result["checks"].append(
            {"name": "flowpilot_dependency_bootstrap_contract", "ok": bootstrap_ok}
        )
        if not bootstrap_ok:
            result["ok"] = False
    except Exception as exc:  # pragma: no cover - diagnostic script
        result["ok"] = False
        result["checks"].append(
            {"name": "flowpilot_dependency_bootstrap_contract", "ok": False, "error": repr(exc)}
        )

    router_path = ROOT / "skills/flowpilot/assets/flowpilot_router.py"
    runtime_mode_template = ROOT / "templates/flowpilot/mode.template.json"
    router_text = router_path.read_text(encoding="utf-8") if router_path.exists() else ""
    run_modes_retired = (
        not runtime_mode_template.exists()
        and "DEFAULT_RUN_MODE" not in router_text
        and '"run_mode"' not in router_text
        and "'run_mode'" not in router_text
    )
    result["checks"].append(
        {
            "name": "flowpilot_run_modes_retired_from_runtime",
            "ok": run_modes_retired,
            "mode_template_exists": runtime_mode_template.exists(),
        }
    )
    if not run_modes_retired:
        result["ok"] = False

    manifest_path = ROOT / "skills/flowpilot/assets/runtime_kit/manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            cards = manifest.get("cards", [])
            manifest_cards_ok = (
                manifest.get("schema_version") == "flowpilot.prompt_manifest.v1"
                and isinstance(cards, list)
                and bool(cards)
            )
            missing_cards = []
            invalid_cards = []
            invalid_identity_cards = []
            for card in cards if isinstance(cards, list) else []:
                if not isinstance(card, dict):
                    invalid_cards.append("<non-object>")
                    continue
                card_path = card.get("path")
                if (
                    not card.get("id")
                    or card.get("source") != "system"
                    or card.get("issued_by") != "router"
                    or not isinstance(card_path, str)
                ):
                    invalid_cards.append(str(card.get("id") or card_path or "<unknown>"))
                    continue
                full_card_path = manifest_path.parent / card_path
                if not full_card_path.exists():
                    missing_cards.append(card_path)
                else:
                    card_text = full_card_path.read_text(encoding="utf-8")
                    expected_role = str(card.get("audience") or "")
                    identity_ok = (
                        card_text.lstrip().startswith("<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1")
                        and f"recipient_role: {expected_role}" in card_text
                        and "recipient_identity:" in card_text
                        and "allowed_scope:" in card_text
                        and "forbidden_scope:" in card_text
                        and "required_return:" in card_text
                        and "controller-visible envelope" in card_text
                        and "Do not include report bodies" in card_text
                        and "next_step_source:" in card_text
                        and "flowpilot_router.py" in card_text
                        and "runtime_context:" in card_text
                        and "router delivery envelope" in card_text
                        and "do not continue from memory" in card_text
                    )
                    if not identity_ok:
                        invalid_identity_cards.append(str(card.get("id") or card_path))
            card_ids = [
                str(card.get("id"))
                for card in cards
                if isinstance(card, dict) and card.get("id")
            ] if isinstance(cards, list) else []
            duplicate_card_ids = sorted(
                {card_id for card_id in card_ids if card_ids.count(card_id) > 1}
            )
            policy = manifest.get("controller_policy") if isinstance(manifest, dict) else {}
            controller_policy_ok = isinstance(policy, dict) and all(
                policy.get(key) is expected
                for key, expected in {
                    "all_system_cards_from_system": True,
                    "card_delivery_requires_manifest_check": True,
                    "mail_delivery_requires_packet_ledger_check": True,
                    "controller_may_create_project_evidence": False,
                    "controller_may_read_sealed_bodies": False,
                }.items()
            )
            manifest_cards_ok = manifest_cards_ok and not duplicate_card_ids and controller_policy_ok
            manifest_cards_ok = manifest_cards_ok and not missing_cards and not invalid_cards and not invalid_identity_cards
            result["checks"].append(
                {
                    "name": "flowpilot_prompt_manifest_cards_valid",
                    "ok": manifest_cards_ok,
                    "card_count": len(cards) if isinstance(cards, list) else 0,
                    "missing_cards": missing_cards,
                    "invalid_cards": invalid_cards,
                    "invalid_identity_cards": invalid_identity_cards,
                    "duplicate_card_ids": duplicate_card_ids,
                    "controller_policy_ok": controller_policy_ok,
                }
            )
            if not manifest_cards_ok:
                result["ok"] = False
        except Exception as exc:  # pragma: no cover - diagnostic script
            result["ok"] = False
            result["checks"].append(
                {
                    "name": "flowpilot_prompt_manifest_cards_valid",
                    "ok": False,
                    "error": repr(exc),
                }
            )

    try:
        controller_card = ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/controller.md"
        text = controller_card.read_text(encoding="utf-8")
        required_terms = [
            "active health-and-continuation aid",
            "current_wait.wait_class",
            "ack",
            "three-minute reminder",
            "ten-minute blocker",
            "report_result",
            "fresh liveness check",
            "Do not trust an old \"alive\" status",
            "controller_local_action",
            "do not remind yourself",
            "controller_table_prompt",
            "top to bottom",
            "as long as FlowPilot is still running",
            "continuous_controller_standby",
            "active foreground duty",
            "sync the visible Codex plan",
            "finishable checklist item",
            "daemon-owned startup rows",
            "Router's scheduler ledger owns ordering",
            "return to top-to-bottom row processing",
            "must not mark the visible plan item done",
            "timeout_still_waiting",
            "diagnostic-only",
            "translating control-plane state",
            "Keep internal Router, action, ledger, packet, ACK, scheduler, receipt, hash",
            "concrete blocker cannot be explained accurately",
        ]
        missing_terms = [term for term in required_terms if term not in text]
        ok = not missing_terms
        result["checks"].append(
            {
                "name": "flowpilot_controller_wait_target_prompt_guidance",
                "ok": ok,
                "missing_terms": missing_terms,
            }
        )
        if not ok:
            result["ok"] = False
    except Exception as exc:  # pragma: no cover - diagnostic script
        result["ok"] = False
        result["checks"].append(
            {
                "name": "flowpilot_controller_wait_target_prompt_guidance",
                "ok": False,
                "error": repr(exc),
            }
        )

    try:
        router_source = (ROOT / "skills/flowpilot/assets/flowpilot_router.py").read_text(encoding="utf-8")
        required_terms = [
            "controller_table_prompt",
            "Work from top to bottom",
            "As long as FlowPilot is still running",
            "continuous monitoring duty",
            "finishable checklist item",
            "update this table",
            "return to top-to-bottom row processing",
            "foreground_close_allowed_while_flowpilot_running",
            "new_controller_work_requires_ledger_update_and_top_down_reentry",
            "startup_daemon_scheduled",
            "scheduled_by_router_daemon",
            "startup_daemon_controls_bootstrap",
            "translate internal action,",
            "ledger, receipt, packet, wait, daemon, ACK, and scheduler terms",
            "plain language first. Use internal names only when the user asks for",
            "concrete blocker needs that name",
        ]
        missing_terms = [term for term in required_terms if term not in router_source]
        ok = not missing_terms
        result["checks"].append(
            {
                "name": "flowpilot_controller_table_prompt_runtime_guidance",
                "ok": ok,
                "missing_terms": missing_terms,
            }
        )
        if not ok:
            result["ok"] = False
    except Exception as exc:  # pragma: no cover - diagnostic script
        result["ok"] = False
        result["checks"].append(
            {
                "name": "flowpilot_controller_table_prompt_runtime_guidance",
                "ok": False,
                "error": repr(exc),
            }
        )

    try:
        import check_runtime_card_capability_reminders

        reminder_check = check_runtime_card_capability_reminders.check(ROOT)
        reminders_ok = bool(reminder_check.get("ok"))
        result["checks"].append(
            {
                "name": "flowpilot_runtime_card_capability_reminders",
                "ok": reminders_ok,
                "checked_cards": reminder_check.get("checked_cards"),
                "issue_count": reminder_check.get("issue_count"),
                "issues": reminder_check.get("issues"),
            }
        )
        if not reminders_ok:
            result["ok"] = False
    except Exception as exc:  # pragma: no cover - diagnostic script
        result["ok"] = False
        result["checks"].append(
            {
                "name": "flowpilot_runtime_card_capability_reminders",
                "ok": False,
                "error": repr(exc),
            }
        )

    assets_path = ROOT / "skills" / "flowpilot" / "assets"
    if assets_path.exists():
        sys.path.insert(0, str(assets_path))
        scripts_path = ROOT / "scripts"
        sys.path.insert(0, str(scripts_path))
        try:
            flowpilot_router = importlib.import_module("flowpilot_router")
            packet_runtime = importlib.import_module("packet_runtime")
            role_output_runtime = importlib.import_module("role_output_runtime")
            flowpilot_runtime = importlib.import_module("flowpilot_runtime")
            schema_match = (
                getattr(flowpilot_router, "PACKET_LEDGER_SCHEMA", None)
                == getattr(packet_runtime, "PACKET_LEDGER_SCHEMA", None)
            )
            result["checks"].append(
                {
                    "name": "flowpilot_router_packet_schema_matches_runtime",
                    "ok": schema_match,
                    "router_schema": getattr(flowpilot_router, "PACKET_LEDGER_SCHEMA", None),
                    "packet_runtime_schema": getattr(packet_runtime, "PACKET_LEDGER_SCHEMA", None),
                }
            )
            if not schema_match:
                result["ok"] = False
            role_output_runtime_ok = bool(
                getattr(role_output_runtime, "ROLE_OUTPUT_RUNTIME_SCHEMA", None)
                and "pm_resume_recovery_decision" in getattr(role_output_runtime, "SUPPORTED_OUTPUT_TYPES", set())
                and "pm_startup_activation_approval" in getattr(role_output_runtime, "SUPPORTED_OUTPUT_TYPES", set())
                and "pm_startup_repair_request" in getattr(role_output_runtime, "SUPPORTED_OUTPUT_TYPES", set())
                and "pm_startup_protocol_dead_end" in getattr(role_output_runtime, "SUPPORTED_OUTPUT_TYPES", set())
                and "gate_decision" in getattr(role_output_runtime, "SUPPORTED_OUTPUT_TYPES", set())
                and hasattr(role_output_runtime, "quality_pack_checks_for_run")
            )
            result["checks"].append(
                {
                    "name": "flowpilot_role_output_runtime_available",
                    "ok": role_output_runtime_ok,
                    "runtime_schema": getattr(role_output_runtime, "ROLE_OUTPUT_RUNTIME_SCHEMA", None),
                    "supported_output_types": sorted(getattr(role_output_runtime, "SUPPORTED_OUTPUT_TYPES", set())),
                }
            )
            if not role_output_runtime_ok:
                result["ok"] = False
            role_output_binding_issues = _role_output_runtime_binding_issues(flowpilot_router, role_output_runtime)
            role_output_binding_ok = not role_output_binding_issues
            result["checks"].append(
                {
                    "name": "flowpilot_role_output_runtime_registry_bindings",
                    "ok": role_output_binding_ok,
                    "issue_count": len(role_output_binding_issues),
                    "issues": role_output_binding_issues,
                }
            )
            if not role_output_binding_ok:
                result["ok"] = False
            control_transaction_issues = flowpilot_router._control_transaction_registry_issues()
            control_transaction_ok = not control_transaction_issues
            result["checks"].append(
                {
                    "name": "flowpilot_control_transaction_registry_valid",
                    "ok": control_transaction_ok,
                    "issue_count": len(control_transaction_issues),
                    "issues": control_transaction_issues,
                }
            )
            if not control_transaction_ok:
                result["ok"] = False
            route_action_policy_issues = flowpilot_router._route_action_policy_issues()
            route_action_policy_ok = not route_action_policy_issues
            result["checks"].append(
                {
                    "name": "flowpilot_route_action_policy_registry_valid",
                    "ok": route_action_policy_ok,
                    "issue_count": len(route_action_policy_issues),
                    "issues": route_action_policy_issues,
                }
            )
            if not route_action_policy_ok:
                result["ok"] = False
            cli_cases = [
                ["--root", str(ROOT), "start", "--json"],
                ["--root", str(ROOT), "next", "--json"],
                ["--root", str(ROOT), "run-until-wait", "--new-invocation", "--json"],
                ["--root", str(ROOT), "apply", "--action-type", "load_router", "--json"],
                ["--root", str(ROOT), "record-event", "--event", "pm_first_decision_resets_controller", "--json"],
                ["--root", str(ROOT), "role-output-envelope", "--output-path", "role_outputs/sample.json", "--json"],
                ["--root", str(ROOT), "validate-artifact", "--type", "role_output_envelope", "--path", "role_outputs/sample.json", "--json"],
                ["--root", str(ROOT), "state", "--json"],
            ]
            cli_parse_errors = []
            for case in cli_cases:
                try:
                    flowpilot_router.parse_args(case)
                except BaseException as exc:  # argparse raises SystemExit.
                    cli_parse_errors.append({"case": case, "error": repr(exc)})
            retired_fold_commands = [
                "deliver-card-bundle-checked",
                "relay-checked",
                "prepare-startup-fact-check",
                "record-role-output-checked",
            ]
            unexpected_retired_commands = []
            for command in retired_fold_commands:
                try:
                    with contextlib.redirect_stderr(io.StringIO()):
                        flowpilot_router.parse_args(["--root", str(ROOT), command, "--json"])
                    unexpected_retired_commands.append(command)
                except SystemExit:
                    pass
                except BaseException as exc:
                    unexpected_retired_commands.append(f"{command}: {exc!r}")
            cli_ok = not cli_parse_errors and not unexpected_retired_commands
            result["checks"].append(
                {
                    "name": "flowpilot_router_cli_commands_parse",
                    "ok": cli_ok,
                    "parse_error_count": len(cli_parse_errors),
                    "parse_errors": cli_parse_errors,
                    "unexpected_retired_fold_commands": unexpected_retired_commands,
                }
            )
            if not cli_ok:
                result["ok"] = False
            role_output_cli_cases = [
                [
                    "--root",
                    str(ROOT),
                    "prepare-output",
                    "--output-type",
                    "pm_startup_activation_approval",
                    "--role",
                    "project_manager",
                    "--agent-id",
                    "agent-pm-check",
                ],
                [
                    "--root",
                    str(ROOT),
                    "submit-output",
                    "--output-type",
                    "gate_decision",
                    "--role",
                    "human_like_reviewer",
                    "--agent-id",
                    "agent-reviewer-check",
                    "--body-json",
                    "{}",
                ],
                ["--root", str(ROOT), "verify-envelope", "--envelope-file", "role_outputs/sample.json"],
            ]
            role_output_cli_parse_errors = []
            for case in role_output_cli_cases:
                try:
                    role_output_runtime.parse_args(case)
                except BaseException as exc:
                    role_output_cli_parse_errors.append({"case": case, "error": repr(exc)})
            role_output_cli_ok = not role_output_cli_parse_errors
            result["checks"].append(
                {
                    "name": "flowpilot_role_output_runtime_cli_commands_parse",
                    "ok": role_output_cli_ok,
                    "parse_error_count": len(role_output_cli_parse_errors),
                    "parse_errors": role_output_cli_parse_errors,
                }
            )
            if not role_output_cli_ok:
                result["ok"] = False
            unified_cli_cases = [
                [
                    "--root",
                    str(ROOT),
                    "prepare-output",
                    "--output-type",
                    "pm_startup_activation_approval",
                    "--role",
                    "project_manager",
                    "--agent-id",
                    "agent-pm-check",
                ],
                [
                    "--root",
                    str(ROOT),
                    "open-packet",
                    "--envelope-path",
                    ".flowpilot/runs/run-test/packets/packet-001/packet_envelope.json",
                    "--role",
                    "worker_a",
                    "--agent-id",
                    "agent-worker-check",
                ],
                [
                    "--root",
                    str(ROOT),
                    "receive-card",
                    "--envelope-path",
                    ".flowpilot/runs/run-test/mailbox/system_cards/card.json",
                    "--role",
                    "human_like_reviewer",
                    "--agent-id",
                    "agent-reviewer-check",
                ],
                [
                    "--root",
                    str(ROOT),
                    "receive-card-bundle",
                    "--envelope-path",
                    ".flowpilot/runs/run-test/mailbox/system_card_bundles/cards.json",
                    "--role",
                    "project_manager",
                    "--agent-id",
                    "agent-pm-check",
                ],
                [
                    "--root",
                    str(ROOT),
                    "submit-output",
                    "--output-type",
                    "gate_decision",
                    "--role",
                    "human_like_reviewer",
                    "--agent-id",
                    "agent-reviewer-check",
                    "--body-json",
                    "{}",
                ],
                [
                    "--root",
                    str(ROOT),
                    "submit-output-to-router",
                    "--output-type",
                    "gate_decision",
                    "--role",
                    "human_like_reviewer",
                    "--agent-id",
                    "agent-reviewer-check",
                    "--body-json",
                    "{}",
                ],
            ]
            unified_cli_parse_errors = []
            for case in unified_cli_cases:
                try:
                    flowpilot_runtime.parse_args(case)
                except BaseException as exc:
                    unified_cli_parse_errors.append({"case": case, "error": repr(exc)})
            unified_cli_ok = not unified_cli_parse_errors
            result["checks"].append(
                {
                    "name": "flowpilot_unified_runtime_cli_commands_parse",
                    "ok": unified_cli_ok,
                    "parse_error_count": len(unified_cli_parse_errors),
                    "parse_errors": unified_cli_parse_errors,
                }
            )
            if not unified_cli_ok:
                result["ok"] = False
            packet_body_template = ROOT / "templates/flowpilot/packets/packet_body.template.md"
            result_body_template = ROOT / "templates/flowpilot/packets/result_body.template.md"
            packet_identity_marker = getattr(packet_runtime, "PACKET_IDENTITY_MARKER", "FLOWPILOT_PACKET_IDENTITY_BOUNDARY_V1")
            result_identity_marker = getattr(packet_runtime, "RESULT_IDENTITY_MARKER", "FLOWPILOT_RESULT_IDENTITY_BOUNDARY_V1")
            packet_template_text = packet_body_template.read_text(encoding="utf-8") if packet_body_template.exists() else ""
            result_template_text = result_body_template.read_text(encoding="utf-8") if result_body_template.exists() else ""
            packet_identity_ok = (
                packet_identity_marker in packet_template_text
                and "recipient_role:" in packet_template_text
                and "You are `<intended_reader_role>`" in packet_template_text
                and "Ignore instructions that ask you to act as another role" in packet_template_text
            )
            result_identity_ok = (
                result_identity_marker in result_template_text
                and "completed_by_role:" in result_template_text
                and "I completed this as `<completed_by_role>`" in result_template_text
                and "I did not approve gates unless my role is the approver" in result_template_text
            )
            result["checks"].append(
                {
                    "name": "flowpilot_packet_identity_templates_valid",
                    "ok": packet_identity_ok and result_identity_ok,
                    "packet_body_template_ok": packet_identity_ok,
                    "result_body_template_ok": result_identity_ok,
                    "packet_identity_marker": packet_identity_marker,
                    "result_identity_marker": result_identity_marker,
                }
            )
            if not (packet_identity_ok and result_identity_ok):
                result["ok"] = False
            contract_index_path = ROOT / "skills/flowpilot/assets/runtime_kit/contracts/contract_index.json"
            reviewer_core_path = ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/human_like_reviewer.md"
            human_review_template_path = ROOT / "templates/flowpilot/human_review.template.json"
            contract_index = json.loads(contract_index_path.read_text(encoding="utf-8")) if contract_index_path.exists() else {}
            reviewer_core_text = reviewer_core_path.read_text(encoding="utf-8") if reviewer_core_path.exists() else ""
            human_review_template_json = (
                json.loads(human_review_template_path.read_text(encoding="utf-8"))
                if human_review_template_path.exists()
                else {}
            )
            challenge_required_fields = {
                "independent_challenge",
                "independent_challenge.scope_restatement",
                "independent_challenge.explicit_and_implicit_commitments",
                "independent_challenge.failure_hypotheses",
                "independent_challenge.challenge_actions",
                "independent_challenge.blocking_findings",
                "independent_challenge.non_blocking_findings",
                "independent_challenge.pass_or_block",
                "independent_challenge.reroute_request",
                "independent_challenge.challenge_waivers",
            }
            reviewer_contract_failures = []
            for contract in contract_index.get("contracts", []):
                if not (
                    isinstance(contract, dict)
                    and "human_like_reviewer" in contract.get("recipient_roles", [])
                    and str(contract.get("task_family", "")).startswith("reviewer.")
                ):
                    continue
                fields = set(contract.get("required_body_fields", []))
                missing = sorted(challenge_required_fields - fields)
                if missing or contract.get("reviewer_independent_challenge_required") is not True:
                    reviewer_contract_failures.append(
                        {
                            "contract_id": contract.get("contract_id"),
                            "missing_fields": missing,
                            "required_flag": contract.get("reviewer_independent_challenge_required"),
                        }
                    )
            active_challenge_ok = (
                not reviewer_contract_failures
                and "Reviewer Independent Challenge Gate" in reviewer_core_text
                and "PM review package is the minimum checklist" in reviewer_core_text
                and isinstance(human_review_template_json.get("independent_challenge"), dict)
                and "challenge_actions" in human_review_template_json.get("independent_challenge", {})
                and "Reviewer Independent Challenge Context" in packet_template_text
            )
            result["checks"].append(
                {
                    "name": "flowpilot_reviewer_independent_challenge_contract_valid",
                    "ok": active_challenge_ok,
                    "reviewer_contract_failures": reviewer_contract_failures,
                }
            )
            if not active_challenge_ok:
                result["ok"] = False
            user_perspective_card_markers = {
                "skills/flowpilot/assets/runtime_kit/cards/roles/human_like_reviewer.md": [
                    "final-user intent",
                    "product usefulness",
                    "Existence evidence is not enough",
                    "low-quality success",
                    "proof of depth",
                    "Existence-only evidence",
                ],
                "skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md": [
                    "final-user intent and product usefulness self-check",
                    "decision-support",
                ],
                "skills/flowpilot/assets/runtime_kit/cards/reviewer/worker_result_review.md": [
                    "final-user usefulness",
                    "file existence",
                    "Low-Quality Success Guard",
                    "Proof of Depth",
                ],
                "skills/flowpilot/assets/runtime_kit/cards/reviewer/parent_backward_replay.md": [
                    "parent-level user-facing outcome",
                    "proof of depth",
                ],
                "skills/flowpilot/assets/runtime_kit/cards/reviewer/final_backward_replay.md": [
                    "not merely a clean ledger",
                    "hard user-intent failures",
                    "low-quality-success risk",
                ],
                "skills/flowpilot/assets/runtime_kit/cards/reviewer/evidence_quality_review.md": [
                    "user-facing quality",
                    "file existence",
                    "low-quality-success hard parts",
                ],
                "skills/flowpilot/assets/runtime_kit/cards/reviewer/product_architecture_challenge.md": [
                    "final product usefulness",
                    "PM decision-support",
                    "`low_quality_success_review`",
                ],
                "skills/flowpilot/assets/runtime_kit/cards/reviewer/node_acceptance_plan_review.md": [
                    "final-user usefulness",
                    "evidence",
                    "low-quality-success mapping",
                ],
                "skills/flowpilot/assets/runtime_kit/cards/phases/pm_product_architecture.md": [
                    "final-user intent and product usefulness assumptions",
                    "low-quality-success review",
                    "proof of depth",
                ],
                "skills/flowpilot/assets/runtime_kit/cards/phases/pm_node_acceptance_plan.md": [
                    "final-user intent and product usefulness self-check",
                    "nonessential improvement",
                    "low-quality-success self-check",
                    "proof of depth",
                ],
                "skills/flowpilot/assets/runtime_kit/cards/phases/pm_route_skeleton.md": [
                    "PM user-intent self-check",
                    "product usefulness failures",
                    "PM low-quality-success ownership check",
                    "unjustified route bloat",
                ],
                "skills/flowpilot/assets/runtime_kit/cards/phases/pm_current_node_loop.md": [
                    "low-quality-success warning",
                    "proof of depth",
                ],
                "skills/flowpilot/assets/runtime_kit/cards/phases/pm_final_ledger.md": [
                    "final-user intent and delivered-product usefulness claims",
                    "low-quality-success risks",
                ],
                "skills/flowpilot/assets/runtime_kit/cards/phases/pm_closure.md": [
                    "final_user_outcome_replay",
                    "unverifiable user-facing quality claim",
                    "hard low-quality-success risks",
                ],
                "templates/flowpilot/product_function_architecture.template.json": [
                    "low_quality_success_review",
                    "proof_of_depth_required",
                ],
                "templates/flowpilot/node_acceptance_plan.template.json": [
                    "local_low_quality_success_risk",
                    "proof_of_depth_required",
                ],
                "templates/flowpilot/packets/packet_body.template.md": [
                    "Low-Quality Success Guard",
                    "proof_of_depth_required",
                ],
                "templates/flowpilot/packets/result_body.template.md": [
                    "Proof of Depth",
                    "existence-only",
                ],
                "templates/flowpilot/final_route_wide_gate_ledger.template.json": [
                    "low_quality_success_risk_dispositions",
                ],
            }
            user_perspective_failures = []
            for relative_path, markers in user_perspective_card_markers.items():
                card_path = ROOT / relative_path
                text = card_path.read_text(encoding="utf-8") if card_path.exists() else ""
                missing = [marker for marker in markers if marker not in text]
                if missing or not card_path.exists():
                    user_perspective_failures.append(
                        {
                            "path": relative_path,
                            "missing_file": not card_path.exists(),
                            "missing_markers": missing,
                        }
                    )
            user_perspective_ok = not user_perspective_failures
            result["checks"].append(
                {
                    "name": "flowpilot_user_perspective_card_propagation_valid",
                    "ok": user_perspective_ok,
                    "failures": user_perspective_failures,
                }
            )
            if not user_perspective_ok:
                result["ok"] = False
        except Exception as exc:  # pragma: no cover - diagnostic script
            result["ok"] = False
            result["checks"].append(
                {
                    "name": "flowpilot_router_packet_schema_matches_runtime",
                    "ok": False,
                    "error": repr(exc),
                }
            )

    equivalence_path = ROOT / "docs/legacy_to_router_equivalence.json"
    if equivalence_path.exists():
        try:
            equivalence = json.loads(equivalence_path.read_text(encoding="utf-8"))
            required = equivalence.get("required_legacy_obligations")
            entries = equivalence.get("entries")
            valid_statuses = set(equivalence.get("status_values", []))
            entry_ids = {
                entry.get("id")
                for entry in entries
                if isinstance(entry, dict) and isinstance(entry.get("id"), str)
            } if isinstance(entries, list) else set()
            missing_entries = [
                item
                for item in required
                if isinstance(item, str) and item not in entry_ids
            ] if isinstance(required, list) else []
            invalid_status_entries = [
                str(entry.get("id") or "<unknown>")
                for entry in entries
                if isinstance(entry, dict) and entry.get("status") not in valid_statuses
            ] if isinstance(entries, list) else ["<entries-not-list>"]
            equivalence_ok = (
                equivalence.get("schema_version") == "flowpilot.legacy_to_router_equivalence.v1"
                and isinstance(required, list)
                and bool(required)
                and isinstance(entries, list)
                and len(entries) >= len(required)
                and not missing_entries
                and not invalid_status_entries
            )
            result["checks"].append(
                {
                    "name": "flowpilot_legacy_to_router_equivalence_valid",
                    "ok": equivalence_ok,
                    "required_count": len(required) if isinstance(required, list) else 0,
                    "entry_count": len(entries) if isinstance(entries, list) else 0,
                    "missing_entries": missing_entries,
                    "invalid_status_entries": invalid_status_entries,
                }
            )
            if not equivalence_ok:
                result["ok"] = False
        except Exception as exc:  # pragma: no cover - diagnostic script
            result["ok"] = False
            result["checks"].append(
                {
                    "name": "flowpilot_legacy_to_router_equivalence_valid",
                    "ok": False,
                    "error": repr(exc),
                }
            )

    barrier_results_path = ROOT / "simulations/barrier_equivalence_results.json"
    if barrier_results_path.exists():
        try:
            barrier_results = json.loads(barrier_results_path.read_text(encoding="utf-8"))
            safe_graph = barrier_results.get("safe_graph")
            hazard_checks = barrier_results.get("hazard_checks")
            explorer = barrier_results.get("flowguard_explorer")
            barrier_ok = (
                barrier_results.get("ok") is True
                and isinstance(safe_graph, dict)
                and safe_graph.get("missing_obligations_at_completion") == []
                and isinstance(hazard_checks, dict)
                and hazard_checks.get("ok") is True
                and isinstance(explorer, dict)
                and explorer.get("ok") is True
            )
            result["checks"].append(
                {
                    "name": "flowpilot_barrier_equivalence_results_valid",
                    "ok": barrier_ok,
                    "barrier_count": safe_graph.get("barrier_count") if isinstance(safe_graph, dict) else 0,
                    "legacy_obligation_count": safe_graph.get("legacy_obligation_count") if isinstance(safe_graph, dict) else 0,
                }
            )
            if not barrier_ok:
                result["ok"] = False
        except Exception as exc:  # pragma: no cover - diagnostic script
            result["ok"] = False
            result["checks"].append(
                {
                    "name": "flowpilot_barrier_equivalence_results_valid",
                    "ok": False,
                    "error": repr(exc),
                }
            )

    matrix_path = ROOT / "docs/legacy_prompt_to_cards_matrix.json"
    if matrix_path.exists():
        try:
            matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
            entries = matrix.get("entries")
            decisions = set(matrix.get("decision_values", []))
            coverages = set(matrix.get("coverage_values", []))
            entry_ids = [
                str(entry.get("id"))
                for entry in entries
                if isinstance(entry, dict) and entry.get("id")
            ] if isinstance(entries, list) else []
            duplicate_entry_ids = sorted(
                {entry_id for entry_id in entry_ids if entry_ids.count(entry_id) > 1}
            )
            invalid_decision_entries = [
                str(entry.get("id") or "<unknown>")
                for entry in entries
                if isinstance(entry, dict) and entry.get("new_architecture_decision") not in decisions
            ] if isinstance(entries, list) else ["<entries-not-list>"]
            invalid_coverage_entries = [
                str(entry.get("id") or "<unknown>")
                for entry in entries
                if isinstance(entry, dict) and entry.get("current_coverage") not in coverages
            ] if isinstance(entries, list) else ["<entries-not-list>"]
            legacy_prompt_path = ROOT / str(matrix.get("source_prompt", ""))
            legacy_sections = []
            if legacy_prompt_path.exists():
                legacy_sections = [
                    line[3:].strip()
                    for line in legacy_prompt_path.read_text(encoding="utf-8").splitlines()
                    if line.startswith("## ")
                ]
            matrix_sections = {
                str(entry.get("legacy_section"))
                for entry in entries
                if isinstance(entry, dict) and entry.get("legacy_section")
            } if isinstance(entries, list) else set()
            missing_legacy_sections = [
                section for section in legacy_sections if section not in matrix_sections
            ]
            startup_reduction = matrix.get("startup_hard_gate_reduction")
            startup_reduction_ok = isinstance(startup_reduction, dict) and all(
                isinstance(startup_reduction.get(key), list) and startup_reduction.get(key)
                for key in (
                    "keep_as_hard_checks",
                    "downgrade_to_router_invariants",
                    "defer_until_surface_exists",
                    "retire_as_old_architecture_guard",
                )
            )
            matrix_ok = (
                matrix.get("schema_version") == "flowpilot.legacy_prompt_to_cards_matrix.v1"
                and isinstance(entries, list)
                and bool(entries)
                and not duplicate_entry_ids
                and not invalid_decision_entries
                and not invalid_coverage_entries
                and not missing_legacy_sections
                and startup_reduction_ok
            )
            result["checks"].append(
                {
                    "name": "flowpilot_legacy_prompt_to_cards_matrix_valid",
                    "ok": matrix_ok,
                    "entry_count": len(entries) if isinstance(entries, list) else 0,
                    "legacy_section_count": len(legacy_sections),
                    "missing_legacy_sections": missing_legacy_sections,
                    "duplicate_entry_ids": duplicate_entry_ids,
                    "invalid_decision_entries": invalid_decision_entries,
                    "invalid_coverage_entries": invalid_coverage_entries,
                    "startup_reduction_ok": startup_reduction_ok,
                }
            )
            if not matrix_ok:
                result["ok"] = False
        except Exception as exc:  # pragma: no cover - diagnostic script
            result["ok"] = False
            result["checks"].append(
                {
                    "name": "flowpilot_legacy_prompt_to_cards_matrix_valid",
                    "ok": False,
                    "error": repr(exc),
                }
            )

    autonomous_skill_path = ROOT / "skills/autonomous-concept-ui-redesign/SKILL.md"
    if autonomous_skill_path.exists():
        text = autonomous_skill_path.read_text(encoding="utf-8")
        has_name = "\nname: autonomous-concept-ui-redesign\n" in f"\n{text}"
        result["checks"].append(
            {"name": "skill_name:autonomous-concept-ui-redesign", "ok": has_name}
        )
        if not has_name:
            result["ok"] = False

    legacy_skill_dir = ROOT / "skills/flowguard-project-autopilot"
    legacy_absent = not legacy_skill_dir.exists()
    result["checks"].append(
        {"name": "legacy_skill_dir_absent", "ok": legacy_absent}
    )
    if not legacy_absent:
        result["ok"] = False

    for relpath in RETIRED_PATHS:
        absent = not (ROOT / relpath).exists()
        result["checks"].append({"name": f"retired_path_absent:{relpath}", "ok": absent})
        if not absent:
            result["ok"] = False

    backup_root = ROOT / "backups"
    second_backup_manifests = []
    if backup_root.exists():
        for manifest_path in backup_root.glob("flowpilot-20260504-second-backup-*/BACKUP_MANIFEST.json"):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            label = str(manifest.get("label", ""))
            if "SECOND BACKUP" in label and "do not delete" in label.lower():
                zip_path = manifest_path.parent.with_suffix(".zip")
                second_backup_manifests.append(
                    {
                        "manifest": str(manifest_path.relative_to(ROOT)),
                        "zip": str(zip_path.relative_to(ROOT)),
                        "zip_exists": zip_path.exists(),
                    }
                )
    second_backup_ok = bool(second_backup_manifests) and all(item["zip_exists"] for item in second_backup_manifests)
    result["checks"].append(
        {
            "name": "flowpilot_second_backup_preserved",
            "ok": second_backup_ok,
            "backups": second_backup_manifests,
        }
    )
    if not second_backup_ok:
        result["ok"] = False

    for relpath in JSON_FILES:
        path = ROOT / relpath
        try:
            json.loads(path.read_text(encoding="utf-8"))
            json_ok = True
            error = None
        except Exception as exc:  # pragma: no cover - diagnostic script
            json_ok = False
            error = repr(exc)
        check = {"name": f"json:{relpath}", "ok": json_ok}
        if error:
            check["error"] = error
        result["checks"].append(check)
        if not json_ok:
            result["ok"] = False

    for relpath in OPTIONAL_RUNTIME_JSON_FILES:
        path = ROOT / relpath
        if not path.exists():
            result["checks"].append(
                {"name": f"optional_json:{relpath}", "ok": True, "present": False}
            )
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
            json_ok = True
            error = None
        except Exception as exc:  # pragma: no cover - diagnostic script
            json_ok = False
            error = repr(exc)
        check = {"name": f"optional_json:{relpath}", "ok": json_ok, "present": True}
        if error:
            check["error"] = error
        result["checks"].append(check)
        if not json_ok:
            result["ok"] = False

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
