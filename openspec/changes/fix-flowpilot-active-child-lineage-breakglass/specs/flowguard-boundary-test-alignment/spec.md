## MODIFIED Requirements

### Requirement: Cartesian coverage includes active lineage and break-glass cells
FlowPilot SHALL bind active child lineage and same-root break-glass behavior to
executable tests or model checks that cover the finite Cartesian boundary.

#### Scenario: Active child lineage boundary is covered
- **WHEN** the coverage suite runs
- **THEN** it MUST include no replacement, single replacement, replacement chain, missing target, cycle, and still-superseded target cases.

#### Scenario: Break-glass boundary is covered
- **WHEN** the coverage suite runs
- **THEN** it MUST include active, cleared-unclosed, verified-closed, retired, same-root, and different-root blocker histories
- **AND** attempt counts at 1, 4, 5, and 6.

#### Scenario: Effect checks beat text checks
- **WHEN** FlowGuard or fake AI reports claim pass from PM text while route/replay effects still use a superseded child
- **THEN** the executable coverage MUST fail that case.
