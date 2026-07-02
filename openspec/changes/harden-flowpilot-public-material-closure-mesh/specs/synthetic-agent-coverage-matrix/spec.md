# synthetic-agent-coverage-matrix Specification

## ADDED Requirements

### Requirement: Declared finite-universe Cartesian coverage exists

FlowPilot SHALL declare finite axes for material access, role responsibility, blocker family, route state, repeat depth, terminal state, and final projection, then cover all required cells or documented interaction groups with executable tests.

#### Scenario: Coverage suite claims full mesh
- **WHEN** a test or model claims public material/sealed body/blocker/terminal/identity coverage
- **THEN** it MUST list the finite axes or generated case ids it covers
- **AND** every required cell or shard MUST have current passing evidence.

### Requirement: Observed misses are backfed into canonical coverage

Observed misses from historical blockers SHALL become canonical bad cases or explicit scoped gaps in the coverage matrix.

#### Scenario: Historical miss repeats without a test cell
- **WHEN** a miss class such as shallow FlowGuard pass, ordinary material skip, identity leak, stale final projection, or missing terminal coverage was observed
- **THEN** a named test/model cell MUST cover that class before completion confidence can be claimed.
