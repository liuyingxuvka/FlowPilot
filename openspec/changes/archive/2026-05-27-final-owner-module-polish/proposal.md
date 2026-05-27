## Why

The previous runtime clarity pass turned the old monolith into facades and owner
modules, but a small set of owner modules still carry multiple responsibilities
and remain the main places where future bugs would be slow to localize. This
change performs the final targeted polish pass: split only the remaining heavy
owners, keep compatibility facades stable, and keep FlowGuard/StructureMesh
evidence current.

## What Changes

- Split the remaining heavy packet control-plane transition model into
  phase-oriented transition owner modules behind the existing
  `packet_control_plane_model_transitions.py` facade.
- Split the router facade export manifest into domain-oriented manifest shards
  while preserving the existing facade installer and export registry contract.
- Split the largest router owner modules by behavior family:
  action-factory dispatch gates/actions, PM role-work lifecycle/result/index
  helpers, terminal summary/final ledger/closure/reconciliation helpers, and
  Controller action/receipt/reconciliation helpers.
- Continue moving prompt-like instruction text out of Python only where the
  text is stable, long-lived, and already protected by PromptStore-style
  manifest checks.
- Update FlowGuard StructureMesh/TestMesh/model-alignment evidence so the new
  owner boundaries are executable and release-scoped, including a conservative
  source-contract audit for selected model-backed Python surfaces.
- Update install checks, maintainer documentation, version/changelog, and local
  installed skill sync.
- Run focused tests and hidden background router/Meta/Capability regressions
  before local git completion.
- Keep remote publication out of scope: no GitHub push, tag, or release.

## Capabilities

### New Capabilities
- `owner-module-polish`: Covers the final owner-module polish pass for the
  remaining heavy FlowPilot runtime/model files, including facade compatibility,
  StructureMesh/TestMesh evidence, prompt asset discipline, and local-only
  completion gates.

### Modified Capabilities
- `runtime-structure-clarity`: Extends the prior runtime clarity requirement so
  remaining over-large owner modules are split by behavior family rather than
  left as broad catch-all owners.
- `repository-maintenance-guardrails`: Extends maintenance completion to require
  hidden-background evidence, local install freshness, and local git completion
  for this final polish pass.

## Impact

- Affected code: selected files under `skills/flowpilot/assets/`, especially
  packet control-plane transition owners, router export manifests, action
  factory owners, PM role-work owners, terminal ledger owners, and Controller
  scheduler/receipt owners.
- Affected models/tests: `simulations/flowpilot_structure_maintenance_model.py`,
  `simulations/flowpilot_router_facade_split_model.py`,
  `simulations/run_flowpilot_model_test_alignment_checks.py`, focused unit
  tests, router background tier, Meta and Capability FlowGuard regressions.
- Affected docs/versioning/install: maintainer maps, runtime prompt docs if new
  prompt assets are moved, `scripts/install_checks/common.py`, `CHANGELOG.md`,
  `VERSION`, and the installed local FlowPilot skill.
