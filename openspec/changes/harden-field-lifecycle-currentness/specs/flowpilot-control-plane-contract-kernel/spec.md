## ADDED Requirements

### Requirement: Packet currentness lifecycle is mechanically monotonic
FlowPilot SHALL treat packet currentness fields as Runtime-owned mechanical
state. Once a packet enters a noncurrent terminal disposition, later results
MUST remain audit evidence only and MUST NOT reactivate the packet as current,
blocked, or waiting work.

#### Scenario: Late result after terminal packet disposition
- **WHEN** a packet status is `accepted`, `quarantined_after_route_mutation`, or `superseded_after_repair`
- **AND** a late result is submitted for that packet
- **THEN** Runtime MUST record the result as non-authoritative audit evidence
- **AND** Runtime MUST preserve the packet terminal disposition
- **AND** Runtime MUST NOT convert the packet to `result_submitted` or `result_blocked`

#### Scenario: Duplicate result after accepted packet
- **WHEN** a packet already has an accepted result
- **AND** another result is submitted for the same packet
- **THEN** Runtime MUST block the duplicate result mechanically
- **AND** Runtime MUST preserve the accepted packet state and accepted result pointer

### Requirement: Pending route mutation state has one terminal disposition
FlowPilot SHALL keep route-mutation pending state Runtime-owned and current
only until the corresponding route mutation is committed, superseded, or
blocked.

#### Scenario: Route mutation commit finishes pending state
- **WHEN** a pending route mutation is committed into the active route/frontier
- **THEN** Runtime MUST clear or terminally disposition the pending route mutation
- **AND** later packet/result processing MUST NOT treat the old pending mutation
as current work
