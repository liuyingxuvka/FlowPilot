## Why

FlowPilot's daemon can observe a Controller receipt before Router-owned durable evidence has been reclaimed into Router state. That creates false control blockers: Controller has finished its local action and the file proof exists, but Router still sees an unsatisfied flag and stops the run.

This change separates Controller-local completion from Router-owned workflow completion, then requires Router to reconcile both ledgers before choosing the next action or creating a blocker.

## What Changes

- Add a Router-owned control ledger that records ownership, waiting, durable artifact reclaim, and postcondition decisions separately from the Controller action ledger.
- Classify Controller actions so a Controller receipt can mean either local delivery completion, Router-owned artifact reclaim needed, lightweight display/status completion, or true stateful host completion.
- Reconcile Controller receipts, Router-owned artifacts, and role-output waits before every daemon next-action decision.
- Reclaim valid Router-owned startup mechanical audit artifacts from disk before creating a stateful postcondition blocker.
- Preserve existing startup route-sign/display timing; this change does not move the startup display action earlier.
- Keep heavyweight `run_meta_checks.py` and `run_capability_checks.py` out of this validation pass per the user's instruction.

## Capabilities

### New Capabilities
- `router-controller-ledger-reconciliation`: Controller action receipts and Router-owned workflow completion are tracked separately and reconciled before progress/blocker decisions.

### Modified Capabilities
- None.

## Impact

- Affected runtime: `skills/flowpilot/assets/flowpilot_router.py`.
- Affected tests: focused Router runtime tests for Controller receipts, Router-owned artifact reclaim, and daemon tick reconciliation.
- Affected models: FlowGuard control-plane friction model/check results and adoption logs.
- No dependency, public API, startup-display timing, or heavyweight meta/capability regression change is intended.
