## MODIFIED Requirements

### Requirement: Actionable Recovery Duty

When foreground duty requires recovery or reissue, the runtime SHALL include a
concrete command payload sufficient for the Controller to execute the next
runtime action without guessing.

#### Scenario: Replacement duty names packet and role

- **GIVEN** a liveness or stale lease condition requires replacement
- **WHEN** foreground duty is rendered
- **THEN** the recovery payload names the packet id, responsibility, host kind,
  command, and stale lease ids
- **AND** the payload does not include sealed body text
