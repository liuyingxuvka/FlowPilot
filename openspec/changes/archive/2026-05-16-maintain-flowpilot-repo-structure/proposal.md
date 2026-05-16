## Why

FlowPilot has accumulated many completed OpenSpec changes, large validation
outputs, duplicated source artifacts, and local runtime state while the core
runtime kept evolving quickly. The next maintenance pass should make that
history easier to navigate without weakening FlowGuard-backed behavior checks
or losing evidence.

## What Changes

- Archive completed OpenSpec changes into the OpenSpec archive area while
  leaving unfinished or still-active changes visible.
- Add repository maintenance reports for validation artifact duplication and
  local FlowPilot runtime retention, both defaulting to read-only output.
- Reduce low-risk duplicate source ownership where a script can delegate to the
  skill asset source of truth.
- Split a small startup-focused portion of the router runtime tests out of the
  monolithic router test file.
- Clean public-boundary documentation issues and add repository text/binary
  line-ending policy.
- Run focused tests and background FlowGuard model regressions with the
  existing stable artifact contract.
- Re-sync the locally installed FlowPilot skill and verify source freshness.

## Capabilities

### New Capabilities

- `repository-maintenance-guardrails`: Defines how maintenance passes preserve
  OpenSpec evidence, FlowGuard evidence, local runtime state, install freshness,
  and public release boundaries.

### Modified Capabilities

None. This pass should not change FlowPilot product behavior, runtime protocol,
or public invocation semantics.

## Impact

Affected areas are OpenSpec change layout, maintenance scripts, focused tests,
documentation hygiene, local install synchronization, and validation logs.
Runtime protocol and skill behavior should remain compatible with the current
FlowGuard model boundaries.
