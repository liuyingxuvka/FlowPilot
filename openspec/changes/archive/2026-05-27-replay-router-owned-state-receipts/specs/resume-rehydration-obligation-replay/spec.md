## ADDED Requirements

### Requirement: Resume state load remains Router-owned under receipt projection
Heartbeat and manual resume SHALL preserve Router ownership of resume state
loading even when `load_resume_state` is represented by a Controller action
receipt.

#### Scenario: Resume load receipt sets resume state through Router replay
- **WHEN** `heartbeat_or_manual_resume_requested` has been recorded
- **AND** Controller records a valid `done` receipt for `load_resume_state`
- **THEN** Router MUST replay the registered `load_resume_state` Router action
  handler
- **AND** Router MUST set `resume_state_loaded` through that Router replay
  before evaluating resume rehydration or PM resume-decision work

#### Scenario: Resume receipt without Router replay cannot advance resume
- **WHEN** Controller records a valid `done` receipt for `load_resume_state`
- **AND** Router cannot replay the registered Router-owned state loader path
- **THEN** Router MUST NOT deliver downstream resume cards or mark resume state
  loaded from the receipt alone
- **AND** Router MUST surface a concrete control-plane blocker or incomplete
  action state

### Requirement: Resume recovery reissues missing waits in original creation order
Router SHALL preserve the durable creation order of missing Controller waits
when resume or role recovery mechanically reissues replacement obligations.

#### Scenario: Multiple missing waits are reissued in creation order
- **WHEN** role recovery finds multiple missing Controller waits for the same
  recovered role
- **THEN** Router MUST assign replacement obligations in the original durable
  Controller action creation order
- **AND** the first replacement MUST become the pending action before later
  replacements

#### Scenario: Same timestamp does not reorder waits
- **WHEN** two Controller waits have identical or indistinguishable timestamp
  precision
- **THEN** Router MUST use durable Controller action creation sequence metadata
  before falling back to action id or path ordering
