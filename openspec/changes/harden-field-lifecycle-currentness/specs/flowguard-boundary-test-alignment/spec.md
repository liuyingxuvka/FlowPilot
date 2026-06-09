## ADDED Requirements

### Requirement: Behavior-bearing field lifecycle projects to alignment evidence
FlowPilot SHALL project behavior-bearing field lifecycle rows into FlowGuard
model obligations, owner code contracts, and ordinary test evidence before
claiming field lifecycle coverage for currentness, pending state, or derived
views.

#### Scenario: Field lifecycle projection is missing for currentness fields
- **WHEN** model-test alignment inspects packet/result/frontier currentness
fields
- **THEN** it MUST find nonempty field lifecycle projections for terminal
packet status, result audit history, accepted result pointers, pending route
mutation, and active-packet derived views
- **AND** it MUST report a gap if those projections are absent

#### Scenario: Field lifecycle projection points to ordinary tests
- **WHEN** a field lifecycle projection is registered
- **THEN** it MUST name the owner code contract and ordinary test evidence that
exercises the current-contract behavior
