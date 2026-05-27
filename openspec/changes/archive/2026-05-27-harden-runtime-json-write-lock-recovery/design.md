## Context

FlowPilot persists daemon/runtime control state through JSON files in the run
root. On Windows, `os.replace()` can raise `PermissionError` while another
process, scanner, or recently crashed writer still holds a handle. The current
runtime JSON helper has a lock file protocol, but two gaps remain:

- replace-time `PermissionError` can escape as a raw fatal exception after a
  short retry window;
- daemon recovery for `RouterLedgerWriteInProgress` writes status and
  `router_state.json` without protecting against a second write-lock collision.

The observed run showed all three outward symptoms: a daemon crash on
`router_scheduler_ledger.json`, a daemon crash while trying to record
`router_state.json` wait status, and a runtime write-lock error packaged as a
PM control blocker for a Controller action file.

## Goals / Non-Goals

**Goals:**

- Preserve daemon liveness when a runtime JSON write lock is recoverable.
- Keep write-lock waits mechanical and bounded before any PM repair path is
  used.
- Preserve valid JSON ledgers and dead-owner takeover evidence.
- Add model and test coverage for scheduler, run-state, and Controller action
  lock surfaces.
- Keep the change compatible with the existing router facade split and install
  sync tooling.

**Non-Goals:**

- Replace the JSON persistence mechanism with a database.
- Change FlowPilot role authority, PM semantics, or sealed packet boundaries.
- Add new external dependencies.
- Hide real corruption: parse failures without an active or recoverable write
  lock still remain repair-needed errors.

## Decisions

1. **Normalize replace-time `PermissionError` into runtime write-lock semantics.**
   The low-level writer already owns the lock file, so a prolonged
   `PermissionError` after retries means the target path is still externally
   blocked. Raising `RouterLedgerWriteInProgress` preserves the existing
   wait/retry vocabulary and path metadata. Alternative considered: increase
   the retry timeout only. That would reduce frequency but still leaves daemon
   paths with fatal raw exceptions.

2. **Make daemon write-lock wait status best-effort.**
   When daemon tick work raises `RouterLedgerWriteInProgress`, the daemon should
   try to refresh lock/status for observability, but any nested
   `RouterLedgerWriteInProgress` during that observability write must produce a
   deferred tick rather than fall into the outer fatal handler. Alternative
   considered: skip all status writes in the wait path. That avoids the crash
   but loses useful liveness information.

3. **Keep dead-owner takeover as the recovery boundary.**
   If a lock has a dead owner, existing takeover evidence should be recorded and
   normal daemon replay should continue. If the owner is live or unknown, daemon
   progress defers to the next tick. Alternative considered: let PM decide all
   lock blockers. That misroutes mechanical runtime failures into semantic
   repair.

4. **Classify runtime write-lock failures before PM blocker materialization.**
   Code paths that catch `RouterLedgerWriteInProgress` while creating or
   summarizing Controller work should treat it as runtime settlement first. PM
   repair is only appropriate after the runtime path proves it cannot settle or
   after the condition represents true protocol corruption.

## Risks / Trade-offs

- **Longer wait before surfacing a real filesystem problem** -> Keep waits
  bounded by existing lock freshness and takeover rules, and leave stale or
  corrupt ledgers visible in daemon status.
- **Nested best-effort writes may hide status update failures** -> Return
  explicit deferred tick metadata containing the original and nested lock paths.
- **Controller blocker routing might under-report a real issue** -> Only
  suppress PM semantic routing for `RouterLedgerWriteInProgress`; genuine
  corruption, invalid payloads, and protocol failures still route through
  existing blocker policy.

## Migration Plan

1. Update the FlowGuard persistent daemon model to include nested write-lock
   recovery and mechanical blocker classification.
2. Add ordinary tests that reproduce the three observed failure shapes.
3. Implement the narrow runtime/daemon/classification changes.
4. Run focused model/tests, install sync, install audit, and background
   heavyweight regressions.

## Open Questions

- None for this scoped fix.
