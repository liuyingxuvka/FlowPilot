## 1. Inventory And Routing

- [x] 1.1 Run predictive KB, git/coordination, OpenSpec, and real FlowGuard preflight.
- [x] 1.2 Capture all current red/yellow groups from the inventory into this task plan.
- [x] 1.3 Validate the OpenSpec change strictly.

## 2. Red Runner Repairs

- [x] 2.1 Repair cross-plane source audit so split-facade helper ownership is detected.
- [x] 2.2 Repair control-plane expected-event audit so split external-event contracts are detected.
- [x] 2.3 Repair material-scan runtime phase synchronization for future runs.
- [x] 2.4 Repair daemon live projection so controller-relayed startup intake status is recognized.
- [x] 2.5 Add focused tests for each repaired red-runner boundary.

## 3. Scoped Evidence Accounting

- [x] 3.1 Stop counting default `--json-out` omission as skipped evidence when parsed stdout is current.
- [x] 3.2 Keep true missing/scoped replay adapters visible with their owning runners.
- [x] 3.3 Keep true semantic or mutation waivers visible without overclaiming pass evidence.

## 4. Structure Findings

- [x] 4.1 Refresh the diagnostic list of deferred StructureMesh split findings.
- [x] 4.2 Split only any structure target that has a focused safe ownership proof and parity tests in this pass.
- [x] 4.3 Classify any remaining broad split target as a StructureMesh authority blocker, not a silent pass.

Result: no deferred StructureMesh target was split in this pass. The remaining
twelve split candidates are broad ownership-boundary work, so they remain
visible as StructureMesh-scoped follow-up instead of being force-cleared.

## 5. Validation And Sync

- [x] 5.1 Run focused unit tests for the repaired audit/runtime boundaries.
- [x] 5.2 Run the red FlowGuard runners directly.
- [x] 5.3 Run FlowGuard model-test alignment and full coverage sweep/inventory refresh.
- [x] 5.4 Run install/audit freshness checks and sync repo-owned FlowPilot skill if production skill source changed.
- [x] 5.5 Record FlowGuard adoption evidence and KB postflight.

## Current Finding Queue

Closed on 2026-05-22.

- Red runner group: none.
- Live-runtime/current-state group: none.
- Source/code finding group: none.
- Missing or scoped replay adapter group: none; exact replay evidence is recorded in `simulations/flowpilot_full_model_replay_evidence.json`.
- Skipped/scoped evidence group: none; scoped runner keys are covered only when the replay evidence manifest names exact current evidence.
- Deferred StructureMesh split group: none.
- Explicit StructureMesh skip: `flowpilot_router_protocol_external_event_data.py`, because it is a table-only declarative protocol surface with no functions, classes, state writes, or duplicate effect paths.

Final evidence:

- `simulations/flowpilot_model_test_alignment_results.json`: `alignment_ok`, `source_audit_ok`, `full_diagnostic_ok`, `full_coverage_ok`, and `release_convergence_ok` are true.
- `simulations/flowpilot_full_model_coverage_inventory_results.json`: 96 runners, no gap classes.
- `simulations/flowpilot_layered_boundary_proof_results.json`: `layered_accounting_ok` and `full_leaf_cartesian_ok` are true.
