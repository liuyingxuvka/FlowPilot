## Why

The existing repair-loop break-glass gate catches long normalized same-family repair chains, but it can still be too broad for ordinary repeated mistakes across different route nodes and too noisy when old repair records appear in current status. ProjectRadar exposed the need for a narrower rule: break-glass only when the same current node repeatedly fails on the same problem, while stale repair history remains audit-only and ledger reads stay robust during active writes.

## What Changes

- Restrict repair-loop break-glass to more than five consecutive same-node, same-problem repair attempts.
- Treat cross-node similar failures as normal PM/reviewer repair unless the same node's consecutive loop threshold is exceeded.
- Keep stale repair records as ledger history while excluding noncurrent repair rows from current status/final-preflight blockers.
- Harden runtime ledger persistence with atomic write replacement and bounded transient read retry for incomplete JSON.
- Keep the repair minimal: no new packet type, no broad semantic classifier, no persistent repair-family field mesh, and no compatibility path for old protocol shapes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `blocker-repair-policy`: same-node consecutive repair-loop threshold and stale-history/current-status separation.
- `controller-break-glass-repair`: break-glass trigger is limited to same-node consecutive repeat loops, not cross-node similar failures.
- `runtime-ledger-persistence`: runtime ledger read/write behavior must avoid partial JSON exposure and tolerate transient incomplete reads.
- `controller-user-status`: current status must not present noncurrent repair history as active work.

## Impact

- Runtime repair-loop review in `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`.
- Ledger persistence helpers in `runtime.py`.
- Narrow card wording for Reviewer, FlowGuard Operator, Controller, and break-glass guidance.
- Focused runtime tests, card coverage tests, FlowGuard model checks, topology rebuild/check, and local install sync.
