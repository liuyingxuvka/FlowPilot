## ADDED Requirements

### Requirement: Review-window completeness cells are coverage-owned
FlowPilot SHALL generate synthetic coverage cells from the review-window
completeness matrix. Each generated cell MUST have a stable cell id, review
flow id, mutation or behavior profile, expected oracle reaction, primary
evidence owner, and confidence boundary.

#### Scenario: Completeness row creates coverage cells
- **WHEN** a review-window completeness row is declared
- **THEN** the synthetic coverage matrix MUST include cells for required
  window paths, material authorization, future-stage boundary, PM repair return,
  and fake-AI review behavior profiles.

#### Scenario: Missing owner fails coverage
- **WHEN** a generated review-window completeness cell lacks a current primary
  evidence owner
- **THEN** the synthetic coverage gate MUST fail
- **AND** the failure MUST identify the missing cell id.

### Requirement: Cartesian review-window axes are explicit
FlowPilot SHALL represent review-window coverage as a bounded Cartesian matrix
over declared review flows, window mutation families, authorized-material
states, fake-AI behavior profiles, and retry-count classes.

#### Scenario: Valid combination has an oracle
- **WHEN** a Cartesian combination is valid for a declared review flow
- **THEN** the generated cell MUST declare whether Runtime should accept,
  reject, block, reissue, require PM repair/recheck, keep normal retry, or
  trigger break-glass threshold behavior.

#### Scenario: Invalid combination is explicitly scoped out
- **WHEN** a Cartesian combination does not apply to a review flow
- **THEN** the matrix MUST mark it as `not_applicable`
- **AND** the row MUST include a reason rather than silently skipping the
  combination.
