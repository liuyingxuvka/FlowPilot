## MODIFIED Requirements

### Requirement: Historical And Contract Exhaustion Inputs Are Consumed
The system SHALL consume existing contract-exhaustion and historical material
families as inputs to the Cartesian layer rather than replacing them.

#### Scenario: Contract exhaustion bridge includes formal artifact faults
- **WHEN** ContractExhaustionMesh emits registry-backed formal artifact fault modes
- **THEN** the Cartesian bridge MUST recognize those fault modes as current
  control-plane mutations and MUST NOT translate them through fallback aliases

#### Scenario: Formal artifact bridge rows are consumed
- **WHEN** the Cartesian runner checks contract-exhaustion bridge rows
- **THEN** every formal artifact bridge row MUST have a known source mutation,
  known Cartesian mutation, current evidence owner, and no missing mutation
  family finding
