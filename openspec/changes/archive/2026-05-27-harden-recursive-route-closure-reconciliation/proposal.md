## Why

The previous maintenance pass made FlowPilot v0.9.4 locally healthy, but the
remaining route and closure risks are now narrow enough to finish in one pass.
Two gaps still matter before heavier dogfooding:

- recursive route traversal can skip a sibling parent/module and enter its leaf
  child directly after the previous parent closes;
- terminal closure does not yet make defect-ledger, role-memory, and imported
  artifact quarantine reconciliation first-class runtime evidence.

## What Changes

- Require effective route traversal to enter every non-root parent/module before
  any of its child leaves, including sibling modules reached after a prior
  parent completes.
- Add a focused FlowGuard model for recursive route traversal and terminal
  closure reconciliation hazards.
- Add runtime reconciliation helpers for defect ledger, role memory, and
  continuation quarantine/imported-artifact disposition.
- Record those reconciliation results in the final route-wide ledger and
  terminal closure suite, and block closure when they are dirty.
- Update tests, templates, install checks, docs, version metadata, installed
  skill sync, and local git evidence.

## Capabilities

### New Capabilities

- `recursive-route-parent-entry`: sibling parent/module nodes are entered and
  reviewed before descendants.
- `terminal-closure-reconciliation`: terminal closure cites and enforces defect
  ledger, role-memory, and imported-artifact quarantine reconciliation.

### Modified Capabilities

- `repository-maintenance-guardrails`: this maintenance pass finishes with
  OpenSpec validation, FlowGuard evidence, local install freshness, background
  regression artifacts, and a local git commit. It does not push, tag, publish,
  or create a release.

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- `templates/flowpilot/`
- `simulations/`
- `tests/test_flowpilot_router_runtime.py`
- `scripts/check_install.py`
- `HANDOFF.md`, `README.md`, `CHANGELOG.md`, and FlowGuard adoption docs
- Local installed FlowPilot skill after repository validation passes
