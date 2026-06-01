## ADDED Requirements

### Requirement: Final Evidence Matrix Includes Route Deliverable Rows

The terminal evidence matrix SHALL include a row for each required route deliverable check declared by an effective route node.

#### Scenario: Deliverable row records missing artifact

- **WHEN** an effective route node declares a required deliverable check whose runtime evaluation fails
- **THEN** the final evidence matrix MUST include a `route_deliverable` row with status `missing` or `failed`
- **AND** the matrix unresolved count MUST be non-zero.

#### Scenario: Deliverable row records covered artifact

- **WHEN** an effective route node declares a required deliverable check whose runtime evaluation passes
- **THEN** the final evidence matrix MUST include a `route_deliverable` row with status `covered`
- **AND** the row MUST identify the route node and deliverable check ID.
