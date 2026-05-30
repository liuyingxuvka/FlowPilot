## ADDED Requirements

### Requirement: Wait recovery evidence is persisted from current ledger authority
The runtime ledger SHALL persist wait recovery metadata from current packet, lease, progress, and guard state without relying on old Router daemon files.

#### Scenario: Guard writes wait recovery metadata
- **WHEN** lifecycle guard evaluates a packet wait
- **THEN** the persisted guard and foreground duty MUST include the wait recovery state, packet id, lease id, progress count, and replacement eligibility
- **AND** sealed packet and result bodies MUST remain hidden.

#### Scenario: Later progress invalidates stale recovery evidence
- **WHEN** a progress event is recorded after a prior replacement warning
- **THEN** the next persisted guard MUST reflect the newer progress event
- **AND** older replacement warnings MUST NOT remain authoritative without revalidation.

### Requirement: Accepted packet repair writes auditable ledger events
Current-run repair for accepted-packet assignment races SHALL write explicit events and state changes to the run ledger.

#### Scenario: Repair closes replacement lease
- **WHEN** repair finds an accepted packet assigned to a later active replacement lease
- **THEN** repair MUST record an event identifying the packet, accepted result, original lease when known, replacement lease, and repair reason
- **AND** the replacement lease MUST no longer be active after repair.
