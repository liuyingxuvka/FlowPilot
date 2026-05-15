## Why

A fresh FlowPilot run proved that daemon-first startup now happens, but the
Router daemon later exited with `JSONDecodeError`. The concrete runtime
evidence showed `runtime/router_scheduler_ledger.json` contained a complete
JSON object followed by a partial appended row fragment. The lock then moved
to `error`, while daemon status could still look active if read alone.

The previous FlowGuard models caught ordering, ACK, barrier, duplicate row, and
receipt-reconciliation problems, but treated durable ledger files as abstract
valid tables. They did not model ledger parseability after every write, atomic
write semantics, or status/lock/process consistency.

## What Changes

- Upgrade focused FlowGuard models so this class is explicit:
  - Router scheduler ledger invalid JSON after a daemon write.
  - Controller action ledger invalid JSON after a Controller write.
  - Runtime ledger writes without atomic replace semantics.
  - Router scheduler ledger having more than one writer.
  - Daemon status claiming active after lock error or missing process.
- Define the minimum production repair boundary:
  - one shared atomic JSON write helper for runtime ledgers;
  - one Router-owned scheduler ledger write path;
  - validate read-after-write for ledgers that drive daemon progress;
  - make daemon status derive liveness from lock plus process evidence;
  - on ledger corruption, stop scheduling and surface one repair state instead
    of continuing with partial data.

## Non-Goals

- Do not redesign the Router/Controller two-table protocol.
- Do not add a second startup-specific rule.
- Do not run heavyweight meta/capability regressions for this focused plan.
- Do not repair historical corrupted run files as part of the model upgrade.

## Impact

- Focused FlowGuard models and result artifacts under `simulations/`.
- Future production repair target: `skills/flowpilot/assets/flowpilot_router.py`.
- Future focused runtime tests for atomic write, corrupted ledger recovery,
  daemon status/lock consistency, and no duplicate scheduler writer.
