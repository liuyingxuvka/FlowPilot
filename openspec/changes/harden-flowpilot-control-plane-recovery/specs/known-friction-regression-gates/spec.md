## ADDED Requirements

### Requirement: Rehydration replay loop is a known-friction regression family
FlowPilot SHALL include the audited rehydration replay loop as a known-friction
regression family that exercises real control-plane surfaces.

#### Scenario: Local PM decision receipt without Router event is caught
- **WHEN** a fixture contains a mechanically valid PM control-blocker repair
  decision receipt
- **AND** no matching Router event was recorded
- **THEN** the regression gate MUST report the output as not consumed by Router
- **AND** it MUST NOT close the active control blocker.

#### Scenario: Repeated same-family blockers are caught
- **WHEN** a fixture would materialize more than one blocker for the same
  rehydrate-role attempt family without a new distinct cause
- **THEN** the regression gate MUST fail unless the implementation coalesces
  the family or exposes a durable terminal disposition.

#### Scenario: Break-glass limbo is caught
- **WHEN** a break-glass incident remains open with only not-run validations
  and no recovery transaction or blocked disposition
- **THEN** the regression gate MUST report the incident as uncovered
- **AND** completion confidence for that known-friction family MUST remain
  scoped or blocked.
