## Context

The Controller action ledger now separates ordinary executable Controller work
from passive wait status projections. Startup pre-review reconciliation still
scans the controller action JSON files directly, so it can see a passive
`await_current_scope_reconciliation` row and misclassify it as an unresolved
startup Controller row.

## Goals / Non-Goals

**Goals:**
- Prevent startup pre-review reconciliation from self-blocking on its own
  passive wait row.
- Preserve blocking for ordinary startup Controller rows until they are closed
  and Router-reconciled.
- Preserve existing card-return and active-control-blocker joins.
- Capture the rule in focused FlowGuard and runtime regression tests.

**Non-Goals:**
- Do not change the Controller action ledger schema.
- Do not weaken startup review gates or make ACKs count as semantic work.
- Do not rewrite current-node reconciliation logic.
- Do not run the heavyweight Meta or Capability models in this pass.

## Decisions

1. Skip passive wait/status rows before adding startup Controller-row blockers.
   - Rationale: passive waits describe Router state; they are not Controller
     work and do not require Controller receipts.
   - Alternative considered: special-case only the current pending action id.
     Rejected because stale historical passive wait rows have the same
     non-work semantics and can cause the same false blocker.

2. Use the existing passive-wait projection metadata.
   - Rationale: `_action_is_passive_wait_status`,
     `controller_projection_kind=passive_wait_status`, and
     `controller_receipt_required=false` already define the queue boundary.
   - Alternative considered: add a startup-specific skip list. Rejected because
     it would duplicate the Controller queue boundary and drift.

3. Keep the fix at the blocker-scan boundary.
   - Rationale: the wait-clearing path already recomputes blockers before
     clearing `pending_action`; once the false blocker disappears, existing
     logic can continue without state migration.
   - Alternative considered: mutate existing wait rows on disk. Rejected
     because the bug is a classification issue, not stale data requiring
     destructive repair.

## Risks / Trade-offs

- [Risk] A future passive wait with side effects could be skipped. Mitigation:
  use the existing passive-wait helper, which only classifies wait action types
  without `controller_side_effect_required`.
- [Risk] Focused checks do not prove every project-control path. Mitigation:
  run the targeted FlowGuard model, focused Router tests, install checks, and
  non-heavy background regressions while recording the skipped heavyweight
  models explicitly.

## Migration Plan

1. Update focused OpenSpec, FlowGuard model, and Router test coverage.
2. Patch the startup pre-review Controller-row scan to ignore passive wait
   status rows.
3. Run focused tests and non-heavy background checks.
4. Sync the local installed FlowPilot skill from the validated repository
   source.
