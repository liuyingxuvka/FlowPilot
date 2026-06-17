## ADDED Requirements

### Requirement: End-to-end chaos rows consume bridge case ids

End-to-end chaos coverage rows SHALL consume executable bridge case ids for
model-derived bad cases that claim public runtime coverage.

#### Scenario: Chaos row cites bridge evidence

- **WHEN** an end-to-end chaos row covers a current-contract bad package class
- **THEN** it MUST cite the bridge case id, executable evidence command, event
  evidence, convergence result, and freshness receipt

#### Scenario: Matrix-only proof is rejected for chaos execution

- **WHEN** an end-to-end chaos row cites only a model matrix result
- **THEN** the chaos matrix MUST reject the row as executable proof
