## ADDED Requirements

### Requirement: Synthetic coverage consumes contract-exhaustion rows
The synthetic agent coverage matrix SHALL include the generated
contract-exhaustion rows as control-plane branch coverage evidence.

#### Scenario: Generated branch lacks evidence owner
- **WHEN** a generated contract-exhaustion row has no primary runtime test,
  replay, model-alignment, or background-artifact evidence owner
- **THEN** the synthetic coverage matrix MUST fail and identify the missing
  generated branch owner

#### Scenario: Generated branch remains non-live evidence
- **WHEN** a generated contract-exhaustion row passes with synthetic or fixture
  inputs
- **THEN** the coverage matrix MUST classify it as control-plane regression
  evidence and MUST NOT use it as live target-project completion evidence

#### Scenario: Historical failure replay remains non-live and repair-owned
- **WHEN** a generated contract-exhaustion row comes from a historical failure
  family
- **THEN** the coverage matrix MUST classify it as `historical_failure_replay`,
  expose the normal repair route, and keep `glass_break_allowed_in_acceptance`
  false

#### Scenario: Contract-exhaustion owner is not consumed by TestMesh
- **WHEN** the contract-exhaustion report lists an unregistered required child
  suite owner
- **THEN** the synthetic coverage matrix MUST NOT treat the generated rows as
  fully consumed branch evidence
