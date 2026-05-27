## ADDED Requirements

### Requirement: Role cohort recovery proof is transaction-fresh
FlowPilot SHALL require heartbeat/manual resume role cohort recovery to prove
the latest recovery transaction and current host addressability before any
dependent work resumes.

#### Scenario: Latest recovery transaction lacks host proof
- **WHEN** heartbeat/manual resume has requested role recovery for a stale,
  missing, unknown, or unaddressable role
- **AND** the latest recovery transaction does not have current host
  addressability proof for that role
- **THEN** Controller and Router MUST keep recovery incomplete and MUST NOT
  resume role-dependent normal work.

#### Scenario: Older all-ready report exists
- **WHEN** an older role recovery report says all six roles are ready
- **AND** a newer liveness fault transaction exists
- **THEN** heartbeat/manual resume MUST ignore the older report for readiness.
