## ADDED Requirements

### Requirement: Role-output ledger package reconciliation commits domain artifacts first
FlowPilot SHALL treat PM package disposition entries discovered in the role-output ledger as candidate events until their domain commit succeeds. Router MUST NOT set the event flag, append event history, mark scoped idempotency, or close Controller waits for material, research, or current-node package dispositions before the PM package disposition writer has committed the canonical disposition artifact and required package state.

#### Scenario: Ledger package disposition with failed source self-check
- **GIVEN** the role-output ledger contains a PM package disposition candidate for a current package batch
- **AND** at least one source result envelope has a missing, failed, mismatched, or unparseable `contract_self_check`
- **WHEN** Router reconciles durable role-output ledger evidence
- **THEN** Router MUST reject or skip the candidate before event finalization
- **AND** Router MUST NOT set the package disposition event flag
- **AND** Router MUST NOT close the PM disposition wait

#### Scenario: Ledger package disposition commits before event record
- **GIVEN** the role-output ledger contains a valid PM package disposition candidate for a current package batch
- **WHEN** Router reconciles durable role-output ledger evidence
- **THEN** Router MUST commit the canonical PM package disposition artifact before recording the external event
- **AND** the recorded event, scoped idempotency row, batch state, and wait closure MUST refer to that committed artifact identity

#### Scenario: Ledger package disposition covers adjacent package families
- **WHEN** Router reconciles PM package disposition candidates for material, research, or current-node result packages
- **THEN** the same domain-first commit rule MUST apply to each package family

#### Scenario: Stale package replay remains quarantine-only
- **GIVEN** canonical package disposition authority already exists for a batch or generation
- **AND** a stale role-output ledger or direct event replay carries a different body hash
- **WHEN** Router classifies the replay before commit
- **THEN** Router MUST quarantine or skip the replay without rewriting the canonical disposition artifact
- **AND** Router MUST NOT use the stale replay to close waits or mark new event progress

#### Scenario: Recorded event without canonical package authority
- **GIVEN** scoped idempotency or event history says a PM package disposition was already recorded
- **AND** the active package batch lacks `pm_result_disposition` or the referenced canonical disposition artifact is missing
- **WHEN** Router sees another PM package disposition candidate for the same batch or generation
- **THEN** Router MUST NOT crash the daemon
- **AND** Router MUST NOT close waits or mark new event progress from the split state
- **AND** Router MUST surface the split authority as blocked, invalid, or repair-owned evidence requiring an explicit repair path

#### Scenario: Package disposition ingress matrix closes the same defect family
- **WHEN** the PM package disposition defect family is validated
- **THEN** validation MUST cover direct event intake, role-output ledger reconciliation, and daemon startup or restart replay
- **AND** validation MUST include valid canonical state, missing canonical state, mismatched body hash, and repair-owned replay cases
