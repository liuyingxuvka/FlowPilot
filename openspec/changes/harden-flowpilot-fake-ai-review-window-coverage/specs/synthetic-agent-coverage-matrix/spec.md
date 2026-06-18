## ADDED Requirements

### Requirement: Contract-driven responder owns malformed-output cells
The synthetic agent coverage matrix SHALL require every generated fake-AI
malformed-output cell to be owned by the contract-driven fake AI responder or a
named focused runtime test that consumes responder output.

#### Scenario: Malformed syntax cell has a responder owner
- **WHEN** the matrix includes a malformed strict-JSON object case
- **THEN** the cell MUST name the contract-driven fake AI responder as evidence owner
- **AND** the cell MUST name the concrete malformed syntax family.

#### Scenario: Hand-written bad fixture cannot be the only owner
- **WHEN** a negative AI-output case is represented only by a hand-written body fixture
- **THEN** the coverage matrix MUST classify the cell as missing responder evidence
- **AND** the parent coverage gate MUST fail until responder-owned evidence exists.

### Requirement: Projection completeness is a coverage dimension
The synthetic agent coverage matrix SHALL include cells proving that
runtime-enforced output obligations are visible in the AI-facing packet
contract before the first response.

#### Scenario: Runtime validator obligation lacks first-packet projection
- **WHEN** a runtime validator enforces a required field, child field, finite option, active id, projection row, or owner coverage rule
- **AND** the current packet contract does not expose the obligation through structured contract metadata
- **THEN** the coverage matrix MUST mark the cell failed as a projection gap.

#### Scenario: Current active ids are projected
- **WHEN** a validator requires coverage of current active acceptance items or node-owned acceptance items
- **THEN** the matrix MUST require evidence that the current active ids are visible in the first AI-facing packet.
