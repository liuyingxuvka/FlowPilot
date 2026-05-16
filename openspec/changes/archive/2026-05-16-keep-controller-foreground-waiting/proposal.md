## Why

FlowPilot can keep the Router daemon alive while the foreground Controller still ends the user-visible turn after reporting that the daemon is waiting for a role. This makes active work look stopped even though the backend control loop is healthy.

## What Changes

- Add a foreground Controller standby contract for live Router-daemon waits.
- Require the foreground Controller to keep watching Router daemon status and the Controller action ledger when no immediate Controller action exists.
- Make role-wait states such as `reviewer_reports_startup_facts` nonterminal for the foreground Controller when the Router daemon is live.
- Keep `next` and `run-until-wait` as diagnostic or explicit repair tools only; standby waiting must not drive Router progress manually.
- Surface daemon death, stale locks, user-needed states, and explicit Controller actions as wait exits.

## Capabilities

### New Capabilities

- `controller-foreground-standby`: Foreground Controller standby behavior while Router daemon is live and waiting for role output or daemon-issued Controller actions.

### Modified Capabilities

- None.

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- FlowPilot runtime cards and protocol references for Controller behavior
- FlowGuard foreground/daemon liveness model and checks
- Runtime tests for daemon role-wait and foreground standby behavior
- Local installed `flowpilot` skill synchronization
