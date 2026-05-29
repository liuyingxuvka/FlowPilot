## ADDED Requirements

### Requirement: Bootstrap Describes Seed-Owned Answers Only
FlowPilot bootstrap documentation and validation SHALL describe startup answer
recording as seed-owned current work, not as a later Controller row.

#### Scenario: Deterministic seed is complete
- **WHEN** the deterministic startup seed has recorded answers for the current run
- **THEN** the scheduler excludes any later answer-recording work for the same
  answers
- **AND** user-facing or maintenance documentation SHALL NOT teach a legacy row name
  as a current startup step.
