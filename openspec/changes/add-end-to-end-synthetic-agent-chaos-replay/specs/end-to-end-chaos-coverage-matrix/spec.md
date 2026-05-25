## ADDED Requirements

### Requirement: End-to-end chaos matrix records executable coverage
The system SHALL maintain a matrix for full-flow fake AI chaos replay coverage.

#### Scenario: Matrix rows include phase and evidence
- **WHEN** a row is added to the matrix
- **THEN** it MUST name the flow phase, injected error sequence, expected rejection or acceptance, protected invariant, recovery route, final state, and executable evidence id.

#### Scenario: Matrix rejects missing recovery or proof
- **WHEN** a row lacks recovery route, protected invariant, final state, or executable evidence
- **THEN** matrix validation MUST fail.

#### Scenario: Matrix distinguishes leaf and parent evidence
- **WHEN** a row references hard-gate or router child-suite evidence
- **THEN** the row MUST identify whether that evidence is leaf support, parent support, or the primary full-flow replay evidence.

### Requirement: End-to-end chaos matrix exposes bounded confidence
The matrix SHALL describe what the fake AI replay proves and what it does not prove.

#### Scenario: Matrix boundary excludes live AI semantic quality
- **WHEN** the matrix result is generated
- **THEN** it MUST state that fake package replay proves protocol, state, recovery, and proof gates but does not prove live AI semantic quality.
