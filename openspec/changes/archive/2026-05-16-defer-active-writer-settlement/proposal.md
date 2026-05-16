## Why

The daemon already settles durable Controller and Router evidence before
returning work, but live audit showed a missing distinction: evidence can be
temporarily incomplete because another writer is still active. Treating that
case as corruption or a postcondition failure can create false blockers or stop
the daemon.

## What Changes

- Treat fresh JSON write locks, transient `.tmp-*.json` files, and
  disappearing files during directory scans as active settlement evidence, not
  immediate blocker evidence.
- Fold startup role flags from the run bootstrap record into Router state on
  daemon ticks once the paired flags are stable.
- Keep `deliver_mail` receipt folding on the existing mail-delivery helper, but
  defer blocker creation when the packet/mail ledger is actively being written.
- Preserve the parallel executable repair-transaction work: unsupported or
  non-executable repair decisions remain owned by
  `make-repair-transactions-executable`.

## Impact

- Affected runtime: `skills/flowpilot/assets/flowpilot_router.py`.
- Affected validation: daemon reconciliation FlowGuard model/checks and focused
  Router runtime tests.
- Heavyweight Meta/Capability simulations are skipped by user direction.
