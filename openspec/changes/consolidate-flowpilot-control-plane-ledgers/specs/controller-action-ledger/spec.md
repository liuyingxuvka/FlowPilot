## ADDED Requirements

### Requirement: Controller receipts are durable facts before projections
Controller receipts SHALL be persisted as durable action-local facts before any
scheduler or display projection is updated.

#### Scenario: Receipt is valid but scheduler fold is deferred
- **WHEN** Controller records a valid receipt and the scheduler fold is deferred
  because the daemon owns the scheduler ledger or a write lock is fresh
- **THEN** the receipt remains durable and discoverable by action id
- **AND** the matching Controller action record exposes receipt metadata
- **AND** a later Router-owned fold reconciles scheduler and display state from
  the receipt without requiring Controller to repeat the host action.
