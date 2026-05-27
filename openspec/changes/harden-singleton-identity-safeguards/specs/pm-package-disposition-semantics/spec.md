## ADDED Requirements

### Requirement: PM Package Disposition Singleton Evidence
FlowPilot SHALL include PM package disposition singleton evidence in the authority matrix and duplicate hazard model.

#### Scenario: Same package has one semantic disposition
- **WHEN** a package has a recorded disposition for the same router event, batch id, packet ids, and packet generation id
- **THEN** singleton evidence records that disposition as the sole semantic authority for that package identity

#### Scenario: Different disposition body conflicts
- **WHEN** a later disposition for the same semantic package identity has a different body hash
- **THEN** the singleton checker reports a conflict unless an authorized repair, cancellation, supersession, or reissue creates a new package identity
