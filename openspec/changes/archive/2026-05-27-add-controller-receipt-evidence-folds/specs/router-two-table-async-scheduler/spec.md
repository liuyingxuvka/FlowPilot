## ADDED Requirements

### Requirement: Async scheduler waits on proven in-flight relay work
FlowPilot SHALL treat packet relay/open/ACK/progress evidence as in-flight work and SHALL NOT issue a duplicate ordinary relay action while the same packet family and packet ids are already in progress.

#### Scenario: Worker has opened relayed packet
- **WHEN** packet relay evidence exists for a packet family
- **AND** at least one addressed worker has opened, ACKed, or recorded progress for the packet
- **AND** the worker result has not yet returned
- **THEN** Router MUST wait for result or blocker evidence
- **AND** Router MUST NOT issue the same packet relay command again

#### Scenario: Relay evidence exists before aggregate flag is folded
- **WHEN** Router-visible relay evidence proves packet dispatch
- **AND** the aggregate dispatch flag is stale false at scheduler entry
- **THEN** Router MUST run the registered evidence fold before next-action selection
- **AND** duplicate-dispatch checks MUST see the folded in-flight state

### Requirement: Async scheduler escalates only after bounded proof failure
FlowPilot SHALL reserve Controller retry and PM repair escalation for cases where the registered evidence fold cannot prove completion or in-flight work from Router-visible records.

#### Scenario: Controller receipt is done but all relay evidence is absent
- **WHEN** a relay Controller row reports `done`
- **AND** packet/result relay evidence is absent from the registered sources
- **THEN** Router MAY use the existing retry budget and PM repair path
- **AND** Router MUST NOT silently continue as if the relay had succeeded
