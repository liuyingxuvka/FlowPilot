## MODIFIED Requirements

### Requirement: Accepted Packet Lease Health

The runtime SHALL prevent accepted packets from retaining stale active leases.

#### Scenario: Packet reassignment supersedes older active lease

- **GIVEN** a packet has an active assigned lease
- **WHEN** the packet is assigned to a replacement active lease before acceptance
- **THEN** the previous active lease is marked superseded with the replacement lease id
- **AND** the replacement lease is the packet's assigned lease

#### Scenario: Final preflight blocks stale accepted-packet active leases

- **GIVEN** an accepted packet has a stale active lease left from replacement or recovery
- **WHEN** final return preflight runs
- **THEN** the preflight is not allowed
- **AND** the blockers name the stale accepted-packet lease health issue
