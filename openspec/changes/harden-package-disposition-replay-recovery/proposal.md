## Why

Live FlowPilot control-plane evidence showed that a same-package PM
disposition conflict can be correctly rejected once, then crash the Router
daemon later when stale role-output ledger replay sees the same different
`body_hash` after a control blocker or PM repair decision already owns the
conflict.

The prior package-disposition hardening covered semantic identity and direct
conflict rejection, but it overclaimed confidence for the daemon replay path
and repair-owned conflict states.

## What Changes

- Extend PM package-disposition semantics so a conflicting replay is classified
  by repair ownership instead of always treated as a fresh fatal event.
- Harden daemon direct role-output reconciliation so stale package conflicts
  that are already owned by a control blocker or PM repair decision are
  quarantined or skipped while the legal wait remains visible.
- Preserve the hard `body_hash` conflict rule: conflicting same-generation
  package bodies are never silently accepted as success.
- Add FlowGuard model-miss coverage, same-class generalized tests, and a
  recurring defect-family gate for package-disposition conflict replay.
- Validate material-scan, research, and current-node package disposition replay
  behavior across direct event intake, role-output ledger replay, active
  control-blocker ownership, PM repair-decision ownership, and daemon restart
  replay.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `pm-package-disposition-semantics`: Clarifies repair-owned conflict replay
  and same-class coverage across material, research, and current-node package
  dispositions.
- `daemon-projection-reconciliation`: Requires daemon role-output replay to
  classify already-owned package conflicts without entering `daemon_error`.
- `router-external-wait-reconciliation`: Preserves the legal PM/control-blocker
  wait when a stale conflicting package disposition is replayed.
- `known-friction-defect-family-gates`: Adds a recurring gate for package
  disposition conflict replay after earlier scoped green evidence missed the
  daemon path.

## Impact

- Affected runtime code: role-output bridge event reconciliation and shared
  scoped-event conflict classification.
- Affected FlowGuard models: event idempotency, control-plane friction, repair
  transaction evidence as needed, known-friction regression matrix, and
  model-test alignment.
- Affected tests: focused router runtime tests for PM package-disposition
  conflicts and daemon replay recovery across all package kinds.
- Affected sync: repo-owned installed FlowPilot skill must be refreshed and
  install freshness checks must pass before this change is considered done.
