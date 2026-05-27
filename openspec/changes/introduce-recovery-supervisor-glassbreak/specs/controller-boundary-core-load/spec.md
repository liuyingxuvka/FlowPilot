## ADDED Requirements

### Requirement: Controller core is reloaded after Recovery Supervisor exit
FlowPilot SHALL invalidate the old Controller generation after Recovery
Supervisor mode and require a fresh Controller-core boundary confirmation
before normal route work resumes.

#### Scenario: Recovery transaction closes
- **WHEN** Recovery Supervisor closes a recovery transaction
- **THEN** the close record MUST name the prior Controller generation, the next
  Controller generation, and a Controller boundary proof or core hash

#### Scenario: Old Controller tries to resume
- **WHEN** the old Controller generation attempts to continue normal route work
  after Recovery Supervisor mode
- **THEN** FlowPilot MUST reject the resume until the new Controller-core
  reinjection proof is recorded
