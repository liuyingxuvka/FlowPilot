## MODIFIED Requirements

### Requirement: Router reconciles before choosing next action or blocker

FlowPilot SHALL run a reconciliation barrier before every daemon next-action decision, manual next-action decision, and control-blocker creation.

#### Scenario: Packet result receipt fold has batch side effects
- **WHEN** Controller receipt evidence folds a packet/result relay postcondition
- **THEN** Router MUST apply all lifecycle side effects owned by that fold, including durable packet-batch status and Router projection refresh where applicable
- **AND** Router MUST NOT treat a flag-only fold as sufficient when a durable lifecycle record is still stale

#### Scenario: Cross-ledger disagreement is detected before next action
- **WHEN** Controller receipts, packet batches, PM role-work indexes, lifecycle indexes, or Router projections disagree about the same logical obligation
- **THEN** Router MUST reconcile the disagreement from durable evidence before exposing new work
- **AND** if reconciliation cannot prove a safe state, Router MUST surface an explicit control blocker instead of continuing from stale projection state
