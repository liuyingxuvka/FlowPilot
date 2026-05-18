## ADDED Requirements

### Requirement: Runtime Write-Lock Failures Are Mechanical Before Semantic

FlowPilot SHALL classify runtime JSON write-lock failures as mechanical runtime
settlement issues before routing them to PM semantic repair.

#### Scenario: Controller action file has an active runtime write lock

- **WHEN** Router encounters `RouterLedgerWriteInProgress` while reading,
  writing, or summarizing a Controller action JSON file
- **THEN** FlowPilot first records runtime write-lock wait or takeover evidence
- **AND** it SHALL NOT create a PM semantic repair blocker until bounded runtime
  settlement has failed.

#### Scenario: Runtime settlement fails after bounded recovery

- **WHEN** a runtime write-lock condition remains unresolved after bounded
  wait/takeover recovery
- **THEN** FlowPilot may materialize a control-plane blocker
- **AND** the blocker SHALL identify the failure as mechanical runtime ledger
  settlement rather than reviewer, PM, or business-task content failure.
