## ADDED Requirements

### Requirement: Synthetic coverage owns rejection liveness cells
The synthetic agent coverage matrix SHALL register every required
rejection/liveness cell with branch kind, contract family, defect class,
primary evidence owner, evidence command or test id, and confidence boundary.

#### Scenario: Required rejection cell lacks evidence
- **WHEN** a rejection/liveness cell is required by the parent matrix but has no
  current evidence owner
- **THEN** the synthetic coverage gate MUST fail and identify the missing cell.

#### Scenario: Synthetic evidence remains scoped
- **WHEN** a rejection/liveness cell is backed only by fake AI or historical
  replay evidence
- **THEN** the coverage matrix MUST mark the row as scoped synthetic evidence
- **AND** it MUST NOT use the row to close live AI semantic quality or release
  confidence by itself.

