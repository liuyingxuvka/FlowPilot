## Why

FlowPilot startup currently has partial async behavior for role ACKs, but the Router daemon still tends to expose one Controller action at a time. This makes startup feel special even though the later route loop already treats work as ledgered obligations that Router can reconcile at a gate.

## What Changes

- Introduce an explicit Router scheduler table alongside the existing Controller action table.
- Keep the Controller table simple: Controller sees rows to execute, marks each row with a receipt, and does not own dependency planning.
- Make the Router daemon the startup and route driver: every one-second tick reconciles receipts and keeps enqueueing independent Controller rows until a real barrier is reached.
- When a live barrier leaves no ordinary Controller row ready, expose a stable continuous standby row so Controller keeps the visible Codex plan in-progress and watches the monitor until the next real release condition.
- Reuse the current-scope pre-review reconciliation rule for startup fact review instead of adding a startup-only gate.
- Preserve the existing PM startup activation semantics: the reviewer report plus the same-role `pm.startup_activation` ACK gate remain sufficient; no second all-startup ACK layer is added.
- Add focused FlowGuard coverage for two-table async scheduling, barrier stops, startup pre-review reconciliation, continuous standby, and duplicate side-effect hazards.

## Capabilities

### New Capabilities
- `router-two-table-async-scheduler`: Defines the Router scheduler table, Controller action table boundary, daemon enqueue rule, and unified current-scope reconciliation gate.

### Modified Capabilities
- None.

## Impact

- Affects FlowPilot Router daemon scheduling, Controller action ledger metadata, foreground standby, receipt reconciliation, and startup/current-scope review gating.
- Adds focused FlowGuard model and runtime tests.
- Does not run or require the heavyweight `simulations/run_meta_checks.py` or `simulations/run_capability_checks.py` regressions.
