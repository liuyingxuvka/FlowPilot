## Why

FlowPilot is much easier to maintain after the previous structure pass, but the
remaining router facade, aggregate router runtime test source, role/packet
runtime surfaces, and several child FlowGuard models are still large enough to
slow safe maintenance. This change finishes the structure convergence work so
future repairs can happen in small, obvious modules with focused validation.

## What Changes

- Preserve the current local `main` baseline with a rollback backup before
  production-code edits.
- Continue facade-first router cleanup while preserving public imports, CLI
  commands, event names, persisted JSON shapes, and runtime protocol semantics.
- Move router runtime test implementations out of the aggregate source into
  domain modules while keeping compatibility entrypoints during the migration.
- Split role-output and remaining packet-runtime responsibilities behind their
  current public modules.
- Split the largest child FlowGuard models and runners into state, transition,
  hazard, invariant, and audit modules where the split improves readability.
- Add a verification matrix that maps changed boundaries to focused tests,
  model checks, slow-domain background checks, install sync, and public-boundary
  checks.
- Keep Meta/Capability release checks on the current layered `--full` path.
  The old `--legacy-full` path remains an explicit compatibility oracle only.
- Synchronize the repository-owned installed FlowPilot skill and local git
  state after validation.

## Capabilities

### New Capabilities

- `final-structure-convergence`: final maintainability contract for reducing
  large FlowPilot Python and test surfaces without changing runtime behavior,
  public entrypoints, or release/publication boundaries.

### Modified Capabilities

- None. This is an implementation-structure and verification-readiness change;
  product behavior and protocol contracts remain unchanged unless validation
  exposes a real bug that must be repaired in scope.

## Impact

- Affected code:
  - `skills/flowpilot/assets/flowpilot_router.py` and focused router helpers.
  - `tests/test_flowpilot_router_runtime.py` and router runtime domain tests.
  - `skills/flowpilot/assets/role_output_runtime.py`.
  - `skills/flowpilot/assets/packet_runtime.py` if remaining CLI/audit slices
    still warrant extraction.
  - Large child FlowGuard models and selected check runners in `simulations/`.
- Affected verification:
  - focused router runtime tests,
  - role-output and packet-runtime tests,
  - focused child FlowGuard checks,
  - model hierarchy check,
  - layered Meta/Capability `--full` checks,
  - install sync/check/audit,
  - smoke and public-boundary checks.
- No remote push, tag, GitHub Release, deploy, binary package, or public
  publication is part of this change.
