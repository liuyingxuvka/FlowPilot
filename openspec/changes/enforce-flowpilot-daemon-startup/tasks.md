## 1. FlowGuard

- [x] 1.1 Update the persistent Router daemon model/checks so formal startup
      treats daemon startup as an internal required step, not an optional mode.
- [x] 1.2 Add a known-bad startup hazard where Controller core loads after a
      failed or skipped daemon startup, and verify the hazard is detected.

## 2. Runtime

- [x] 2.1 Add an internal startup bootstrap action that starts or attaches to
      the run-scoped Router daemon before `load_controller_core`.
- [x] 2.2 Fail formal startup if daemon startup cannot create or observe live
      lock/status/ledger state.
- [x] 2.3 Preserve manual CLI daemon commands for diagnostics and explicit
      stale-lock repair without adding a daemon-off formal path.

## 3. Tests And Docs

- [x] 3.1 Add focused runtime tests for daemon-before-Controller ordering,
      startup failure on daemon launch failure, and same-run live daemon
      attach without duplicate writer.
- [x] 3.2 Update skill instructions so formal FlowPilot startup describes the
      daemon as built in, not optional.
- [x] 3.3 Run focused tests, FlowGuard checks, install sync, and git status.
