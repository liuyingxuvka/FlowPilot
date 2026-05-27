## Why

FlowPilot already emits rich `next_step_contract` dictionaries on Router and
Controller actions, but those dictionaries are not yet promoted into the new
FlowGuard workflow-step contract evidence path. The current final confidence
gate also remains blocked by three model-test-code coverage findings, so the
process needs a focused pass that makes step obligations executable and closes
the release evidence gaps.

## What Changes

- Add a FlowGuard-backed workflow-step contract projection for FlowPilot
  `next_step_contract` records, including preconditions, receipts,
  postconditions, stale invalidators, and continuation blockers.
- Add executable checks and tests that prove key Router action contracts are
  projected into first-class step-contract evidence.
- Reclassify routine Router validation around focused TestMesh child suites
  rather than broad wrapper modules that are too slow for daily confidence.
- Clear the current full model-test-code diagnostic blockers by adding current
  evidence for the two deferred runtime StructureMesh surfaces and replacing
  stale legacy-full evidence with current completed evidence or a justified
  supersession.
- Keep local install sync, install audit, and final confidence validation
  serialized so installed FlowPilot matches the final source tree.

## Capabilities

### New Capabilities
- `workflow-step-contract-gates`: Defines the FlowGuard step-contract evidence
  path for FlowPilot `next_step_contract` records and the release gate that
  consumes it.

### Modified Capabilities
- `flowpilot-structure-debt-convergence`: Runtime contract surfaces above the
  diagnostic threshold may be cleared by current StructureMesh deferral
  evidence only when the final diagnostic no longer treats them as actionable
  release blockers.
- `router-runtime-testmesh`: Routine Router confidence must consume focused
  child-suite evidence and avoid treating broad wrapper modules as required
  routine evidence.
- `flowguard-full-model-coverage-inventory`: The full diagnostic must consume
  workflow-step contract evidence, current TestMesh child evidence, and
  completed legacy/superseded validation status before final confidence.

## Impact

- Router action-contract and model-test-alignment code under `simulations/`.
- Test-tier definitions under `scripts/test_tier/` and tests that validate
  tier composition.
- FlowPilot runtime contract diagnostics for `skills/flowpilot/assets/`.
- Local install sync scripts and install audit/check commands.
- OpenSpec task evidence and FlowGuard generated result artifacts.
