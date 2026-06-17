## ADDED Requirements

### Requirement: Break-glass is the fifth same-class no-progress safety fuse

Controller break-glass SHALL remain unavailable for known recoverable paths
before threshold, and SHALL be required when the same control-plane failure
class repeats five times without progress.

#### Scenario: First four repeated attempts stay normal-lane

- **WHEN** a known current-contract failure repeats on attempts one through four
  and normal reject, reissue, block, repair, redesign, or terminal stop remains
  available
- **THEN** Controller MUST keep the path in the normal control plane and MUST
  NOT open break-glass

#### Scenario: Fifth no-progress repeat opens break-glass

- **WHEN** the same failure class reaches the fifth no-progress attempt without
  repair delta, new evidence, or legal next-action progress
- **THEN** Controller MUST open a run-scoped break-glass incident with the
  repeated lineage, failed normal lanes, suspected control-plane defect, and
  required permanent follow-up

#### Scenario: Break-glass pass is not ordinary recovery

- **WHEN** a fifth-repeat bridge row enters break-glass as expected
- **THEN** reports MUST classify the result as safety-fuse coverage and MUST NOT
  count it as normal repair convergence
