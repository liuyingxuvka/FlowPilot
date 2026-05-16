## Why

Startup pre-review reconciliation can currently block on its own
`await_current_scope_reconciliation` passive wait status row. That leaves
FlowPilot looking alive but stuck after the real startup obligations have
already been reconciled.

## What Changes

- Treat Router-owned passive wait/status projections as non-blocking evidence
  during startup pre-review reconciliation.
- Keep real startup-local obligations blocking: missing startup flags,
  unresolved card returns, unreconciled ordinary Controller work, and active
  local control blockers still prevent Reviewer startup fact work.
- Add focused FlowGuard and Router runtime coverage for the self-block case.
- Keep heavyweight Meta and Capability model runs skipped for this pass by user
  request.

## Capabilities

### New Capabilities
- `startup-reconciliation-passive-wait`: Defines how startup pre-review
  reconciliation treats Router-owned passive wait status rows.

### Modified Capabilities
- None.

## Impact

- Affected code: `skills/flowpilot/assets/flowpilot_router.py`.
- Affected tests: focused Router runtime tests for startup pre-review
  reconciliation.
- Affected models: focused current-scope pre-review FlowGuard model and result
  JSON.
- Installation: repository-owned FlowPilot skill must be synced to the local
  installed skill after validation.
