## Why

FlowPilot already has normal and system-level synthetic AI replay coverage, but it still needs a focused hard-gate proof that bad AI submissions are rejected without polluting run state. This change targets the remaining high-risk class: inputs that look plausible but are unauthorized, stale, mismatched, progress-only, or terminal-overclaiming.

## What Changes

- Add a hard-gate red-team coverage matrix that inventories AI-facing runtime entrypoints, bad package classes, expected rejection behavior, and state non-mutation obligations.
- Add executable red-team replay tests for unauthorized Router events, role-output event authority mismatches, packet/result identity mismatch, progress-only completion overclaims, stale run authority, and terminal closure overclaims.
- Require each hard-gate row to name the entrypoint, bad package class, expected error/blocker result, state invariant, and runtime test evidence.
- Fix any discovered runtime path that accepts a bad package, mutates protected state before rejection, or fails to route the rejected input to a clear blocker/repair state.
- Refresh FlowGuard model-test alignment and synthetic coverage evidence after implementation.

## Capabilities

### New Capabilities

- `hard-gate-red-team-pack`: Defines the hard-gate red-team replay capability for AI-facing runtime entrypoints and rejection/non-mutation expectations.
- `hard-gate-coverage-matrix`: Defines matrix metadata and validation rules for tracking hard-gate red-team coverage evidence.

### Modified Capabilities

- None.

## Impact

- Affected runtime tests: synthetic trace replay, router runtime role-output/packet/terminal tests, and coverage matrix tests.
- Affected simulations: hard-gate matrix script/results and model-test alignment evidence.
- Affected docs/records: FlowGuard adoption log and OpenSpec task evidence.
- No public API, release, tag, push, or deployment action is included.
