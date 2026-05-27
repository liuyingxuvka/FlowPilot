## ADDED Requirements

### Requirement: Package-disposition conflict replay is a recurring defect-family gate

FlowPilot SHALL maintain a known-friction gate for PM package-disposition
conflict replay so scoped green checks for direct conflict rejection cannot be
reported as full live-run confidence.

#### Scenario: Observed replay miss is generalized before closure

- **GIVEN** live or replay evidence shows daemon failure after a previously
  modeled package-disposition conflict path appeared green
- **WHEN** the defect family is repaired
- **THEN** the gate SHALL include the observed daemon replay failure
- **AND** it SHALL include same-class generalized cases across package kind,
  replay source, blocker ownership, PM repair ownership, and daemon restart
  replay.

#### Scenario: Evidence is scoped when same-class coverage is incomplete

- **GIVEN** only material-scan or direct event-intake cases have current green
  evidence
- **WHEN** FlowPilot reports repair confidence for package-disposition conflict
  replay
- **THEN** the report SHALL mark confidence as scoped
- **AND** it SHALL NOT claim the full defect family is closed.
