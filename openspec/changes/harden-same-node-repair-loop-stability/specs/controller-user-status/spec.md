## ADDED Requirements

### Requirement: Current status excludes noncurrent repair history
FlowPilot current status SHALL describe only current effective blockers as active work and SHALL keep old repair-chain rows as history instead of current user-visible blockers.

#### Scenario: Superseded repair packet is not active status
- **WHEN** a repair packet or blocker row has been superseded, cleared, retired, or attached to a noncurrent route node
- **THEN** current status MUST NOT report that row as an active blocker or current wait.

#### Scenario: Current active blocker remains visible
- **WHEN** a blocker is current-effective for the active route and current target packet
- **THEN** current status MUST continue to expose it as active public blocker metadata.
