## ADDED Requirements

### Requirement: Active packet projections derive from Router currentness
FlowPilot SHALL derive active-packet views from the single Router currentness
predicate and MUST NOT maintain parallel local filters for compact status,
final closure, or progress projections.

#### Scenario: Route node is noncurrent but packet status is blocking
- **WHEN** a packet belongs to a route node whose status is `accepted`,
`waived`, or `superseded`
- **AND** the packet status still contains a blocking or submitted value
- **THEN** Router-derived active-packet projections MUST exclude that packet
- **AND** the projection MUST NOT independently reclassify it as active work

#### Scenario: Route version is stale
- **WHEN** a packet route version differs from the active route version
- **THEN** compact status, final closure, and progress projections MUST treat
the packet as noncurrent through the shared currentness predicate
