## ADDED Requirements

### Requirement: Shadow peer conflicts preserve run isolation
The system SHALL test peer-run conflicts involving shared background artifacts,
local install state, active run ownership, and model-test evidence rows.

#### Scenario: Peer run cannot consume another run's proof
- **WHEN** a shadow peer flow attempts to reuse another run's proof, stop
  another run, or overwrite shared background artifacts
- **THEN** the active run remains isolated, stale evidence is rejected, and the
  conflict is either blocked or quarantined
