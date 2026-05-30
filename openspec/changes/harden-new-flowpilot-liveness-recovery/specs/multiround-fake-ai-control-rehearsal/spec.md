## ADDED Requirements

### Requirement: Fake AI rehearsal covers slow live role waits
The fake AI rehearsal suite SHALL include a slow-but-working role scenario that proves patrol does not replace a live role before liveness failure evidence.

#### Scenario: Slow reviewer sends progress and is not replaced
- **WHEN** a reviewer ACKs a packet and then records progress before submitting a result
- **THEN** the rehearsal MUST show no replacement lease was assigned
- **AND** the eventual original reviewer result MUST be accepted through the normal packet lifecycle.

### Requirement: Fake AI rehearsal covers accepted-result replacement race
The fake AI rehearsal suite SHALL include an accepted-result race scenario matching the observed live failure family.

#### Scenario: Accepted packet is not reassigned
- **WHEN** a packet already has an accepted result
- **AND** a later replacement assignment is attempted
- **THEN** the rehearsal MUST show the assignment is rejected or repaired
- **AND** the next action MUST advance beyond the accepted packet.
