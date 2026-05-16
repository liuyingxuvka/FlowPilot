## Context

Router daemon settlement already has the right high-level order:

1. reconcile durable Controller receipts and Router ledgers;
2. update Router state;
3. return the next action only after reconciliation.

The missing rule is how to classify evidence that is not stable yet. A fresh
writer lock, a transient `.tmp-*.json`, or a file that disappears between
directory scan and read means "someone may still be writing." That should not
be treated the same as "Router does not know how to apply this receipt."

## Decisions

1. Active writer evidence defers, it does not block.

   If a fresh runtime write lock or transient temp action file is visible, the
   daemon records/writes a waiting-for-settlement status and retries on the next
   one-second daemon tick. It does not create a PM/control blocker solely from
   active writer evidence.

2. Stalled or unsupported evidence remains a real blocker path.

   If a write lock is stale, JSON is corrupt without an active writer, or a
   receipt returns `unsupported_stateful_controller_receipt`, the existing
   blocker/repair path still applies. Waiting is not a substitute for missing
   code.

3. Startup flag folding is daemon-owned settlement.

   When run bootstrap flags show both `roles_started` and
   `role_core_prompts_injected`, the daemon folds both into Router state
   together before next-action computation. If only one flag is visible, Router
   waits for a stable pair instead of inventing a partial state.

4. Repair-transaction execution stays with the parallel change.

   This change may rely on executable repair transactions existing, but it does
   not implement new `plan_kind` behavior. That remains owned by
   `make-repair-transactions-executable`.

## Risks / Trade-offs

- [Risk] Deferring too broadly could hide a real logic bug.
  [Mitigation] Defer only for concrete active-writer evidence; unsupported
  receipt classifications still go to blocker/repair.
- [Risk] Directory scans may miss a just-written action for one tick.
  [Mitigation] The daemon wakes every second; a one-tick delay is safer than
  reading a transient file.
- [Risk] Conflicts with parallel repair-transaction work.
  [Mitigation] Do not modify repair transaction plan-kind handling in this
  change; only avoid creating blockers while writes are active.

## Migration Plan

1. Extend the focused daemon reconciliation FlowGuard model with active-writer
   settlement states and hazards.
2. Harden Controller action scans to skip transient temp files and tolerate
   disappearing scan results.
3. Raise the existing `RouterLedgerWriteInProgress` path for active mail/packet
   ledger writes so the daemon waits instead of creating a blocker.
4. Fold paired startup role flags from bootstrap into Router state during daemon
   settlement.
5. Add focused runtime tests and run lightweight model/test/install checks.
