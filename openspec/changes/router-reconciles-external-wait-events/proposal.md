## Why

FlowPilot can record the external event a role or PM returned, then leave the matching Controller wait row in `waiting`, which lets the foreground Controller see stale work even though Router has already advanced.

This must be a generic Router reconciliation rule, not a PM-specific repair path.

## What Changes

- Add Router-owned reconciliation for external events that satisfy waiting Controller action rows.
- Require Router to close every matching open wait row before it computes or exposes the next wait row.
- Preserve Controller simplicity: Controller watches and receipts host actions, while Router owns event-to-wait progression.
- Add focused FlowGuard hazards for recorded-event/stale-wait, next-wait-before-old-wait-closed, and Controller-owned wait closure.

## Capabilities

### New Capabilities
- `router-external-wait-reconciliation`: Defines how Router records external events, closes matching wait rows, and advances to the next Router-owned state.

### Modified Capabilities
- None.

## Impact

- Affects FlowPilot Router event recording, durable wait reconciliation, Controller action ledger summaries, Router scheduler row state, and focused FlowGuard validation.
- Does not change release, publish, dependency, or heavyweight meta/capability regression requirements.
