## ADDED Requirements

### Requirement: Startup scheduler obeys terminal fence
Daemon-owned startup scheduling SHALL stop immediately when current-run
lifecycle is terminal.

#### Scenario: Startup scheduler receives stopped run
- **WHEN** startup daemon scheduling is asked to create startup intake, role
  startup, heartbeat binding, or Controller core handoff for a stopped run
- **THEN** it MUST return terminal/no-op status
- **AND** it MUST NOT append a new startup scheduler row or Controller action.

#### Scenario: Stop arrives between startup rows
- **WHEN** a startup Controller receipt is consumed and the run has become
  terminal before the next startup row is scheduled
- **THEN** Router MUST preserve terminal projection and MUST NOT schedule the
  next startup row.
