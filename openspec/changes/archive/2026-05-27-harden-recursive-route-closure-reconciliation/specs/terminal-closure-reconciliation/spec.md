## ADDED Requirements

### Requirement: Terminal closure reconciles defect, role, and import state

FlowPilot terminal closure SHALL cite current-run reconciliation status for the
defect ledger, role memory, and imported-artifact quarantine before accepting PM
terminal closure.

#### Scenario: Defect ledger blocks closure

- **WHEN** the current run has a defect ledger with blocker-open defects or
  fixed-pending-recheck defects
- **THEN** terminal closure is rejected
- **AND** the blocker count is reported in the final ledger or closure review.

#### Scenario: Role memory blocks stale authority

- **WHEN** a current-run role memory packet belongs to a different run or marks
  historical agent ids as reused authority
- **THEN** terminal closure is rejected
- **AND** the stale role memory paths are reported.

#### Scenario: Imported artifacts remain quarantined

- **WHEN** continuation quarantine shows prior control state, old agent ids, or
  old assets still acting as current authority
- **THEN** terminal closure is rejected
- **AND** the quarantine path is cited as the blocking source.

#### Scenario: Optional ledgers are absent

- **WHEN** a new or minimal run has no optional defect or role-memory artifacts
- **THEN** FlowPilot records `present=false` for that reconciliation family
- **AND** absence alone does not become a pass claim or a closure blocker.
