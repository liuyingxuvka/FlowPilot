## Why

FlowPilot's current runtime and validation files are correct but too dense to
maintain safely: the main router still contains multi-hundred-line event,
controller-action computation, and action-application functions, while the
largest model and install-check files concentrate unrelated responsibilities in
single functions. This change reduces structural weight without changing
protocol semantics, persisted JSON shapes, public behavior, or release scope.

## What Changes

- Preserve the current commit as the rollback baseline and record a structural
  audit before runtime refactoring.
- Add a focused FlowGuard model for the refactor process itself: no protocol
  field changes, no deleted compatibility entrypoints, one boundary per slice,
  validation before the next slice, and install/public-boundary sync before
  remote sync.
- Split router responsibilities behind compatibility entrypoints:
  event handling, controller-action provider ordering, controller-action
  handlers, and selected runtime domains.
- Split the large router runtime test file into domain wrappers while keeping
  the legacy aggregate test entry available during migration.
- Split the Meta and Capability model `apply` flows into phase functions
  without changing explored state, hazard labels, or result meaning.
- Split `scripts/check_install.py` into check groups while preserving the JSON
  output contract.
- Update handoff/adoption documentation and synchronize the installed
  `flowpilot` skill after source changes.
- Do not add features, change protocol semantics, alter JSON payload shapes,
  publish a release, or delete old public entrypoints in this change.

## Capabilities

### New Capabilities

- `behavior-preserving-structural-maintenance`: Rules for large internal
  refactors that reduce file/function size while preserving runtime behavior,
  protocol semantics, validation gates, rollback points, and install sync.
- `router-runtime-module-boundaries`: Rules for splitting FlowPilot router
  events, controller-action computation, action handlers, runtime domains, and
  test entrypoints behind stable compatibility surfaces.
- `model-and-tooling-structure-reduction`: Rules for splitting large FlowGuard
  model `apply` functions and install/release check scripts without changing
  check meaning, result contracts, or public-boundary behavior.

### Modified Capabilities

- None. Existing protocol and product-behavior requirements remain unchanged.

## Impact

- Affected source: `skills/flowpilot/assets/flowpilot_router.py` and new
  helper modules under `skills/flowpilot/assets/`.
- Affected models: `simulations/meta_model.py`,
  `simulations/capability_model.py`, and a new focused structural refactor
  model/check runner.
- Affected tooling: `scripts/check_install.py`.
- Affected tests: router runtime domain tests and split test wrappers.
- Affected docs: HANDOFF, README, FlowGuard adoption log, and a structural
  baseline/audit note.
- No dependency, protocol, API, release, or deployment changes.
