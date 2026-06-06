# resume-rehydration-obligation-replay Specification

## Purpose
Define current resume obligation replay without historical continuation
compatibility or fixed-role startup assumptions.

## Requirements
### Requirement: Resume rehydration SHALL run Router obligation replay before default PM resume

Router SHALL run metadata-only obligation replay before delivering a PM resume
decision card after current manual resume restores or replaces current
background role bindings, unless current-run memory or resume state is missing.

#### Scenario: Manual resume replays mechanical obligations

- **WHEN** `manual_resume_requested` has been recorded
- **AND** `load_resume_state` has loaded current-run state and daemon evidence
- **AND** `rehydrate_role_bindings` reports current background role bindings
  ready with current-run memory, liveness preflight, and common context
- **THEN** Router scans current-run outstanding waits for the restored role
  bindings before delivering `pm.resume_decision`

#### Scenario: Current resume uses one replay path

- **WHEN** a current resume wake follows the state load and role-binding
  rehydration path
- **THEN** Router uses the same obligation replay rules for all current resume
  recovery work
- **AND** Router MUST NOT use unsupported historical continuation events or
  historical role evidence to satisfy resume replay.

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

### Requirement: Current replay packages cover background role lifecycle recovery
The system SHALL include current role lifecycle replay packages that require
background role liveness, memory, prompt, and PM resume-context evidence before
normal work resumes.

#### Scenario: Partial role-binding rehydration blocks normal work
- **WHEN** a replay package omits a required current role binding, reports stale
  memory, treats unknown liveness as active, omits concurrent liveness
  preflight, or rehydrates before resume state is loaded
- **THEN** the Router rejects the package or keeps a recoverable control
  blocker until the standard rehydration evidence is present

### Requirement: Resume state load remains Router-owned under receipt projection
Manual resume SHALL preserve Router ownership of resume state loading even when
`load_resume_state` is represented by a Controller action receipt.

#### Scenario: Resume load receipt sets resume state through Router replay
- **WHEN** `manual_resume_requested` has been recorded
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
when current resume or role recovery mechanically reissues replacement
obligations.

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
