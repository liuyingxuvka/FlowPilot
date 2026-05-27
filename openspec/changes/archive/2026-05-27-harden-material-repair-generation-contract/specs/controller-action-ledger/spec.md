## ADDED Requirements

### Requirement: Controller repair work packet receipts fold repair transactions
FlowPilot SHALL reconcile `controller_repair_work_packet` done receipts into the owning repair transaction before clearing the active Router pending action.

#### Scenario: Done receipt updates repair transaction
- **WHEN** Controller writes a `done` receipt for a Router-authored `controller_repair_work_packet`
- **THEN** Router MUST verify the action cannot approve gates, mutate routes, or read sealed bodies
- **AND** Router MUST write the receipt result into the matching repair transaction
- **AND** Router MUST move the transaction to a recheck state before clearing the pending action

#### Scenario: Missing transaction blocks clearance
- **WHEN** Controller writes a `done` receipt for `controller_repair_work_packet` but Router cannot update the matching repair transaction
- **THEN** Router MUST preserve or create a control blocker
- **AND** Router MUST NOT treat the Controller receipt alone as repair completion.
