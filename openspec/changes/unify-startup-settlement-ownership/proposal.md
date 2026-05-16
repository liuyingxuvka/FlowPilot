## Why

Live FlowPilot startup can fail even when the system is healthy because the
foreground command treats another active runtime writer as a fatal error, and
startup daemon postconditions can reconcile the same Controller receipt through
a second owner. This change keeps startup settlement in the existing runtime
flows while removing the false-failure and split-owner paths.

## What Changes

- Foreground startup/status paths reuse the existing runtime JSON write-lock
  liveness rule: fresh active writers are waited on and retried, while stale
  locks or unsupported evidence still fail through the existing error path.
- Startup daemon bootloader postconditions stop directly owning final
  action-row reconciliation; they write or observe the Controller receipt and
  let the existing startup receipt application path settle Router state.
- FlowGuard live projection recognizes the existing Router startup release path
  after the PM has opened `user_intake`, so post-release states are not
  misclassified as unreleased startup material.
- Replaying an already applied startup receipt remains a no-op and must not
  create a PM/control blocker.
- No new daemon, lock file family, receipt ledger, or startup workflow is
  introduced.

## Capabilities

### New Capabilities
- `startup-settlement-ownership`: Foreground startup writer settlement and
  single-owner startup receipt reconciliation.

### Modified Capabilities
- None.

## Impact

- Affected runtime: `skills/flowpilot/assets/flowpilot_router.py`.
- Affected validation: focused Router runtime tests and the daemon
  reconciliation FlowGuard model/checks.
- Affected sync: repository-owned FlowPilot skill must be synced to the local
  installed skill after validation.
