## ADDED Requirements

### Requirement: Package-disposition replay gate includes unowned stale replay

FlowPilot SHALL include the historical unowned foreground/daemon interleaving
branch in the known-friction regression gate for PM package-disposition
conflict replay, in addition to repair-owned replay branches.

#### Scenario: Historical branch is missing concrete evidence

- **WHEN** the package-disposition replay friction row lacks a test or replay
  that commits a newer canonical package body before replaying an older durable
  role-output row
- **THEN** the known-friction gate SHALL report the row as uncovered or scoped
- **AND** FlowPilot SHALL NOT claim full closure for the defect family.

#### Scenario: Model-only evidence is insufficient

- **WHEN** model checks pass for package-disposition conflict replay
- **AND** no runtime or daemon-facing test proves stale unowned replay is
  quarantined without accepting the old body
- **THEN** the known-friction gate SHALL classify the evidence as scoped.
