## ADDED Requirements

### Requirement: Router direct dispatch replaces Reviewer pre-dispatch approval for new PM packets
Router SHALL use direct-dispatch validation as the active pre-worker gate for new PM-authored work packets. Reviewer pre-dispatch approval SHALL remain legacy-only and SHALL NOT be required before relaying a valid PM-authored Worker or Officer packet.

#### Scenario: Valid PM packet relays after Router validation
- **WHEN** PM registers a work packet for a Worker or Officer
- **AND** Router verifies packet authority, target role, sealed body boundary, hash identity, active-holder state, and recipient availability
- **THEN** Router SHALL allow Controller to relay the packet envelope to the assigned role
- **AND** Router SHALL NOT require `reviewer.dispatch_request` or an equivalent Reviewer approval before relay.

#### Scenario: Invalid packet still blocks before worker relay
- **WHEN** a PM-authored work packet fails Router direct-dispatch validation
- **THEN** Router SHALL block or repair the packet before worker relay
- **AND** Reviewer approval SHALL NOT be used to override the failed mechanical gate.
