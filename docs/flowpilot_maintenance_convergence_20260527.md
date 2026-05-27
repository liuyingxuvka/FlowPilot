# FlowPilot Maintenance Convergence - 2026-05-27

## Scope

This maintenance pass is governed by OpenSpec change
`complete-flowpilot-maintenance-convergence` and uses FlowGuard Architecture
Reduction, StructureMesh, DevelopmentProcessFlow, and TestMesh boundaries.

Out of scope: remote push, tag, release publication, deploy, destructive
runtime cleanup, and validation artifact deletion.

## OpenSpec Archive Evidence

- `openspec validate --all --strict --json --no-interactive` passed before
  archive movement: 166 items passed, 0 failed.
- `clarify-parallel-flow-block-authority` archived normally and created
  `openspec/specs/parallel-flow-block-authority/spec.md`.
- 98 additional completed active changes archived normally.
- 15 older completed changes archived with `--skip-specs` after normal archive
  hit superseded target-header conflicts or an already-created partial spec.
  The full proposal/design/spec/task files remain preserved under
  `openspec/changes/archive/`.
- Post-archive `openspec list` reports only
  `complete-flowpilot-maintenance-convergence` as active.
- Post-archive `openspec validate --all --strict --json --no-interactive`
  passed: 147 items passed, 0 failed.

## Validation Artifact Audit

Command:

```powershell
python scripts\audit_validation_artifacts.py --json
```

Result:

- Status: passed, read-only.
- Scanned root: `simulations`.
- Artifact count: 163.
- Duplicate group count: 24.
- Runner duplicate pair count: 21.
- Duplicate bytes: 4,031,018.
- Total bytes scanned: 19,951,402.

Decision:

- No validation artifact was deleted, moved, or rewritten in this pass.
- Duplicate result files remain reviewable evidence.
- Future cleanup must first prove each canonical candidate is still the only
  referenced path for its runner/model family.

## Runtime Retention Audit

Command:

```powershell
python scripts\flowpilot_runtime_retention.py --json --max-runs 30
```

Result:

- Status: passed, read-only.
- FlowPilot runtime root: `.flowpilot`.
- Current run: `run-20260527-072618`.
- Current pointer exists: true.
- Run index exists: true.
- Run directories: 81.
- Indexed runs: 94.
- Missing indexed run directories: 14.
- Unindexed run directories: 1.
- Excess run directory candidates over max 30: 51.
- Runtime size: 351,165,309 bytes across 17,241 files.

Decision:

- No `.flowpilot` runtime directory, current pointer, run index, or run evidence
  was deleted or rewritten in this pass.
- The current run is protected.
- A future cleanup command may be designed separately, but must keep the
  current run and index protected by default.

## FlowGuard Hotspot Contraction

Compatibility-preserving splits:

- `flowpilot_router_work_packets_pm_role_writes_decisions.py` remains the
  import facade. The role-result, formal-gate, packet-outcome, and package
  disposition helpers now live in child modules.
- `flowpilot_router_protocol_external_event_data.py` remains the import facade.
  Startup, material, route, and terminal phase event data now live in phase
  child modules.
- `flowpilot_router_protocol_work_contracts.py` keeps its public contract
  surface and imports process-contract policy data from
  `flowpilot_router_protocol_process_contracts.py`.

Preserved boundaries:

- Public imports and router-facing helper names are retained.
- Runtime data shapes, prompt text, event/ledger schemas, and CLI behavior were
  not intentionally changed.
- Model-test-code alignment metadata now binds the child modules directly.

## Verification Evidence

Foreground checks:

- OK: syntax compilation for all touched runtime, simulation, and contract
  metadata files.
- OK: `python -m unittest tests.test_flowpilot_control_plane_contracts -v`
  passed 23 tests.
- OK:
  `python -m unittest tests.test_flowpilot_full_diagnostic_contracts.FlowPilotFullDiagnosticContractTests -v`
  passed 14 tests.
- OK:
  `python -m unittest tests.test_flowpilot_model_test_alignment.FlowPilotModelTestAlignmentTests -v`
  passed 16 tests.
- OK: `python simulations\run_flowpilot_structure_maintenance_checks.py`
  returned StructureMesh and TestMesh green decisions.
- OK:
  `python simulations\run_flowpilot_model_test_alignment_checks.py --json-out simulations\flowpilot_model_test_alignment_results.json`
  returned `alignment_ok=true`, `full_coverage_ok=true`, 857 covered surfaces,
  0 gaps, 0 deferred structure splits, and 0 explicitly skipped structure
  splits.
- OK:
  `python simulations\run_flowpilot_control_plane_friction_checks.py --skip-live-audit --json-out tmp\flowpilot_control_plane_friction_skip_live_latest.json`
  passed the abstract control-plane model.

Scoped live-run limitation:

- The default live audit against `.flowpilot/runs/run-20260527-072618` still
  fails on active runtime-state findings:
  `material_progress_flags_not_generation_scoped`,
  `material_reissue_keeps_stale_progress_flags`, and
  `packet_result_author_identity_not_replayable`.
- The external event source-contract parsing issue exposed during the split was
  fixed and rechecked; the remaining default live audit findings are not event
  contract readability failures.
- This active run appears peer-owned and is still being used by parallel AI
  work. It was not mutated, repaired, deleted, or rolled back in this pass.
- The failed live audit is treated as a concurrency/runtime-state boundary, not
  proof that the compatibility-preserving code split changed behavior.

Background model regressions:

- OK: `python simulations/run_meta_checks.py` completed in
  `tmp/flowguard_background/run_meta_checks.*`; exit code `0`, status
  `passed`, proof reused `false`.
- OK: `python simulations/run_capability_checks.py` completed in
  `tmp/flowguard_background/run_capability_checks.*`; exit code `0`, status
  `passed`, proof reused `false`.
- For both runs, stdout, stderr, combined, exit, and meta artifacts exist under
  `tmp/flowguard_background/`.

Generated maintenance map:

- `python scripts\flowpilot_maintenance_map.py --json-out docs\flowpilot_maintenance_map.json --markdown-out docs\flowpilot_maintenance_map.md`
  refreshed the repository maintenance map.
- Runtime asset files: 371.
- Runtime owner modules: 291.
- Runtime owner modules over the 450-line threshold: 0.
- Model-test-code diagnostic: full coverage true, gaps 0, covered 857.

## Version And Install Sync

- Repository version bumped from `0.9.13` to `0.9.14`.
- Changelog and handoff notes updated for the maintenance convergence pass.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json` refreshed
  the local `flowpilot` skill installation under the Codex skills directory;
  post-sync `source_fresh=true`.
- OK: `python scripts\audit_local_install_sync.py --json`; repo-owned skill
  freshness passed and installed skill names are unique.
- OK: `python scripts\install_flowpilot.py --check --json`; installed
  FlowPilot digest matches the repository source digest.
- OK: `python scripts\check_install.py --json`; repository installation checks
  passed.
