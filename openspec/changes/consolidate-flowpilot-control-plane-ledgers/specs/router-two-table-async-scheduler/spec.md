## ADDED Requirements

### Requirement: Scheduler ledger has one live mutation lane
Router scheduler rows SHALL be mutated through one live Router-owned lane while
daemon mode is active.

#### Scenario: Receipt reconciliation wants scheduler update
- **WHEN** Controller receipt reconciliation identifies a scheduler row that can
  be marked done, blocked, superseded, or reconciled
- **THEN** it submits that fact to the Router-owned fold lane
- **AND** it SHALL NOT also rewrite the scheduler row through an independent
  foreground path.

#### Scenario: No live daemon owns the run
- **WHEN** no live daemon lock exists and foreground recovery is explicitly
  operating as the Router-owned fallback lane
- **THEN** the foreground path may perform the scheduler fold
- **AND** it records that fallback ownership in the reconciliation result.
