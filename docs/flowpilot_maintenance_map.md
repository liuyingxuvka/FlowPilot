# FlowPilot Maintenance Map

This generated map records the current model-code-test maintenance surface for FlowPilot.

## Summary

- Runtime asset files: 344
- Runtime owner modules: 267
- Script files: 36
- Model files: 259
- Test files: 82
- Model-test-code diagnostic: full coverage=False, gaps=13, covered=717

## Runtime Owner Modules

Threshold: 450 lines.
- `skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_packet_folds.py`: 582 lines over-threshold
- `skills/flowpilot/assets/flowpilot_router_role_output_bridge.py`: 574 lines over-threshold
- `skills/flowpilot/assets/flowpilot_router_runtime_state.py`: 539 lines over-threshold
- `skills/flowpilot/assets/flowpilot_router_protocol_external_event_data.py`: 503 lines over-threshold
- `skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_scheduled.py`: 490 lines over-threshold
- `skills/flowpilot/assets/flowpilot_router_startup_intake_materialization.py`: 453 lines over-threshold

Largest runtime owner modules:

- `skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_packet_folds.py`: 582 lines over-threshold
- `skills/flowpilot/assets/flowpilot_router_role_output_bridge.py`: 574 lines over-threshold
- `skills/flowpilot/assets/flowpilot_router_runtime_state.py`: 539 lines over-threshold
- `skills/flowpilot/assets/flowpilot_router_protocol_external_event_data.py`: 503 lines over-threshold
- `skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_scheduled.py`: 490 lines over-threshold
- `skills/flowpilot/assets/flowpilot_router_startup_intake_materialization.py`: 453 lines over-threshold
- `skills/flowpilot/assets/flowpilot_router_daemon_runtime.py`: 431 lines
- `skills/flowpilot/assets/flowpilot_router_controller_repair_schedule.py`: 428 lines
- `skills/flowpilot/assets/flowpilot_router_action_handlers_basic.py`: 427 lines
- `skills/flowpilot/assets/flowpilot_router_controller_runtime.py`: 406 lines

## Facades

Runtime facades:
- `skills/flowpilot/assets/flowpilot_router.py`: 112 lines
- `skills/flowpilot/assets/flowpilot_paths.py`: 124 lines
- `skills/flowpilot/assets/flowpilot_runtime.py`: 29 lines

Model facades and parent models:
- `simulations/capability_model.py`: 4482 lines over-threshold
- `simulations/meta_model.py`: 3417 lines over-threshold
- `simulations/flowpilot_structure_maintenance_model.py`: 470 lines
- `simulations/flowpilot_router_facade_split_model.py`: 838 lines
- `simulations/flowpilot_model_test_alignment_source_contracts.py`: 71 lines

## Script Entrypoints

- `scripts/check_install.py`: 9 lines
- `scripts/install_flowpilot.py`: 623 lines over-threshold
- `scripts/run_test_tier.py`: 468 lines over-threshold
- `scripts/smoke_autopilot.py`: 143 lines
- `scripts/audit_local_install_sync.py`: 191 lines
- `scripts/run_flowguard_coverage_sweep.py`: 372 lines
- `scripts/flowpilot_maintenance_map.py`: 276 lines

## Large-File Pressure

### simulations
- `simulations/capability_model.py`: 4482 lines over-threshold
- `simulations/meta_model.py`: 3417 lines over-threshold
- `simulations/flowpilot_control_plane_friction_model_audit.py`: 1930 lines over-threshold
- `simulations/flowpilot_resume_model.py`: 1683 lines over-threshold

### scripts
- `scripts/install_checks/common.py`: 751 lines over-threshold
- `scripts/install_flowpilot.py`: 623 lines over-threshold
- `scripts/flowpilot_defects.py`: 590 lines over-threshold
- `scripts/install_checks/runtime.py`: 550 lines over-threshold
- `scripts/run_test_tier.py`: 468 lines over-threshold

### tests
- `tests/router_runtime/common.py`: 2442 lines over-threshold
- `tests/router_runtime/startup_bootstrap.py`: 2274 lines over-threshold
- `tests/router_runtime/foreground_controller.py`: 1894 lines over-threshold
- `tests/test_flowpilot_full_diagnostic_contracts.py`: 1563 lines over-threshold
- `tests/test_flowpilot_packet_runtime.py`: 1092 lines over-threshold
- `tests/router_runtime/quality_gates.py`: 1007 lines over-threshold
- `tests/router_runtime/packets.py`: 987 lines over-threshold
- `tests/router_runtime/material_modeling.py`: 936 lines over-threshold

## Test Tiers

- `collect`: 1 commands, 0 long-running, 0 release-only
- `fast`: 11 commands, 0 long-running, 0 release-only
- `router-startup`: 8 commands, 0 long-running, 0 release-only
- `router-foreground`: 10 commands, 0 long-running, 0 release-only
- `router-packets`: 9 commands, 0 long-running, 0 release-only
- `router-route`: 11 commands, 0 long-running, 0 release-only
- `router-pm-role-work`: 3 commands, 0 long-running, 0 release-only
- `router-quality-gates`: 5 commands, 0 long-running, 0 release-only
- `router-material-modeling`: 3 commands, 0 long-running, 0 release-only
- `router-terminal`: 25 commands, 0 long-running, 0 release-only
- `router`: 64 commands, 0 long-running, 0 release-only
- `integration`: 4 commands, 2 long-running, 0 release-only
- `release`: 4 commands, 3 long-running, 3 release-only
- `legacy-full`: 2 commands, 2 long-running, 2 release-only
- `all`: 80 commands, 2 long-running, 0 release-only

## Split Rules

Current decisions:
- Runtime owner modules currently have 6 files over the StructureMesh line threshold; defer further runtime splitting unless a matching model block and external contract test justify it.
- Test-tier command definitions are split into stable command-group modules while scripts/test_tier/definitions.py remains the compatibility facade.
- Router facade split, structure-maintenance, and source-contract alignment models keep their old import paths while large catalogs move into helper modules.
- Large router-runtime tests stay as watchlist items in this pass; split them only by externally visible contract family and after fixture ownership is clear.
- Remaining large install and defect scripts stay as watchlist items because they are behavior-bearing command surfaces, not pure catalog moves.

Future rules:
- Split runtime only when a model block, public facade, and external contract test already agree.
- Prefer catalog/data extraction for oversized model files; keep old model imports as facades.
- Split scripts only around stable command groups or install-check manifests; preserve CLI behavior.
- Split tests by externally visible contract family before moving internal fixtures.
