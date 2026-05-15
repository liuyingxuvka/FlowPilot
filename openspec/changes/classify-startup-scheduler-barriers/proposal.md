# Classify Startup Scheduler Barriers

## Why

FlowPilot now has a Router scheduler table and a Controller action table, but
some startup actions still behave as barriers because the runtime classifies
them by mechanics such as `requires_payload`, `requires_host_spawn`,
`requires_host_automation`, or display confirmation. That is too broad.

The scheduling decision should depend on whether the next Router action truly
depends on the current action. Startup banner display, role-slot spawn,
heartbeat binding, and display/status writes are obligations that must be
reconciled before the startup Reviewer gate, but they should not prevent Router
from queueing unrelated startup work.

## What Changes

- Introduce an explicit scheduler progress classification:
  `true_barrier`, `phase_handoff`, `parallel_obligation`, and
  `local_dependency`.
- Demote startup banner, heartbeat binding, and startup display/status work
  from broad barriers to parallel startup obligations.
- Demote startup role-slot spawn from broad barrier to a local dependency that
  blocks only role-dependent work.
- Keep real user input, terminal actions, control blockers, resume/rehydration
  gates, non-startup ACK/result waits, and current-scope review waits as true
  barriers.
- Keep the startup Reviewer fact review as the join point: before Reviewer
  live startup review, Router must reconcile all startup Controller rows,
  role-slot evidence, heartbeat binding, banner/display evidence, prep ACKs,
  and startup-local blockers.
- Preserve and extend the existing FlowGuard work for stale bootstrap pending
  actions so done startup receipts advance bootstrap flags, clear pending
  state, reconcile scheduler rows, and do not reissue completed work.

## Capabilities

- Modified: FlowPilot two-table Router scheduler.
- Modified: FlowPilot startup bootloader scheduling.
- Modified: FlowPilot startup pre-review reconciliation.
- Modified: FlowPilot daemon receipt reconciliation.

## Impact

- Startup can queue independent work earlier without weakening startup review.
- Controller continues to execute Router-authorized rows only.
- No new startup-only table, no Controller dependency authority, no release or
  remote push.
- Heavyweight meta/capability model regressions are explicitly skipped for this
  change by user request; focused FlowGuard models and runtime tests are still
  required before implementation and after each slice.
