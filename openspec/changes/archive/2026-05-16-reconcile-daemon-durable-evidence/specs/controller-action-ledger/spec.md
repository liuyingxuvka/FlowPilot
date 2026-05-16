## MODIFIED Requirements

### Requirement: Controller receipts affect Router pending-action state
Controller receipts SHALL be reconciled into both the Controller action ledger
and the active Router pending-action state before Router returns more work.

#### Scenario: Receipt marks active action blocked
- **WHEN** Controller writes a `blocked` receipt for the active pending action
- **THEN** Router MUST mark the action blocked in the ledger
- **AND** Router MUST clear the active pending action
- **AND** Router MUST surface a control blocker for repair routing

#### Scenario: Receipt marks active stateless action done
- **WHEN** Controller writes a `done` receipt for an active pending action whose Router postconditions are already complete or not stateful
- **THEN** Router MUST mark the action done in the ledger
- **AND** Router MUST clear the active pending action before computing the next action

#### Scenario: Receipt marks active stateful action done
- **WHEN** Controller writes a `done` receipt for an action that requires Router-owned stateful postconditions
- **THEN** Router MUST apply those postconditions from a complete receipt payload or produce a repair blocker
- **AND** Router MUST NOT rely on the receipt metadata alone as proof that the postconditions were written
