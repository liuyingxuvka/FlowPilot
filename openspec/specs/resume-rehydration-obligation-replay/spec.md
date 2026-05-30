# resume-rehydration-obligation-replay Specification

## Purpose
TBD - created by archiving change replay-resume-rehydration-obligations. Update Purpose after archive.
## Requirements
### Requirement: Resume rehydration SHALL run Router obligation replay before default PM resume

Router SHALL run metadata-only obligation replay before delivering a PM resume
decision card after heartbeat or manual resume restores or replaces the six
role bindings, unless current-run memory or resume state is missing.

#### Scenario: Heartbeat resume replays mechanical obligations

- **WHEN** `heartbeat_or_manual_resume_requested` has been recorded
- **AND** `load_resume_state` has loaded current-run state and daemon evidence
- **AND** `rehydrate_role_bindings` reports all runtime roles ready with current-run memory or common context
- **THEN** Router scans current-run outstanding waits for the restored roles before delivering `pm.resume_decision`

#### Scenario: Manual resume shares the same replay path

- **WHEN** a manual resume wake follows the same state load and runtime-role rehydration path
- **THEN** Router uses the same obligation replay rules as heartbeat resume

### Requirement: Mechanical resume replay SHALL avoid PM when evidence is unambiguous

Router SHALL settle valid existing evidence or issue durable replacement
obligations after resume rehydration without asking PM solely to acknowledge
role freshness.

#### Scenario: Existing evidence settles resume wait

- **WHEN** a resumed role has an outstanding ACK or output wait
- **AND** current-run evidence already satisfies the expected role, card or packet, return kind, and hash
- **THEN** Router marks the original wait satisfied through resume obligation replay
- **AND** Router does not deliver `pm.resume_decision` solely because the role was rehydrated

#### Scenario: Missing evidence creates replacement work

- **WHEN** a resumed role has an outstanding wait with missing or invalid evidence
- **THEN** Router creates a replacement obligation linked to the original wait
- **AND** Router marks the original wait superseded only after the replacement row is durable
- **AND** Router exposes the replacement row before PM resume decision

### Requirement: Resume replay SHALL preserve PM escalation boundaries

Router SHALL still deliver PM resume decision when replay cannot mechanically
determine safe continuation.

#### Scenario: Ambiguous resume still asks PM

- **WHEN** resume state is ambiguous, current-run memory is incomplete, packet ownership conflicts, outputs conflict, or replay would change route scope or acceptance criteria
- **THEN** Router records PM escalation and delivers `pm.resume_decision`
- **AND** Controller does not choose the winning output or continue from chat history

#### Scenario: No legal replay path asks PM or blocks

- **WHEN** no outstanding obligation can be settled or reissued and the next safe action is not mechanically derivable
- **THEN** Router asks PM for recovery/repair/stop decision or records a control blocker

### Requirement: Historical replay packages cover host role lifecycle recovery
The system SHALL include host/role lifecycle replay packages that require full
runtime-role liveness, memory, prompt, and PM resume-context evidence before normal
work resumes.

#### Scenario: Partial role rehydration blocks normal work
- **WHEN** a replay package omits a role, reports stale memory, treats unknown
  liveness as active, or rehydrates before resume state is loaded
- **THEN** the Router rejects the package or keeps a recoverable control
  blocker until the standard rehydration evidence is present

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
