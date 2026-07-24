## ADDED Requirements

### Requirement: Repeated progress is coalesced without weakening liveness
After ACK, a role progress update SHALL persist only when its finite status
changes or the existing liveness reminder is due.  An identical status inside
the liveness window SHALL return `coalesced=true` without incrementing
`progress_count`, appending a progress event, or saving the ledger.

#### Scenario: Repeated working status inside the window
- **WHEN** a role submits `working` repeatedly before the ten-minute result reminder is due
- **THEN** the first eligible update persists and later identical updates are coalesced
- **AND** ACK and result reminder/replacement deadlines remain unchanged

#### Scenario: Status changes to verifying
- **WHEN** a role changes from `working` to `verifying`
- **THEN** the progress transition persists immediately with the existing `last_progress_at`, `last_progress_status`, and `progress_count` fields

#### Scenario: Reminder becomes due
- **WHEN** a role remains in the same status until the existing liveness reminder is due
- **THEN** one due liveness update persists even though the status text is unchanged
