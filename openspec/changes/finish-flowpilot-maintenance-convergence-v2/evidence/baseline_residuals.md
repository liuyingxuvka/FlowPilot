# V2 Maintenance Baseline Residuals

Generated during the initial `finish-flowpilot-maintenance-convergence-v2`
preflight.

## Commands

- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION); print(flowguard.__file__)"` returned schema `1.0`.
- `openspec validate finish-flowpilot-maintenance-convergence-v2 --strict` passed.
- `python scripts/flowpilot_maintenance_map.py --json-out tmp/maintenance_convergence_v2/maintenance_map.json --markdown-out tmp/maintenance_convergence_v2/maintenance_map.md` passed.
- `python scripts/run_flowguard_coverage_sweep.py --timeout-seconds 20 --json-out tmp/maintenance_convergence_v2/coverage_sweep_baseline.json` produced a non-green baseline.
- `python simulations/run_flowpilot_full_model_coverage_inventory.py --sweep-json tmp/maintenance_convergence_v2/coverage_sweep_baseline.json --alignment-json simulations/flowpilot_model_test_alignment_results.json --json-out tmp/maintenance_convergence_v2/coverage_inventory_baseline.json --markdown-out tmp/maintenance_convergence_v2/coverage_inventory_baseline.md` passed.
- `python scripts/run_test_tier.py --tier release --background --background-dir tmp/flowguard_background_v2_release --background-max-parallel 2 --json` launched and completed the release background supervisor.

## Coverage Inventory Baseline

- Runner count: `106`
- Sweep ok: `false`
- Model-test alignment ok: `true`
- Source audit ok: `true`
- Full coverage ok: `false`
- Release convergence ok: `false`
- Finding count: `45`

## Residual Groups

| Gap class | Runners | Owner route |
| --- | --- | --- |
| `runner_unparsed_or_unavailable` | `flowpilot_process_liveness` | TestMesh / runner parsing repair |
| `runner_not_ok` | `flowpilot_control_plane_friction`, `flowpilot_final_confidence_gate`, `flowpilot_terminal_state_monotonicity`, `protocol_contract_conformance` | DevelopmentProcessFlow plus direct owner routes |
| `live_runtime_or_state_findings` | `flowpilot_control_plane_friction`, `flowpilot_model_mesh` | ModelMesh / live runtime disposition |
| `source_or_code_findings` | `flowpilot_terminal_state_monotonicity` | Model-Test Alignment / source repair |
| `unclassified_model_tier` | `flowpilot_controller_wait_receipt_audit`, `flowpilot_final_confidence_gate`, `flowpilot_flowguard_work_order`, `flowpilot_model_maturation`, `flowpilot_packet_result_family_parity`, `flowpilot_recovery_supervisor`, `flowpilot_role_recovery_liveness`, `flowpilot_runtime_gateway_adoption`, `flowpilot_singleton_identity`, `flowpilot_workflow_step_contract` | ModelMesh / TestMesh classification |

## Protocol Contract Conformance

`tmp/maintenance_convergence_v2/protocol_contract_conformance_baseline.json`
reports `ok: false` with 25 current-source failures. The first repair batches
are:

- startup fact validator and startup repair identity;
- control-blocker and PM resume payload contracts;
- role-output loader compact path/hash references;
- material scan and material dispatch protocol source facts;
- model-miss review block flag routing;
- PM role-work contract-family and recipient-drift rejection;
- global process/contract/result binding tables;
- wait event producer binding tables.

## Terminal Monotonicity

`tmp/maintenance_convergence_v2/terminal_state_monotonicity_baseline.json`
reports `ok: false`. Source audit findings:

- Router pending-return selection does not visibly use `resolved_at` and
  completed-return proof.
- Router card-return checks do not visibly set resolved status and
  completed-return proof for both card and bundle returns.

## Live Runtime And Final Confidence

- `flowpilot_control_plane_friction` reports terminal heartbeat cleanup lacks
  durable host automation proof for `run-20260528-142320`.
- `flowpilot_model_mesh` reports `packet_authority_unchecked` for the same run
  in the coverage sweep.
- Release background artifacts under `tmp/flowguard_background_v2_release`
  show `release_tooling`, `meta_full`, and `capability_full` passed, while
  `public_release_check` failed because a tracked document contained a local
  absolute path and the worktree is intentionally dirty with peer-agent work.

## Claim Boundary

This baseline proves only the current residual map and some release-tier child
evidence. It does not prove final convergence. Any source, model, test, prompt,
or install-sync edit after this file stales affected evidence and requires the
corresponding focused rerun.
