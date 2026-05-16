## 1. Model and Contract

- [x] 1.1 Add focused FlowGuard coverage for current-work ownership projection, including pending-action, packet-holder, passive-reconciliation, and internal Router/Controller cases.
- [x] 1.2 Validate the OpenSpec change artifacts.

## 2. Router Status Implementation

- [x] 2.1 Implement a helper that derives one `current_work` object from pending action, packet ledger, passive waits, scheduler waits, and internal daemon state.
- [x] 2.2 Attach `current_work` to Router daemon status and foreground standby payloads without removing legacy `current_wait` fields.
- [x] 2.3 Attach `current_work` to `display/current_status_summary.json` and ensure packet-holder ownership is visible when `pending_action` is null.

## 3. Runtime Tests and Installation

- [x] 3.1 Add focused runtime tests for packet-holder and passive-reconciliation ownership with `pending_action` null.
- [x] 3.2 Run focused model and runtime tests, then run heavyweight meta/capability checks in the background log contract.
- [x] 3.3 Sync and audit the locally installed FlowPilot skill from the repository source.
- [x] 3.4 Review git status, preserve compatible parallel-agent changes, and commit the complete local repository state requested by the user.
