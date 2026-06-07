## ADDED Requirements

### Requirement: Real Router dry-run rows expose contract classification
FlowPilot real-router dry-run rehearsal rows SHALL report whether each prepared
fake AI package is contract-declared, missing required fields, forbidden-field
negative, or hidden-field overproduction.

#### Scenario: Dry-run evidence names contract family
- **WHEN** a prepared fake AI package is executed through the real Router dry
  run
- **THEN** the evidence row MUST include the packet contract family id and the
  contract classification used to interpret the result

#### Scenario: Hidden-field success is not valid dry-run evidence
- **WHEN** a prepared fake AI package succeeds only because it supplied a field
  absent from the packet contract
- **THEN** the dry-run rehearsal MUST fail or scope out that row as invalid
  evidence
