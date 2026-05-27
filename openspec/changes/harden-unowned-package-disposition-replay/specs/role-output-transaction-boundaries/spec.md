## ADDED Requirements

### Requirement: Role-output replay respects package artifact authority

Role-output ledger replay for PM package dispositions SHALL compare replayed
body identity with the current file-backed package disposition authority before
mutating Router run state.

#### Scenario: Current artifact wins over older replay row

- **GIVEN** the current PM package disposition artifact was written by a newer
  accepted package transaction
- **AND** a durable role-output row for the same semantic package identity has
  an older different body hash
- **WHEN** role-output replay reconciles the row
- **THEN** replay SHALL not overwrite the artifact-backed transaction outcome
- **AND** replay SHALL not write a duplicate package transaction side effect
- **AND** replay SHALL record why the row was skipped or quarantined.

#### Scenario: Missing artifact remains conservative

- **GIVEN** role-output replay sees a same-package different-body conflict
- **AND** Router cannot prove an authoritative current package artifact,
  repair owner, terminal quarantine, or authorized reissue path
- **WHEN** replay reconciles the row
- **THEN** Router SHALL surface a conservative conflict path
- **AND** Router SHALL NOT accept the row as successful package completion.
