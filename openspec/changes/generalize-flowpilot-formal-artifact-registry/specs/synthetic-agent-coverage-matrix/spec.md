## ADDED Requirements

### Requirement: Formal artifact cells derive from registry
FlowPilot SHALL derive formal-artifact synthetic-agent cells from the
runtime-known formal artifact registry.

#### Scenario: Every registered artifact has lifecycle fault cells
- **WHEN** the fake-AI synthetic matrix builds formal artifact cells
- **THEN** every registered AI-submitted formal artifact MUST have missing file,
  wrong path, invalid JSON, missing internal field, wrong value, and body
  conflict cells where applicable.

#### Scenario: Helper-written artifacts cannot hide failures
- **WHEN** fake-AI rehearsal runs a registered formal artifact packet family
- **THEN** the selected fake responder mode MUST determine whether the artifact
  is present, malformed, misplaced, incomplete, conflicting, or compliant
- **AND** setup helpers MUST NOT silently create a compliant file for a
  non-compliant mode.

### Requirement: Matrix reports registered artifact feedback oracles
FlowPilot SHALL associate every registered formal artifact negative cell with
an executable runtime feedback oracle.

#### Scenario: Feedback oracle names executable repair material
- **WHEN** a registered formal artifact negative cell is generated
- **THEN** the oracle MUST require the reissue feedback to name the artifact id,
  current target root or path, internal field path when known, allowed value or
  type when known, and body-only insufficiency.
