## ADDED Requirements

### Requirement: Routine Router evidence uses focused child suites
FlowPilot SHALL treat broad Router wrapper modules as compatibility aggregates
and consume focused TestMesh child suites for routine Router confidence.

#### Scenario: Router routine tier avoids broad resume aggregate
- **WHEN** the Router tier is planned
- **THEN** it MUST include focused resume child suites for reentry,
  rehydration, role recovery, and liveness faults
- **AND** it MUST NOT require a monolithic `router_resume` command as routine
  confidence evidence.

#### Scenario: Startup daemon routine evidence remains bounded
- **WHEN** startup daemon validation is planned
- **THEN** routine evidence MUST come from the focused startup-daemon child
  command and its final artifact status
- **AND** any broad wrapper module SHALL remain compatibility-only evidence.
