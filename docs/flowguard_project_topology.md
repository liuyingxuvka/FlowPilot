# FlowGuard Project Topology

This generated map gives agents a project-level background structure for FlowGuard-heavy work.
It is orientation only; it is not validation evidence.

## Summary

- Model runners: 164
- Model-test alignment families: 18
- Code surfaces: 1083
- Test commands: 451
- Evidence summaries: 5
- Known-bad/risk labels surfaced: 2715

## Area Map

| Area | Models | Alignment families | Code surfaces | Test commands | Known-bad labels |
| --- | ---: | ---: | ---: | ---: | ---: |
| `closure` | 9 | 1 | 19 | 13 | 128 |
| `controller` | 7 | 0 | 91 | 33 | 106 |
| `install-validation` | 1 | 0 | 19 | 17 | 15 |
| `material` | 1 | 0 | 10 | 9 | 16 |
| `model-mesh` | 3 | 0 | 7 | 2 | 86 |
| `model-test-alignment` | 5 | 0 | 14 | 8 | 74 |
| `other` | 94 | 9 | 281 | 37 | 1456 |
| `packet` | 10 | 2 | 202 | 173 | 170 |
| `prompt-card` | 3 | 0 | 4 | 0 | 80 |
| `review` | 4 | 0 | 4 | 2 | 78 |
| `route` | 17 | 3 | 353 | 112 | 327 |
| `startup` | 6 | 1 | 69 | 41 | 129 |
| `structure` | 4 | 2 | 10 | 4 | 50 |

## Evidence Boundaries

Topology guides project understanding only; it does not replace executable FlowGuard checks, tests, conformance replay, install audit, or release evidence.

Agents may use this map to choose which model, test, and code areas to inspect.
Completion and readiness claims still need the owning FlowGuard checks, tests, result artifacts, install audits, and freshness evidence.

## Key Evidence Summaries

| Artifact | Path | OK | Decision | Confidence | Findings |
| --- | --- | --- | --- | --- | ---: |
| `model_test_alignment` | `simulations/flowpilot_model_test_alignment_results.json` | True | `` | `` | 0 |
| `coverage_sweep` | `simulations/flowpilot_full_model_coverage_sweep_results.json` | True | `` | `` | 135 |
| `model_maturation` | `simulations/flowpilot_model_maturation_results.json` | True | `model_maturation_scoped_claim` | `scoped` | None |
| `model_mesh` | `simulations/flowpilot_model_mesh_results.json` | True | `` | `` | None |
| `model_hierarchy` | `simulations/flowpilot_model_hierarchy_results.json` | True | `` | `` | None |

## Model Runner Samples

- `capability` (other, abstract_strong_live_mapping_weaker): `simulations/run_capability_checks.py` -> `simulations/capability_thin_parent_results.json`
- `card_instruction_coverage` (packet, specialized_assertion_or_local_hazard): `simulations/run_card_instruction_coverage_checks.py` -> `simulations/card_instruction_coverage_results.json`; known-bad: hazards, ok, packet_prompt_hazards
- `command_refinement` (other, supporting_model_owned): `simulations/run_command_refinement_checks.py` -> `simulations/flowpilot_command_refinement_results.json`; known-bad: background_collaboration_start_fold, card_bundle_fold, final_replay_fold
- `defect_governance` (other, specialized_assertion_or_local_hazard): `simulations/run_defect_governance_checks.py` -> `simulations/defect_governance_results.json`; known-bad: hazards, ok, blocker_never_logged
- `flowpilot_053_ppa_maintenance` (structure, unclassified_model_tier): `simulations/run_flowpilot_053_ppa_maintenance_checks.py` -> `simulations/flowpilot_053_ppa_maintenance_results.json`; known-bad: expected, hazards, ok
- `flowpilot_acceptance_testmesh` (other, supporting_model_owned): `simulations/run_flowpilot_acceptance_testmesh_checks.py` -> `simulations/flowpilot_acceptance_testmesh_results.json`
- `flowpilot_ai_response_execution_closure` (closure, unclassified_model_tier): `simulations/run_flowpilot_ai_response_execution_closure_checks.py` -> `simulations/flowpilot_ai_response_execution_closure_results.json`; known-bad: background_final_artifact_missing, benchmark_parallelism_unproven, coverage_counts_conflated
- `flowpilot_blocker_repair_information_flow` (other, supporting_model_owned): `simulations/run_flowpilot_blocker_repair_information_flow_checks.py` -> `simulations/flowpilot_blocker_repair_information_flow_results.json`; known-bad: failures, hazards, ok
- `flowpilot_canonical_repair_scope_rotation` (other, supporting_model_owned): `simulations/run_flowpilot_canonical_repair_scope_rotation_checks.py` -> `simulations/flowpilot_canonical_repair_scope_rotation_results.json`; known-bad: expected, hazards, ok
- `flowpilot_card_envelope` (packet, supporting_model_owned): `simulations/run_flowpilot_card_envelope_checks.py` -> `simulations/flowpilot_card_envelope_results.json`; known-bad: hazards, ok, ack_contains_body_content
- `flowpilot_cartesian_control_plane_exhaustion` (other, coverage_strong): `simulations/run_flowpilot_cartesian_control_plane_exhaustion_checks.py` -> `simulations/flowpilot_cartesian_control_plane_exhaustion_results.json`; known-bad: expected, hazards, missing_expected_failures
- `flowpilot_complete_system_alignment` (other, coverage_strong): `simulations/run_flowpilot_complete_system_alignment_checks.py` -> `simulations/flowpilot_complete_system_alignment_results.json`
- `flowpilot_complete_system_development` (other, coverage_strong): `simulations/run_flowpilot_complete_system_development_checks.py` -> `simulations/flowpilot_complete_system_development_results.json`; known-bad: expected, hazards, ok
- `flowpilot_complete_system_historical_replay` (other, coverage_strong): `simulations/run_flowpilot_complete_system_historical_replay_checks.py` -> `simulations/flowpilot_complete_system_historical_replay_results.json`
- `flowpilot_complete_system_live_host_readiness` (other, coverage_strong): `simulations/run_flowpilot_complete_system_live_host_readiness_checks.py` -> `simulations/flowpilot_complete_system_live_host_results.json`
- `flowpilot_complete_system_runtime` (other, coverage_strong): `simulations/run_flowpilot_complete_system_runtime_checks.py` -> `simulations/flowpilot_complete_system_runtime_results.json`
- `flowpilot_complete_system_structure` (structure, coverage_strong): `simulations/run_flowpilot_complete_system_structure_checks.py` -> `simulations/flowpilot_complete_system_structure_results.json`; known-bad: missing_dynamic_host_owner, missing_module_rationale
- `flowpilot_complete_system_testmesh` (other, coverage_strong): `simulations/run_flowpilot_complete_system_testmesh_checks.py` -> `simulations/flowpilot_complete_system_testmesh_results.json`
- `flowpilot_complete_system_ui` (other, coverage_strong): `simulations/run_flowpilot_complete_system_ui_checks.py` -> `simulations/flowpilot_complete_system_ui_results.json`
- `flowpilot_complete_workstream_fake_ai` (other, unclassified_model_tier): `simulations/run_flowpilot_complete_workstream_fake_ai_checks.py` -> `simulations/flowpilot_complete_workstream_fake_ai_results.json`
- `flowpilot_complete_workstream_orchestration` (other, unclassified_model_tier): `simulations/run_flowpilot_complete_workstream_orchestration_checks.py` -> `simulations/flowpilot_complete_workstream_orchestration_results.json`; known-bad: known_bad_count, ok, rows
- `flowpilot_contract_exhaustion_mesh` (other, coverage_strong): `simulations/run_flowpilot_contract_exhaustion_mesh_checks.py` -> `simulations/flowpilot_contract_exhaustion_mesh_results.json`; known-bad: hazards_ok
- `flowpilot_control_plane_friction` (other, coverage_strong): `simulations/run_flowpilot_control_plane_friction_checks.py` -> `simulations/flowpilot_control_plane_friction_results.json`; known-bad: hazards, ok, ack_consumed_semantic_wait_lost
- `flowpilot_control_plane_ledger_consolidation` (closure, supporting_model_owned): `simulations/run_flowpilot_control_plane_ledger_consolidation_checks.py` -> `simulations/flowpilot_control_plane_ledger_consolidation_results.json`; known-bad: failures, hazards, ok
- `flowpilot_control_plane_state_consistency` (other, supporting_model_owned): `simulations/run_flowpilot_control_plane_state_consistency_checks.py` -> `simulations/flowpilot_control_plane_state_consistency_results.json`; known-bad: failures, hazards, ok

## Alignment Families

- `startup` (startup): 2 obligations, 4 test evidence rows
- `packet/card/ack` (packet): 4 obligations, 7 test evidence rows
- `packet result family` (packet): 52 obligations, 97 test evidence rows
- `route mutation` (route): 3 obligations, 6 test evidence rows
- `field lifecycle currentness` (other): 12 obligations, 16 test evidence rows
- `current-node trunk invariant` (other): 2 obligations, 4 test evidence rows
- `terminal/closure/resume` (closure): 6 obligations, 22 test evidence rows
- `role/output contracts` (other): 3 obligations, 5 test evidence rows
- `router loop/daemon` (route): 14 obligations, 31 test evidence rows
- `repair transactions` (other): 10 obligations, 11 test evidence rows
- `test tiering/slow-test contracts` (other): 4 obligations, 7 test evidence rows
- `rejection/liveness matrix` (other): 5 obligations, 9 test evidence rows
- `route authority singularity` (route): 5 obligations, 6 test evidence rows
- `core deliverable non-downgrade` (other): 1 obligations, 2 test evidence rows
- `flowguard 0.53 ppa maintenance` (structure): 4 obligations, 5 test evidence rows
- `complete workstream and ordinary resource discovery` (other): 6 obligations, 6 test evidence rows
- `skillguard deep contract maintenance` (structure): 4 obligations, 5 test evidence rows
- `meta/capability parents` (other): 3 obligations, 5 test evidence rows

## Maintenance Rule

When FlowGuard models, runners, result paths, test registries, code ownership surfaces, prompt/card boundaries, or validation readiness surfaces change, rebuild and check this topology.
