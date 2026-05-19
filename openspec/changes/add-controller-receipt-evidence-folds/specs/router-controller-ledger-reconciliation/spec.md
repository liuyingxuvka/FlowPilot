## ADDED Requirements

### Requirement: Controller ledger reconciliation folds evidence before repair decisions
FlowPilot SHALL reconcile Controller action ledger rows by folding registered Router-visible relay evidence before scheduling retries, PM repair decisions, or control blockers for missing postconditions.

#### Scenario: Done receipt has stale aggregate flag but valid evidence
- **WHEN** the Controller ledger row is `done`
- **AND** the Router-owned aggregate postcondition flag is false
- **AND** packet or result relay evidence proves the registered postcondition
- **THEN** Router MUST update the aggregate flag from evidence
- **AND** Router MUST NOT ask PM to repair the already-proven relay action

#### Scenario: Evidence contradicts the receipt
- **WHEN** the Controller ledger row is `done`
- **AND** the registered evidence fold finds missing, invalid, or contradictory relay records
- **THEN** Router MUST NOT treat the Controller receipt alone as proof
- **AND** Router MUST preserve the existing retry and repair escalation behavior

### Requirement: Controller ledger reconciliation records fold outcomes
FlowPilot SHALL expose whether a relay receipt was reconciled by a registered evidence fold, by an already-true flag, or by the existing non-relay stateful handler.

#### Scenario: Evidence fold repairs stale state
- **WHEN** a registered evidence fold changes a Router-owned flag from false to true
- **THEN** Router SHOULD include an evidence-fold outcome reason in the receipt reconciliation result or traceable Controller row update
