## Context

FlowPilot currently persists control-plane facts across several durable surfaces: role-output ledgers, Controller action rows, Router scheduler rows, Router events/flags, and `router_state.pending_action`. The recent material-sufficiency run proved that some of those surfaces can agree that a role event completed a wait while `pending_action` and daemon status still project the old wait as current work.

The focused FlowGuard control-plane consistency model now represents this miss class with three known-bad cases: role-output event left only in durable storage, resolved wait rows still authorizing pending action, and reconciled waits still generating reminders.

## Goals / Non-Goals

**Goals:**

- Reconcile any authorized direct role-output event into canonical Router events/flags before work selection.
- Invalidate pending-action projections when their Controller action row or Router scheduler row is already resolved.
- Prevent daemon status, current-work summaries, and reminders from using a stale pending action after durable wait resolution.
- Keep the fix narrow enough to avoid physical ledger consolidation or unrelated material-artifact-map changes.

**Non-Goals:**

- Do not merge Controller and Router ledgers.
- Do not change role-output body visibility rules.
- Do not change the semantic material-sufficiency decision contract.
- Do not run heavyweight Meta/Capability models as a prerequisite for this focused repair.

## Decisions

### Use a generic role-output event fold

Direct role outputs already carry `event_name` and runtime validation metadata. Reconciliation should therefore consume authorized ledger entries by event identity, materialize their registered side effects, and call the same Router event recording path used by live `record_external_event`.

Alternative considered: add another one-off material-sufficiency reconciler. That would fix this incident but preserve the same miss class for future PM/reviewer/officer events.

### Treat pending action as projection, not authority

Before any pending action drives status, reminder, or next work, Router must validate its `controller_action_id` and `router_scheduler_row_id` against durable ledgers. Closed, done, reconciled, resolved, superseded, or canceled rows invalidate the pending projection.

Alternative considered: clear `pending_action` only when the role-output reconciler changes state. That leaves stale pending actions from receipt, scheduler, or save-merge paths.

### Keep reconciliation before all outward projections

The same barrier must run before daemon next-action selection, daemon status/current-work derivation, and reminder creation. This keeps the user-visible control plane aligned with durable facts.

Alternative considered: only change daemon next-action computation. That would still allow status or reminders to tell the user that a completed role wait is active.

## Risks / Trade-offs

- Replaying an already-consumed role output could duplicate events. Mitigation: consume by stable role-output receipt/body/event identity and keep idempotent event recording.
- Invalid role outputs could be folded into Router state. Mitigation: require existing runtime validation and expected event authorization before folding.
- Pending-action validation could hide a real live wait if ledger lookup is incomplete. Mitigation: only invalidate when durable row state is explicitly closed/resolved; missing rows remain conservative.
- Parallel agent edits may touch adjacent files. Mitigation: keep edits to control-plane reconciliation, status/current-work, focused tests, and OpenSpec artifacts.

## Migration Plan

1. Add FlowGuard obligations and focused runtime tests for the observed miss class.
2. Implement the generic role-output event reconciler and pending-action authority validation.
3. Run focused FlowGuard and runtime checks.
4. Sync the installed FlowPilot skill from repository source and verify install freshness.
5. Stage or commit only scoped files after checking parallel-agent dirty state.
