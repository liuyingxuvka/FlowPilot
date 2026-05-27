## Why

FlowPilot can still mark a PM package disposition event as recorded from the
role-output ledger before the matching domain artifact has been committed. That
lets a failed source result self-check look like progress, closes the PM wait,
and later leaves the router with no legal next action.

## What Changes

- Require role-output ledger reconciliation to perform the same domain commit
  as direct external-event intake before setting event flags, event history,
  idempotency records, or wait closure.
- Treat PM package disposition reconciliation for material, research, and
  current-node packages as a single transaction boundary.
- Preserve the existing stale/conflicting replay quarantine work, but keep it
  as a pre-commit guard instead of a replacement for the domain commit.
- Add focused regression coverage for bad source result `contract_self_check`
  and adjacent PM package disposition families.
- Promote the recurring PM package disposition failure into a defect-family
  closure gate: authority state must stay consistent across event identity,
  flags, batch state, material artifacts, role-output replay, daemon startup,
  repair ownership, and live-run audit evidence.
- Update FlowGuard/model evidence, generated simulation outputs, and installed
  FlowPilot runtime assets after the fix.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `role-output-transaction-boundaries`: Role-output ledger reconciliation must
  not record router event progress until the event's domain commit succeeds.
- `control-plane-friction-root`: Failed source result self-checks must be
  blocked before any PM package disposition event can close control-plane waits.

## Impact

- Runtime router reconciliation helpers for direct role-output ledger events.
- PM package disposition transaction behavior for material, research, and
  current-node result packages.
- Control-plane friction FlowGuard scenarios and focused router regression
  tests.
- Installed FlowPilot skill/runtime assets that mirror repository changes.
