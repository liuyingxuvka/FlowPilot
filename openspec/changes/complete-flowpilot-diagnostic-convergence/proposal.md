## Why

The FlowPilot full model-test-code diagnostic is now green as a diagnostic
mechanism, but not fully converged as total structure coverage. The latest run
reports 532 total surfaces, 481 covered surfaces, 51 surfaces with remaining
gaps, zero missing ordinary external-contract tests, zero stale evidence gaps,
and 51 explicit StructureMesh deferrals.

The remaining work should be handled as one convergence change rather than as
many isolated repair passes. The goal is to finish the model-code-test binding
work: every remaining owner module must have ordinary tests for its externally
visible contract, oversized modules must be split only after contract evidence
exists, and stale background/release evidence must be replaced or explicitly
classified.

## What Changes

- Add source-audited ordinary external-contract tests for every remaining
  owner module currently reported as `missing_test`.
- Extend the FlowGuard model-test alignment source-contract plan with concrete
  obligations, code contracts, and test evidence for those modules.
- Refresh the full diagnostic until `missing_test=0`, `internal_only_test=0`,
  `missing_model=0`, `extra_code=0`, and `source_audit_ok=true`.
- Apply StructureMesh-governed splits only where the split is low-conflict and
  model-aligned after the relevant external contracts are pinned; otherwise
  record explicit StructureMesh deferral metadata with the proposed follow-up
  split class and safety reason.
- Repair or reclassify stale background evidence for release and legacy full
  model checks. Legacy monolithic Meta/Capability full graphs are historical
  compatibility oracles when current layered full proofs are valid.
- Run focused, background, install-sync, and final diagnostic validation, then
  commit only scoped local changes.

## Capabilities

### New Capabilities

- `flowpilot-diagnostic-convergence`: FlowPilot can prove that model
  obligations, externally visible code contracts, ordinary tests, structure
  boundaries, and background evidence agree across the full diagnostic surface.

### Modified Capabilities

- `router-owner-contract-coverage`: Expands from selected router owner modules
  to all remaining runtime owner modules in the current diagnostic inventory.
- `structuremesh-router-slimming`: Extends from opportunistic facade slimming
  to contract-gated splits for remaining oversized modules and validation
  entrypoints.
- `testmesh-background-evidence`: Requires final background artifacts rather
  than progress-only or local-only release evidence for release confidence.

## Impact

- Affected tests: new focused external-contract tests and updates to existing
  router/runtime/user-flow/packet contract suites.
- Affected models: `simulations/run_flowpilot_model_test_alignment_checks.py`,
  full diagnostic results, and StructureMesh maintenance evidence.
- Affected code: only modules whose contracts are being tested or whose split
  is StructureMesh-approved after those tests pass.
- Affected validation: focused unit tests, FlowGuard model-test alignment,
  StructureMesh maintenance checks, background fast/router/release tiers,
  install sync, local install audit, and local git commit.
- Out of scope unless separately requested: GitHub push, tag, remote release,
  or public publication.
