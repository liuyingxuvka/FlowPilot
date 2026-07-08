## ADDED Requirements

### Requirement: Stale result submissions are rejected before result allocation

FlowPilot SHALL reject result submissions for stale, noncurrent, already
accepted, or inactive-lease packets before creating a result id, writing a
result row, appending packet result history, or advancing route state.

#### Scenario: Already accepted packet is submitted again
- **WHEN** a backend role submits a result for a packet that already has
  `accepted_result_id`
- **THEN** Runtime MUST reject the submission as an already-accepted packet
- **AND** Runtime MUST NOT allocate a new result id
- **AND** Runtime MUST NOT append to `packet.result_ids`
- **AND** Runtime MUST NOT change `packet.accepted_result_id`

#### Scenario: Noncurrent packet submits after next wait starts
- **WHEN** the current waiting packet is different from the submitted packet
- **THEN** Runtime MUST reject the submission as noncurrent
- **AND** the current waiting packet and its lease MUST remain unchanged
- **AND** no result row may be written for the old packet

#### Scenario: Closed or superseded lease submits
- **WHEN** a submission names a lease that is closed, inactive, superseded, or
  not the packet's current assigned lease
- **THEN** Runtime MUST reject the submission before result allocation
- **AND** Runtime MUST NOT route the body through ordinary result validation

### Requirement: Current role dispatch is idempotent for active packet leases

FlowPilot SHALL treat repeated `dispatch-current-role` calls for the same
current packet and active assigned lease as idempotent handoff retrieval, not
as a request to consume a new assignment or supersede the active lease.

#### Scenario: Repeated dispatch while current lease is active
- **WHEN** the current packet already has an active assigned lease for its
  requested role
- **THEN** dispatch MUST return the existing current handoff information
- **AND** dispatch MUST NOT create a new lease
- **AND** dispatch MUST NOT supersede the active lease

#### Scenario: Replacement requires modeled repair lane
- **WHEN** the active assigned lease is closed, mismatched, noncurrent, or
  otherwise invalid
- **THEN** ordinary repeated dispatch MUST NOT silently replace it
- **AND** lease replacement MUST proceed only through the existing modeled
  repair, reissue, or replacement path.
