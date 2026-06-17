## ADDED Requirements

### Requirement: Synthetic coverage rows identify executable evidence level

Synthetic agent coverage rows SHALL classify each row as model-only,
fake-body-contract, Runtime/CLI replay, long-chain convergence, or parent
confidence evidence.

#### Scenario: Coverage row exposes evidence level

- **WHEN** the synthetic agent coverage matrix is generated
- **THEN** every row that cites current-contract matrix coverage MUST name its
  evidence level and MUST NOT imply Runtime/CLI execution unless public runtime
  evidence exists

#### Scenario: Executable bridge row is consumed

- **WHEN** a synthetic coverage row claims executable confidence
- **THEN** it MUST cite an executable bridge row id and current evidence receipt
  for the same packet family and expected outcome

### Requirement: Synthetic matrix reports model-only confidence honestly

Synthetic matrix reports SHALL keep model-only coverage distinct from fake AI
package and runtime replay coverage.

#### Scenario: Model-only row stays scoped

- **WHEN** a row is backed only by the current-contract Cartesian model
- **THEN** the report MUST mark it as scoped model confidence and MUST keep
  executable runtime confidence unresolved
