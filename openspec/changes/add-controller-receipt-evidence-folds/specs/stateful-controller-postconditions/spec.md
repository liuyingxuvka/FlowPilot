## ADDED Requirements

### Requirement: Stateful relay postconditions reconcile from evidence folds
FlowPilot SHALL apply registered packet/result relay evidence folds before treating a Controller `done` receipt as an unsupported stateful postcondition.

#### Scenario: Relay receipt is supported by registered evidence
- **WHEN** Controller records a `done` receipt for an evidence-backed relay action
- **AND** Router-visible evidence satisfies the registered fold for that action
- **THEN** Router MUST set the corresponding postcondition flag
- **AND** Router MUST reconcile the Controller receipt as successful
- **AND** Router MUST NOT emit `unsupported_stateful_controller_receipt`

#### Scenario: Relay receipt lacks required evidence
- **WHEN** Controller records a `done` receipt for an evidence-backed relay action
- **AND** Router-visible evidence does not satisfy the registered fold for that action
- **THEN** Router MUST leave the postcondition flag false
- **AND** Router MUST use the existing bounded retry or repair path

### Requirement: Stateful receipt folding remains idempotent
FlowPilot SHALL make registered relay receipt folds idempotent and SHALL NOT rerun ordinary relay side effects while reconciling a Controller receipt.

#### Scenario: Receipt is processed more than once
- **WHEN** Router observes the same `done` receipt and the same relay evidence on more than one scheduler tick
- **THEN** Router MUST keep the postcondition flag true
- **AND** Router MUST NOT duplicate packet relay history, active-holder leases, result relay rows, or batch counters
