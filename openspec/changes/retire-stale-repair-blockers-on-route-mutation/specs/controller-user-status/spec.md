## ADDED Requirements

### Requirement: Route-mutation-superseded repair blockers are history in status
FlowPilot current status SHALL treat repair blockers superseded by a route mutation as historical evidence rather than an active wait.

#### Scenario: Superseded repair blocker is not active wait
- **WHEN** a repair blocker has `status=superseded_by_route_mutation`
- **THEN** current status MUST NOT present that blocker as a current active repair wait
- **AND** final-preflight MUST NOT block solely because that historical repair blocker exists.
