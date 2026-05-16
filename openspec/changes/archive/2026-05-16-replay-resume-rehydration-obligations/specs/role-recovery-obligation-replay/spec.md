## MODIFIED Requirements

### Requirement: Router scans recovered-role obligations

Router SHALL scan current-run wait rows, card return waits, and packet
ownership metadata for obligations whose target or waiting role is the
recovered or resume-rehydrated role.

#### Scenario: Multiple waits are discovered

- **WHEN** the recovered or resume-rehydrated role has multiple unresolved wait rows in the scheduler or controller ledgers
- **THEN** Router builds a replay candidate list containing each unresolved obligation and its original order

#### Scenario: Unrelated waits are ignored

- **WHEN** wait rows target roles outside the recovered or resume-rehydrated role set
- **THEN** Router does not replay or supersede those rows as part of that recovery replay

### Requirement: PM escalation is reserved for semantic ambiguity

Router SHALL notify PM after role recovery or resume rehydration only when
mechanical replay cannot safely determine continuation.

#### Scenario: Mechanical replay avoids PM

- **WHEN** recovery or resume rehydration succeeds and all waits are settled or replacement obligations are issued without conflict
- **THEN** Router does not deliver a PM freshness or recovery-decision card solely to announce that roles were restored

#### Scenario: Conflicting outputs require PM

- **WHEN** two valid-looking outputs conflict or packet ownership cannot be mechanically resolved
- **THEN** Router escalates to PM with controller-visible envelope metadata and does not let Controller choose the winning output

#### Scenario: Route semantics changed

- **WHEN** replay would require changing route scope, acceptance criteria, or task semantics
- **THEN** Router escalates to PM before issuing replacement work
