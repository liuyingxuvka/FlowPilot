## Context

FlowPilot already has a two-table Router scheduler and Controller action
ledger. It also has a durable reconciliation barrier that handles many packet,
receipt, and role-output cases before computing a next action.

The remaining gap is narrower: Controller-boundary confirmation can be durable
and reconciled in action/scheduler ledgers, while the canonical Router flags
remain false. In that state the daemon can believe the same completed boundary
action is still needed. The outer daemon loop also sleeps after every tick
unless stopped, even when the queue stopped only because the tick reached its
per-tick action budget.

## Goals / Non-Goals

**Goals:**

- Reclaim Controller-boundary confirmation into Router flags whenever the
  valid artifact exists, even if there is no current pending action.
- Run that projection sync before any pending-action return or new action
  computation in both foreground and daemon paths.
- Keep Controller action ledger, Router scheduler row, artifact, and Router
  flags convergent before the daemon decides work is still open.
- Continue the daemon immediately after a `max_actions_per_tick` queue stop,
  subject to bounded loop protection, and sleep only when the tick stops at a
  real barrier or no action.
- Extend the focused FlowGuard model so representative bad cases fail before
  runtime changes are trusted.

**Non-Goals:**

- No broad rewrite of the scheduler, packet runtime, or card runtime.
- No change to Controller ownership; Controller still writes receipts and
  artifacts, Router owns projection reconciliation.
- No weakening of sealed-body boundaries.
- No heavyweight Meta or Capability model run for this pass.
- No remote GitHub push, release, or pull request.

## Decisions

1. **Use one projection sync helper, not another special next-action guard.**
   The helper reads known current-run boundary evidence and updates Router
   flags/events plus linked ledgers. It is safe to call repeatedly and is placed
   in the reconciliation barrier.

2. **Treat artifact-valid plus ledger-reconciled as enough to restore flags.**
   If action and scheduler rows already say the boundary was reconciled and the
   runtime artifact validates, the Router flags are a stale projection. Router
   must rebuild them rather than reissue the Controller action.

3. **Allow projection sync without a live pending action.**
   The observed failure had `pending_action` empty after the receipt was done.
   A repair that only works while `pending_action` still points at the boundary
   action would miss the bug.

4. **Use fast loop only for budget exhaustion.**
   `barrier`, `no_action`, and `pending_action_changed` remain sleep/stop
   reasons because they represent an external wait or state handoff. A
   `max_actions_per_tick` stop means Router intentionally paused its own queue
   drain, so the daemon may immediately start another tick.

5. **Keep bounded loop protection.**
   The per-tick queue budget remains in place, and immediate follow-up ticks
   still honor `max_ticks` and terminal conditions. This prevents an accidental
   infinite internal loop from starving external observers.

## Risks / Trade-offs

- [Risk] Router accepts a bad boundary artifact. -> Mitigation: reuse the
  existing boundary context validator and runtime-envelope checks.
- [Risk] Router flags are synced while action and scheduler rows disagree. ->
  Mitigation: FlowGuard and live projection checks require both projections to
  agree or report a finding.
- [Risk] A completed action is reissued after projection sync. -> Mitigation:
  model hazard plus runtime test asserts no second
  `confirm_controller_core_boundary` action is returned.
- [Risk] Fast looping becomes busy spinning. -> Mitigation: fast loop is only
  for `max_actions_per_tick`; no-action and barrier ticks still sleep.
- [Risk] Other agents' edits are overwritten. -> Mitigation: inspect local git
  status before edits and keep this slice to narrow files.

## Migration Plan

1. Record this plan and risk matrix.
2. Extend the focused daemon reconciliation FlowGuard model and prove known-bad
   projection and fast-loop hazards fail.
3. Run the intended model path and focused runner.
4. Implement the Router projection helper and fast-loop sleep decision.
5. Add focused runtime tests.
6. Run model/tests/install sync and update adoption evidence.

Rollback is a local git revert of this change. No remote publication is part of
the migration.

## Open Questions

- Whether future daemon slices should make fast-loop budget configurable per
  run. Default for this change: keep the existing constant and only skip sleep
  after budget exhaustion.
