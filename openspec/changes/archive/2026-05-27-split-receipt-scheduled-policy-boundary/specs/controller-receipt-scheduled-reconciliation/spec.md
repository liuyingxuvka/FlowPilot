## MODIFIED Requirements

### Requirement: Scheduled Controller receipts reconcile through finite policy helpers
FlowPilot SHALL keep scheduled Controller receipt reconciliation policy helpers
separately testable from the filesystem scan/orchestration loop.

#### Scenario: Scheduled receipt policy is internally split without changing the parent entrypoint
- **WHEN** FlowPilot scans scheduled Controller action receipts
- **THEN** the scheduled receipt parent still exposes the existing helper names
  and `_reconcile_scheduled_controller_action_receipts` entrypoint
- **AND** the policy child MUST own scheduler-row reconciliation lookup,
  backfill, pending-action clearing, and apply-result classification
- **AND** the parent MUST consume the child boundary rather than duplicating
  those policy rules

#### Scenario: Scheduled receipt policy output vocabulary stays closed
- **WHEN** the policy child classifies receipt apply results
- **THEN** it MUST return only `reconciled`, `retry_pending`,
  `repair_pending`, or `blocked`
- **AND** pending-action clearing MUST only clear a pending action when one of
  the declared action-id, scheduler-row, idempotency, postcondition, or label
  matches is present
