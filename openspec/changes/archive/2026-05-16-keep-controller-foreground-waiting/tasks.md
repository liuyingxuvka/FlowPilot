## 1. Model And Contract

- [x] 1.1 Update the persistent Router daemon FlowGuard model with foreground standby states, safe waits, and known-bad foreground-stop hazards.
- [x] 1.2 Add executable checks proving standby does not call `next` or `run-until-wait` as the normal metronome.

## 2. Runtime Implementation

- [x] 2.1 Add a Router CLI/runtime foreground standby command that polls daemon status, lock, and Controller action ledger.
- [x] 2.2 Return structured standby outcomes for `waiting_for_role`, `controller_action_ready`, `terminal`, `daemon_stale_or_missing`, and bounded `timeout_still_waiting`.
- [x] 2.3 Keep standby metadata-only and free of sealed packet/result/report/decision body access.

## 3. Controller Guidance

- [x] 3.1 Update Controller role guidance to require foreground standby instead of ending when daemon is live and waiting for a role.
- [x] 3.2 Update skill/protocol references so standby is the normal foreground wait path and `next`/`run-until-wait` remain diagnostics or explicit repair only.

## 4. Verification And Sync

- [x] 4.1 Add focused runtime tests for role-wait standby, action wake, stale daemon exit, and no manual Router metronome.
- [x] 4.2 Run focused tests, FlowGuard checks, install sync/audit/check, and background heavy meta/capability regressions.
- [x] 4.3 Commit the repository after preserving unrelated existing work.
