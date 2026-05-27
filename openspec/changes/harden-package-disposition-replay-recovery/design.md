## Context

The existing package-disposition model already treats router event, batch id,
packet ids, and packet generation id as the semantic identity. `body_hash` is
audit and conflict evidence. A different `body_hash` for the same identity is
still a real conflict.

The missed branch is the replay state after that conflict is no longer new:
the run may already have an active control blocker or a PM repair transaction
that owns the conflict. In that state, daemon role-output replay must preserve
the current repair wait rather than throwing a fresh fatal conflict.

## Model

Represent the repair as:

`Package disposition replay input x control-plane state -> Set(replay outcome x control-plane state)`

State dimensions:

- replay source: direct event intake, role-output ledger replay, or daemon
  restart replay;
- package kind: material scan, research result, or current-node result;
- conflict ownership: no owner, active control blocker, PM repair decision,
  terminal quarantine, or unknown corruption;
- legal wait: PM control-blocker repair, follow-up producer wait, terminal
  stop, or no active wait.

Safe outcomes:

- same identity and same hash returns already-recorded with no duplicate side
  effect;
- same identity and different hash with no owner opens one control blocker;
- same identity and different hash with an active owner is quarantined or
  skipped as stale conflict evidence;
- current legal wait remains visible and daemon stays alive;
- new generation with authorized producer evidence remains a distinct package
  identity.

Forbidden outcomes:

- daemon enters `daemon_error` from a repair-owned stale package conflict;
- stale conflict is accepted as successful package disposition;
- stale conflict closes a wait as success;
- repeated replay creates duplicate PM dispositions, duplicate control
  blockers, or duplicate repair transactions;
- tests claim full same-class closure while covering only material-scan.

## Implementation Approach

1. Extend the OpenSpec and FlowGuard obligations before runtime edits.
2. Add an explicit model-miss branch for package-disposition conflict replay
   after control-blocker or PM repair ownership exists.
3. Add focused failing tests for the observed replay class and same-class
   generalized cases across material-scan, research, and current-node package
   dispositions.
4. Introduce or reuse a shared conflict classifier so direct event intake and
   role-output ledger replay agree on the same outcomes.
5. In role-output ledger reconciliation, check whether a conflicting scoped
   identity is already represented by an active blocker or PM repair decision
   before treating it as fatal.
6. Record stale conflict handling as explicit audit/quarantine metadata where
   practical, without weakening the hard body-conflict rule.
7. Rerun focused runtime tests, FlowGuard model checks, model-test alignment,
   background heavy regressions, OpenSpec validation, and install sync checks.

## Validation

- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`.
- Event-idempotency FlowGuard checks for direct and replay package conflicts.
- Control-plane friction checks for daemon replay and wait preservation.
- Repair-transaction checks where PM repair ownership affects follow-up waits.
- Known-friction regression matrix with a package-disposition conflict replay
  family row.
- Focused pytest/unittest coverage for material-scan, research, and current
  node package disposition conflict replay.
- Daemon restart or tick-level replay fixture proving no `daemon_error` for
  repair-owned stale conflicts.
- Local installed FlowPilot skill sync and install freshness audit.
