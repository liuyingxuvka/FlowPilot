## ADDED Requirements

### Requirement: Repair Transactions Use Current Families Only
FlowPilot executable repair transactions SHALL use current transaction families
only and SHALL reject deprecated compatibility repair kinds.

#### Scenario: Current repair transaction is submitted
- **WHEN** a current repair transaction family is submitted with a valid current
  body
- **THEN** FlowPilot validates and commits it according to the current
  transaction registry

#### Scenario: Deprecated repair transaction is submitted
- **WHEN** a transaction uses `event_replay`, `legacy_reconcile`, or a
  compatibility-only policy value
- **THEN** FlowPilot rejects the transaction as unsupported
- **AND** FlowPilot SHALL NOT convert it into a current repair transaction
