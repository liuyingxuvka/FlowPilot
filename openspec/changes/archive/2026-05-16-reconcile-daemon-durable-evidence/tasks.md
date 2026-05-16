## 1. Model And Contract

- [x] 1.1 Add a FlowGuard reconciliation model that separates durable evidence from Router state.
- [x] 1.2 Add executable checks for stale pending action, receipt-only completion, role-output ledger submission, canonical artifact drift, stale snapshot overwrite, and barrier ordering.
- [x] 1.3 Run the new reconciliation model and inspect its known-bad hazards before production edits.
- [x] 1.4 Add a lifecycle-wide daemon microstep model for startup, route work, role waits, external events, repair, and terminal cleanup.
- [x] 1.5 Add executable hazards for reading too little, stale startup pending action, stale Router facts, durable-only role output, unclosed external event waits, premature repair blockers, premature terminal status, wrong table ownership, and stale daemon summaries.

## 2. Router Runtime

- [x] 2.1 Add a durable reconciliation barrier before returning pending actions or computing new actions.
- [x] 2.2 Reconcile pending Controller receipts into Router state, clearing completed/blocked pending actions and surfacing incomplete stateful receipts as blockers.
- [x] 2.3 Reconcile valid startup fact role-output ledger entries into canonical report artifacts, Router flags, and Router events idempotently.
- [x] 2.4 Ensure daemon ticks reload or save the reconciled state so stale snapshots do not overwrite newer durable evidence.

## 3. Runtime Tests

- [x] 3.1 Add a test proving a completed pending Controller action is not returned again after a receipt.
- [x] 3.2 Add a test proving an incomplete stateful rehydration receipt becomes a repair blocker instead of silent success or repetition.
- [x] 3.3 Add a test proving a submitted startup fact role-output runtime envelope is consumed by Router reconciliation without a manual role handoff.
- [x] 3.4 Add a test proving canonical startup fact artifact drift is synced back to Router flags/events once.

## 4. Verification And Sync

- [x] 4.1 Run focused runtime tests and the daemon reconciliation FlowGuard check.
- [x] 4.2 Start heavyweight meta/capability regressions in the standard background log contract and inspect artifacts.
- [x] 4.3 Run install check, sync, audit, and installed-skill check.
- [x] 4.4 Stage and commit the local repository, preserving unrelated peer-agent changes.
- [x] 4.5 Run the lifecycle microstep model and rerun the focused two-table and persistent daemon FlowGuard checks, skipping heavyweight meta/capability checks at current user direction.
