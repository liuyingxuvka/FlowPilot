## ADDED Requirements

### Requirement: Startup Settlement Does Not Reissue Retired Answer Rows
FlowPilot startup settlement SHALL preserve one current answer owner and SHALL NOT
reissue retired answer-recording rows as current Controller work.

#### Scenario: Intake side effects are complete
- **WHEN** startup intake side effects prove durable answers and seed-owned flags
- **THEN** foreground retry, daemon tick, and receipt reconciliation use that current
  owner evidence
- **AND** no retired answer-recording row is scheduled or treated as required current
  work.
