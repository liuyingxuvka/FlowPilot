## 1. Inventory And Model Contract

- [x] 1.1 Inventory all Controller-facing wait-shaped action types and classify them as executable action, passive wait status, or standby monitor duty.
- [x] 1.2 Extend focused FlowGuard coverage so pure wait rows in the ordinary Controller queue, pure waits hiding Router-local obligations, standby without wait-target status, and due reminders without executable Controller rows are known-bad hazards.
- [x] 1.3 Run focused FlowGuard checks and preserve result evidence. Run Meta/Capability regressions in the background when needed and practical.

## 2. Runtime Implementation

- [x] 2.1 Add a narrow Router helper for passive wait projections and use it wherever Controller action rows are written or counted.
- [x] 2.2 Prevent `await_role_decision`, `await_card_return_event`, `await_card_bundle_return_event`, and `await_current_scope_reconciliation` from being written as ordinary executable Controller action rows.
- [x] 2.3 Preserve passive wait metadata in Router daemon status, current status summary, scheduler/current-wait projections, and continuous standby payloads.
- [x] 2.4 Ensure Router-owned local obligations are consumed or exposed before passive wait status can be preserved.
- [x] 2.5 Treat historical waiting rows as status/history so they do not hide new executable Controller work.
- [x] 2.6 Add a generic `send_wait_target_reminder` Controller row for any current waiting role when reminder or liveness timing is due.
- [x] 2.7 Reconcile reminder receipts back into the pending wait metadata and card return ledger without satisfying the original ACK/result wait.

## 3. Runtime Tests

- [x] 3.1 Add or update focused tests for role-decision waits moving to monitor/standby instead of ordinary action rows.
- [x] 3.2 Add or update focused tests for card-return waits and current-scope reconciliation waits moving to monitor/standby.
- [x] 3.3 Add or update focused tests proving startup local obligations preempt passive waits and new executable work wakes standby.
- [x] 3.4 Add focused tests proving due reminders materialize for report waits and ACK waits, use Router-authored text, and update wait metadata on receipt.

## 4. Verification, Sync, And Local Git

- [x] 4.1 Run focused runtime tests, py_compile, OpenSpec validation, focused FlowGuard checks, and install/audit checks.
- [x] 4.2 Sync the repository-owned FlowPilot skill to the local installed version and verify source freshness.
- [x] 4.3 Review the final working tree, preserving compatible parallel-agent work for the shared final commit.
- [x] 4.4 Create a local git commit if verification is green and parallel-agent work is in a commit-ready state.

Note: deferred on 2026-05-16 because the shared worktree includes active parallel-agent changes that are not yet commit-ready (`openspec validate --all --strict` fails for `enforce-flowpilot-daemon-startup`, `harden-work-packet-ack-and-no-output-retry` and `replay-role-recovery-obligations` still have unchecked tasks, and the prompt-boundary regression currently fails on work-card ACK continuation text). The wait-status fix itself passed focused OpenSpec, FlowGuard, runtime, and install checks.
