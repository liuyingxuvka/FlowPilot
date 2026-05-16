## MODIFIED Requirements

### Requirement: Router closes waits satisfied by recorded external events
Router SHALL close every open `await_role_decision` Controller action row whose `allowed_external_events` contains a recorded external event.

#### Scenario: Newly recorded event satisfies a wait row
- **WHEN** Router records an external event that appears in an open wait row's `allowed_external_events`
- **THEN** Router marks that wait row satisfied from the external event and rebuilds the Controller action ledger

#### Scenario: Already-recorded event repairs stale wait row
- **WHEN** Router receives an idempotent replay of an already-recorded event and a matching wait row is still open
- **THEN** Router closes the matching wait row without recording a duplicate event

#### Scenario: Output-bearing work clears only from output event
- **WHEN** a Controller wait row represents an output-bearing work package for PM, reviewer, officer, or worker
- **AND** the matching output event in `allowed_external_events` is recorded
- **THEN** Router closes the wait row and rebuilds the Controller action ledger
- **AND** ACK evidence alone is not sufficient for this closure.
