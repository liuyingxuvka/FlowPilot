# FlowGuard Model Hierarchy Specification

## ADDED Requirements

### Requirement: Persistent daemon parent evidence must be thin-child mesh evidence

The FlowPilot parent hierarchy SHALL NOT consume the full
`flowpilot_persistent_router_daemon` result as direct thin-child evidence.

#### Scenario: Router daemon resume partition consumes split children

- **GIVEN** the `router_daemon_resume` parent partition is evaluated
- **WHEN** the parent reads child evidence ids from the responsibility ledger
- **THEN** it consumes focused daemon child evidence for startup/lock,
  Controller actions, wait/liveness, and terminal/projection contracts
- **AND** each focused child result is below the thin-child state threshold
- **AND** the compatibility persistent daemon model may still run outside the
  parent thin-child evidence set.
