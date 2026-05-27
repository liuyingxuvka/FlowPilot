## Why

The current FlowGuard audit found that material-scan repair can still drift across existing ledgers: a PM repair transaction, material packet generation, Controller action replay, Controller receipt fold, role-output event replay, and PM package disposition can each look locally valid without proving they belong to the same current material generation.

This change strengthens the existing repair and control transaction flows. It does not introduce a parallel repair workflow.

## What Changes

- Extend the existing `repair_transaction` material packet-reissue path so the material index, active parallel packet batch, packet ledger projection, and recheck outcome all share one current `packet_generation_id`.
- Tighten existing `operation_replay` so it creates a fresh Controller action from replay intent and current state instead of preserving stale action identity or stale packet-generation context.
- Complete the existing `controller_repair_work_packet` receipt fold path so a done Controller receipt updates the owning repair transaction before Router clears the pending action.
- Extend PM package disposition handling so material-scan dispositions only close waits when the active batch, packet ids, and current material generation match.
- Extend existing scoped event idempotency for PM package dispositions so role-output body references and current batch/generation prevent duplicate side effects.
- Close the existing break-glass patch lifecycle after validation instead of leaving validated temporary patches with no final disposition.
- Add FlowGuard and focused runtime coverage for these obligations, then run install sync and local checks after owned source validation.

## Capabilities

### New Capabilities

- None. This change upgrades existing FlowPilot control-plane capabilities.

### Modified Capabilities

- `executable-repair-transactions`: Material packet reissue and operation replay must be current-generation scoped and replayable through existing repair transactions.
- `controller-action-ledger`: `controller_repair_work_packet` done receipts must fold into the owning repair transaction before pending action clearance.
- `router-external-wait-reconciliation`: PM package disposition waits must close only after current-generation transaction completion or quarantine.
- `packet-open-authority-exits`: Material result authority must remain tied to current packet/batch generation and replayable packet-result author evidence.
- `stateful-controller-postconditions`: Stateful Controller receipt repair remains bounded and must not treat receipt metadata alone as transaction completion.

## Impact

- Affected runtime assets: repair transaction material commit helpers, repair execution/action helpers, Controller receipt reconciliation, PM package disposition writer, scoped event identity policy, break-glass lifecycle helper, and router facade exports.
- Affected FlowGuard models: control-plane friction, repair transaction, PM package absorption, role-output runtime/event idempotency, controller break-glass, control transaction registry, and parent meta/capability confidence.
- Affected tests: focused router runtime material/modeling, control-blocker, foreground Controller, PM disposition/control contracts, role-output idempotency, controller break-glass, and install freshness checks.
- No dependency, stack, release, deployment, or public publication change is included.
