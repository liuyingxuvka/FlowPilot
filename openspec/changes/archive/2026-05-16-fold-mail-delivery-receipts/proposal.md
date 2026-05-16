## Why

The live FlowPilot run exposed a receipt/ledger mismatch: Controller recorded a
successful `deliver_mail` receipt for `user_intake`, but Router could not fold
that receipt into `packet_ledger.mail` or the
`user_intake_delivered_to_pm` flag. The packet therefore stayed with
Controller, the postcondition remained false, and the run escalated into a
mechanical control blocker.

## What Changes

- Fold `deliver_mail` Controller receipts through the same Router-owned
  packet/mail ledger update used by the direct apply path.
- Keep the fold idempotent: repeated reconciliation of the same mail delivery
  must not duplicate mail ledger rows or counters.
- Treat a mail-delivery receipt as complete only when the Router flag and
  packet/mail ledger agree.
- Preserve the existing mechanical control-plane blocker and PM escalation
  behavior when folding cannot be proven.
- Consume PM repair decisions for mail-delivery blockers into a repair
  transaction/reissue path before continuing the same wait.

## Capabilities

### New Capabilities

- `mail-delivery-receipt-folding`: Covers how FlowPilot reconciles
  Controller `deliver_mail` receipts into Router state, packet/mail ledger, and
  repair transactions.

### Modified Capabilities

- None.

## Impact

- Affected runtime: `skills/flowpilot/assets/flowpilot_router.py`.
- Affected validation: daemon reconciliation FlowGuard model/projection and
  focused Router runtime tests.
- No dependency or public API changes.
- Heavyweight Meta/Capability simulations are skipped by user direction for
  this focused control-plane fix.
