# resume-rehydration-obligation-replay Specification

## Purpose
TBD - created by archiving change replay-resume-rehydration-obligations. Update Purpose after archive.
## Requirements
### Requirement: Resume rehydration SHALL run Router obligation replay before default PM resume

Router SHALL run metadata-only obligation replay before delivering a PM resume
decision card after heartbeat or manual resume restores or replaces the six
role agents, unless current-run memory or resume state is missing.

#### Scenario: Heartbeat resume replays mechanical obligations

- **WHEN** `heartbeat_or_manual_resume_requested` has been recorded
- **AND** `load_resume_state` has loaded current-run state and daemon evidence
- **AND** `rehydrate_role_agents` reports all six roles ready with current-run memory or common context
- **THEN** Router scans current-run outstanding waits for the restored roles before delivering `pm.resume_decision`

#### Scenario: Manual resume shares the same replay path

- **WHEN** a manual resume wake follows the same state load and six-role rehydration path
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
