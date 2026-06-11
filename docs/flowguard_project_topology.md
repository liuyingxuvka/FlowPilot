# FlowGuard Project Topology

This generated map gives agents a project-level background structure for FlowGuard-heavy work.
It is orientation only; it is not validation evidence.

## Summary

- Model runners: 142
- Model-test alignment families: 12
- Code surfaces: 942
- Test commands: 350
- Evidence summaries: 5
- Known-bad/risk labels surfaced: 2418

## Area Map

| Area | Models | Alignment families | Code surfaces | Test commands | Known-bad labels |
| --- | ---: | ---: | ---: | ---: | ---: |
| `closure` | 6 | 1 | 16 | 7 | 73 |
| `controller` | 7 | 0 | 87 | 22 | 103 |
| `install-validation` | 1 | 0 | 17 | 16 | 15 |
| `material` | 1 | 0 | 22 | 25 | 11 |
| `model-mesh` | 3 | 0 | 7 | 2 | 73 |
| `model-test-alignment` | 3 | 0 | 12 | 12 | 61 |
| `other` | 81 | 6 | 239 | 40 | 1299 |
| `packet` | 9 | 2 | 170 | 124 | 169 |
| `prompt-card` | 3 | 0 | 4 | 0 | 77 |
| `review` | 3 | 0 | 3 | 0 | 67 |
| `route` | 16 | 2 | 285 | 55 | 304 |
| `startup` | 6 | 1 | 73 | 43 | 129 |
| `structure` | 3 | 0 | 7 | 4 | 37 |

## Evidence Boundaries

Topology guides project understanding only; it does not replace executable FlowGuard checks, tests, conformance replay, install audit, or release evidence.

Agents may use this map to choose which model, test, and code areas to inspect.
Completion and readiness claims still need the owning FlowGuard checks, tests, result artifacts, install audits, and freshness evidence.

## Key Evidence Summaries

| Artifact | Path | OK | Decision | Confidence | Findings |
| --- | --- | --- | --- | --- | ---: |
| `model_test_alignment` | `simulations/flowpilot_model_test_alignment_results.json` | True | `` | `` | 0 |
| `coverage_sweep` | `simulations/flowpilot_full_model_coverage_sweep_results.json` | False | `` | `` | 140 |
| `model_maturation` | `simulations/flowpilot_model_maturation_results.json` | True | `model_maturation_scoped_claim` | `scoped` | None |
| `model_mesh` | `simulations/flowpilot_model_mesh_results.json` | True | `` | `` | None |
| `model_hierarchy` | `simulations/flowpilot_model_hierarchy_results.json` | True | `` | `` | None |

## Model Runner Samples

- `capability` (other, abstract_strong_live_mapping_weaker): `simulations/run_capability_checks.py` -> `simulations/capability_thin_parent_results.json`
- `card_instruction_coverage` (packet, specialized_assertion_or_local_hazard): `simulations/run_card_instruction_coverage_checks.py` -> `simulations/card_instruction_coverage_results.json`; known-bad: hazards, ok, packet_prompt_hazards
- `command_refinement` (other, supporting_model_owned): `simulations/run_command_refinement_checks.py` -> `simulations/flowpilot_command_refinement_results.json`; known-bad: background_collaboration_start_fold, card_bundle_fold, final_replay_fold
- `defect_governance` (other, specialized_assertion_or_local_hazard): `simulations/run_defect_governance_checks.py` -> `simulations/defect_governance_results.json`; known-bad: hazards, ok, blocker_never_logged
- `flowpilot_blocker_repair_information_flow` (other, supporting_model_owned): `simulations/run_flowpilot_blocker_repair_information_flow_checks.py` -> `simulations/flowpilot_blocker_repair_information_flow_results.json`; known-bad: failures, hazards, ok
- `flowpilot_canonical_repair_scope_rotation` (other, supporting_model_owned): `simulations/run_flowpilot_canonical_repair_scope_rotation_checks.py` -> `simulations/flowpilot_canonical_repair_scope_rotation_results.json`; known-bad: expected, hazards, ok
- `flowpilot_card_envelope` (packet, supporting_model_owned): `simulations/run_flowpilot_card_envelope_checks.py` -> `simulations/flowpilot_card_envelope_results.json`; known-bad: hazards, ok, ack_contains_body_content
- `flowpilot_complete_system_alignment` (other, coverage_strong): `simulations/run_flowpilot_complete_system_alignment_checks.py` -> `simulations/flowpilot_complete_system_alignment_results.json`
- `flowpilot_complete_system_development` (other, coverage_strong): `simulations/run_flowpilot_complete_system_development_checks.py` -> `simulations/flowpilot_complete_system_development_results.json`; known-bad: expected, hazards, ok
- `flowpilot_complete_system_historical_replay` (other, coverage_strong): `simulations/run_flowpilot_complete_system_historical_replay_checks.py` -> `simulations/flowpilot_complete_system_historical_replay_results.json`
- `flowpilot_complete_system_live_host_readiness` (other, coverage_strong): `simulations/run_flowpilot_complete_system_live_host_readiness_checks.py` -> `simulations/flowpilot_complete_system_live_host_results.json`
- `flowpilot_complete_system_runtime` (other, coverage_strong): `simulations/run_flowpilot_complete_system_runtime_checks.py` -> `simulations/flowpilot_complete_system_runtime_results.json`
- `flowpilot_complete_system_structure` (structure, coverage_strong): `simulations/run_flowpilot_complete_system_structure_checks.py` -> `simulations/flowpilot_complete_system_structure_results.json`; known-bad: missing_dynamic_host_owner, missing_module_rationale
- `flowpilot_complete_system_testmesh` (other, coverage_strong): `simulations/run_flowpilot_complete_system_testmesh_checks.py` -> `simulations/flowpilot_complete_system_testmesh_results.json`
- `flowpilot_complete_system_ui` (other, coverage_strong): `simulations/run_flowpilot_complete_system_ui_checks.py` -> `simulations/flowpilot_complete_system_ui_results.json`
- `flowpilot_control_plane_friction` (other, coverage_strong): `simulations/run_flowpilot_control_plane_friction_checks.py` -> `simulations/flowpilot_control_plane_friction_results.json`; known-bad: hazards, ok, ack_consumed_semantic_wait_lost
- `flowpilot_control_plane_ledger_consolidation` (closure, supporting_model_owned): `simulations/run_flowpilot_control_plane_ledger_consolidation_checks.py` -> `simulations/flowpilot_control_plane_ledger_consolidation_results.json`; known-bad: failures, hazards, ok
- `flowpilot_control_plane_state_consistency` (other, supporting_model_owned): `simulations/run_flowpilot_control_plane_state_consistency_checks.py` -> `simulations/flowpilot_control_plane_state_consistency_results.json`; known-bad: failures, hazards, ok
- `flowpilot_control_surface_contract` (other, supporting_model_owned): `simulations/run_flowpilot_control_surface_contract_checks.py` -> `simulations/flowpilot_control_surface_contract_results.json`; known-bad: hazards, ok, accepted_result_reassigned_accepted
- `flowpilot_control_transaction_registry` (other, coverage_strong): `simulations/run_flowpilot_control_transaction_registry_checks.py` -> `simulations/flowpilot_control_transaction_registry_results.json`; known-bad: failures, hazards, ok
- `flowpilot_controller_break_glass` (controller, supporting_model_owned): `simulations/run_flowpilot_controller_break_glass_checks.py` -> `simulations/flowpilot_controller_break_glass_results.json`; known-bad: failures, hazards, ok
- `flowpilot_controller_patrol` (controller, supporting_model_owned): `simulations/run_flowpilot_controller_patrol_checks.py` -> `simulations/flowpilot_controller_patrol_results.json`; known-bad: hazards, ok, command_restart_marked_complete
- `flowpilot_controller_process_aside` (controller, supporting_model_owned): `simulations/run_flowpilot_controller_process_aside_checks.py` -> `simulations/flowpilot_controller_process_aside_results.json`; known-bad: failures, hazards, ok
- `flowpilot_controller_receipt_evidence_fold` (controller, supporting_model_owned): `simulations/run_flowpilot_controller_receipt_evidence_fold_checks.py` -> `simulations/flowpilot_controller_receipt_evidence_fold_results.json`; known-bad: failures, hazards, ok
- `flowpilot_controller_wait_receipt_audit` (controller, supporting_model_owned): `simulations/run_flowpilot_controller_wait_receipt_audit_checks.py` -> `simulations/flowpilot_controller_wait_receipt_audit_results.json`; known-bad: failures, hazards, ok

## Alignment Families

- `startup` (startup): 2 obligations, 4 test evidence rows
- `packet/card/ack` (packet): 4 obligations, 7 test evidence rows
- `packet result family` (packet): 13 obligations, 17 test evidence rows
- `route mutation` (route): 2 obligations, 4 test evidence rows
- `field lifecycle currentness` (other): 7 obligations, 12 test evidence rows
- `current-node trunk invariant` (other): 2 obligations, 4 test evidence rows
- `terminal/closure/resume` (closure): 3 obligations, 5 test evidence rows
- `role/output contracts` (other): 3 obligations, 5 test evidence rows
- `router loop/daemon` (route): 14 obligations, 31 test evidence rows
- `repair transactions` (other): 7 obligations, 8 test evidence rows
- `test tiering/slow-test contracts` (other): 3 obligations, 5 test evidence rows
- `meta/capability parents` (other): 3 obligations, 5 test evidence rows

## Maintenance Rule

When FlowGuard models, runners, result paths, test registries, code ownership surfaces, prompt/card boundaries, or validation readiness surfaces change, rebuild and check this topology.
