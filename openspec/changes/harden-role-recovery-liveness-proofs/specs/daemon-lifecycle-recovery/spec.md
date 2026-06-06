## ADDED Requirements

### Requirement: Role cohort recovery proof is transaction-fresh
FlowPilot SHALL require current role-binding recovery to prove the latest
recovery transaction and current host addressability before any dependent work
resumes.

#### Scenario: Latest recovery transaction lacks host proof
- **WHEN** current resume or a mid-run liveness fault has requested role
  recovery for a stale, missing, unknown, or unaddressable role
- **AND** the latest recovery transaction does not have current host
  addressability proof for that role
- **THEN** Controller and Router MUST keep recovery incomplete and MUST NOT
  resume role-dependent normal work.

#### Scenario: Older all-ready role-binding report exists
- **WHEN** an older role-binding recovery report says prior bindings are ready
- **AND** a newer liveness fault transaction exists
- **THEN** current recovery MUST ignore the older report for readiness.
