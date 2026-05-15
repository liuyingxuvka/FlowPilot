## Root Cause

The actual failure was not startup ordering. Startup ordering passed:
the daemon started before startup UI and before startup rows. The failure was
below that layer: a runtime ledger file was not protected as a durable table.

The scheduler ledger must be treated like a tiny database table. If two code
paths can write it, or if a write can leave a partial file visible, the daemon
can read malformed JSON and stop. If daemon status is then read without checking
the lock and process, the system may report a live daemon even after the lock
was released with an error.

## Minimal Architecture

Use one runtime-ledger persistence lane:

1. `read_json_strict(path)` for daemon-critical ledgers.
   - Invalid JSON is not ignored.
   - It becomes a Router-visible repair blocker or daemon error state.

2. `write_json_atomic(path, payload)`.
   - Write to a temp file in the same directory.
   - Flush and close it.
   - Atomically replace the target.
   - Read back and parse the final target for daemon-critical ledgers.

3. Single writer ownership.
   - Router owns `router_scheduler_ledger.json`.
   - Controller writes receipts and its own action artifacts only.
   - Any helper that mutates Router scheduler rows must run through the Router
     write lane while the daemon/run lock is held.

4. Status is derived, not trusted alone.
   - A daemon is live only when lock status, timestamp freshness, and process
     evidence agree.
   - If the lock says `error`, status cannot claim `daemon_active`.

## Why This Is Minimal

This fixes the common foundation rather than every symptom. We do not add
special cases for startup UI, heartbeat, or Controller core. We make the two
tables durable and make daemon liveness truthful. That directly covers the
observed `JSONDecodeError` and prevents the same shape from reappearing in
later runtime ledgers.

## Validation

Focused validation should include:

- FlowGuard scheduler model rejects partial Router/Controller ledger writes.
- FlowGuard persistent daemon model rejects active status after lock error or
  missing process.
- Runtime test corrupts `router_scheduler_ledger.json` and verifies daemon
  stops scheduling and surfaces repair evidence.
- Runtime test verifies scheduler writes remain valid JSON across repeated
  daemon/controller receipt reconciliation.
