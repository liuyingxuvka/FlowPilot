## Why

FlowPilot now has normal synthetic replay coverage and focused hard-gate red-team packages, but the remaining gap is whether fake AI work can drive a whole Router/daemon-controlled run from startup to terminal closure while multiple things go wrong in sequence. The user's target confidence depends on full-flow evidence: bad packages must be rejected, recovery must return to the legal path, parallel runs must not interfere, background proof must be final rather than progress-only, and terminal closure must remain blocked until the route is clean.

## What Changes

- Add an end-to-end synthetic chaos coverage matrix for full-flow fake AI work packages.
- Add executable full-flow replay tests that use Router/daemon runtime helpers across startup, packet dispatch, worker result submission, PM repair, background proof, and terminal closure boundaries.
- Add combination-error scenarios where a run sees more than one bad package before recovering.
- Add recovery-loop scenarios that prove rejection is not enough: the run must accept the repaired package and continue.
- Add parallel-run scenarios that prove one AI/run cannot stop, overwrite, or complete another run.
- Add terminal and background-proof scenarios that reject overclaims until final artifacts and ledgers are clean.
- Wire the new tests into the routine fast parent and affected router child evidence.
- Refresh model-test alignment and local install evidence after implementation.

## Capabilities

### New Capabilities

- `end-to-end-synthetic-agent-chaos-replay`: Defines daemon-driven fake AI replay scenarios that span startup through terminal closure with injected errors and recovery.
- `end-to-end-chaos-coverage-matrix`: Defines matrix metadata and required evidence for full-flow fake AI coverage, including phases, injected errors, recovery routes, protected invariants, and final proof.

### Modified Capabilities

- `hard-gate-red-team-pack`: The existing hard-gate cells remain valid but become supporting leaf evidence for the broader full-flow chaos replay.
- `hard-gate-coverage-matrix`: The existing matrix remains scoped to entrypoint rejection and is cross-linked from the full-flow matrix.

## Impact

- Affected runtime tests: synthetic agent trace replay, hard-gate replay, Router startup/packet/terminal/runtime domain tests.
- Affected simulations: new full-flow chaos matrix script/results and model-test alignment evidence.
- Affected test tiers: fast parent and selected router domain child tiers.
- Affected docs/records: FlowGuard adoption log, OpenSpec artifacts, and local predictive-KB postflight.
- No public release, remote push, tag, deployment, or archive action is included.
