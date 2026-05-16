## ADDED Requirements

### Requirement: Router closes waits satisfied by recorded external events
Router SHALL close every open `await_role_decision` Controller action row whose `allowed_external_events` contains a recorded external event.

#### Scenario: Newly recorded event satisfies a wait row
- **WHEN** Router records an external event that appears in an open wait row's `allowed_external_events`
- **THEN** Router marks that wait row satisfied from the external event and rebuilds the Controller action ledger

#### Scenario: Already-recorded event repairs stale wait row
- **WHEN** Router receives an idempotent replay of an already-recorded event and a matching wait row is still open
- **THEN** Router closes the matching wait row without recording a duplicate event

### Requirement: Router advances only after closing satisfied waits
Router SHALL close satisfied external-event wait rows before exposing a next wait row or next Controller action derived from that event.

#### Scenario: PM repair decision opens a follow-up wait
- **WHEN** Router records `pm_records_control_blocker_repair_decision` and the repair decision requires a follow-up event
- **THEN** the old PM-decision wait is no longer open before Router exposes the follow-up wait

### Requirement: Controller does not own external-event wait progression
Controller SHALL NOT be responsible for deciding that an external-event wait is satisfied.

#### Scenario: Wait closed from Router evidence
- **WHEN** a role or PM event satisfies a wait row
- **THEN** the row records Router-owned reconciliation evidence rather than requiring a Controller receipt
