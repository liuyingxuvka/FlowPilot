## ADDED Requirements

### Requirement: Packet result author evidence remains replayable
FlowPilot SHALL require packet result authority checks to preserve replayable author identity for current-generation material-scan results.

#### Scenario: Result author matches current role binding
- **WHEN** Router accepts material-scan worker results for PM disposition
- **THEN** the result envelope or packet ledger evidence MUST prove the completed role and replayable agent identity for the current packet holder
- **AND** Router MUST record that authority without writing false success fields when the identity is unknown

#### Scenario: Role-name agent id is repaired through existing reissue path
- **WHEN** a material-scan result uses a role key where an agent id is required
- **THEN** Router MUST route the correction through the existing control-plane reissue or packet repair path
- **AND** Router MUST NOT let that result satisfy current-generation packet result authority until corrected.
