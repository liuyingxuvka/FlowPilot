## Why

The previous maintenance pass reduced several large Python surfaces, but the
remaining router, model, and test-helper hotspots are still difficult to reason
about safely. The next split needs FlowGuard StructureMesh/TestMesh evidence
before code movement so shared state, side effects, public entrypoints, and
release evidence cannot drift.

## What Changes

- Add an executable FlowGuard StructureMesh gate for the next router split.
- Add a TestMesh gate for router runtime child-suite evidence and background
  artifact completeness.
- Add FlowGuard Model-Test Alignment evidence so model obligations are bound to
  ordinary test evidence before broad validation claims.
- Add focused ModelMesh-style evidence for remaining large model splits.
- Continue facade-first module decomposition for the router, model, and test
  helper surfaces without changing public imports, CLI commands, event names,
  persisted JSON shapes, or role authority.
- Update verification, handoff, and install-sync documentation to make the new
  gates repeatable.

## Capabilities

### New Capabilities

- `structuremesh-maintenance-gates`: Defines the FlowGuard-backed maintenance
  gate used before and after large script/module/test/model splits.
- `flowguard-model-test-alignment`: Defines the FlowGuard-backed obligation to
  test-evidence review used to decide where to split tests and where to add
  missing tests or model scenarios.

### Modified Capabilities

- `repository-maintenance-guardrails`: Requires StructureMesh/TestMesh evidence
  for the remaining large FlowPilot structural maintenance boundaries.
- `flowguard-model-hierarchy`: Keeps large model splits visible in the
  hierarchy and parent Meta/Capability release evidence.

## Impact

- Affected production code: `skills/flowpilot/assets/flowpilot_router.py` and
  focused helper modules under `skills/flowpilot/assets/`.
- Affected models: remaining large model files under `simulations/`, especially
  persistent router daemon, prompt isolation, cross-plane friction, Meta, and
  Capability parents.
- Affected tests: router runtime child suites, shared router runtime helpers,
  test-tier runner evidence, and model-test alignment evidence.
- Affected validation: OpenSpec strict checks, FlowGuard StructureMesh/TestMesh
  checks, focused unit/model tests, background router tiers, layered
  Meta/Capability checks, install sync, public-release boundary checks, and
  local Git commit readiness.
