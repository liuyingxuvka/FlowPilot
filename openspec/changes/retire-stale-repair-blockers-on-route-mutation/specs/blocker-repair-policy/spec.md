## ADDED Requirements

### Requirement: Route mutation retires stale repair-open blockers
FlowPilot SHALL convert repair-open blockers from older route versions into route-mutation supersession history when a route mutation advances the active route version.

#### Scenario: Older route repair blocker becomes history
- **WHEN** a route mutation records a `new_route_version`
- **AND** an active blocker has `status=repair_packet_open`
- **AND** that blocker has a numeric `route_version` lower than the mutation's `new_route_version`
- **THEN** FlowPilot MUST set that blocker status to `superseded_by_route_mutation`
- **AND** FlowPilot MUST preserve the blocker row with the existing route-mutation supersession metadata.

#### Scenario: Current route repair blocker remains open
- **WHEN** a route mutation records a `new_route_version`
- **AND** an active blocker has `status=repair_packet_open`
- **AND** that blocker has a numeric `route_version` equal to or newer than the mutation's `new_route_version`
- **THEN** FlowPilot MUST leave that blocker in `repair_packet_open`.

#### Scenario: Unproven stale blocker remains unchanged
- **WHEN** a route mutation records a `new_route_version`
- **AND** an active blocker has `status=repair_packet_open`
- **AND** the blocker route version is missing or nonnumeric
- **THEN** FlowPilot MUST leave that blocker unchanged instead of guessing that it is stale.

#### Scenario: Already dispositioned blocker is idempotent
- **WHEN** a route mutation cleanup sees a blocker that is not `repair_packet_open`
- **THEN** FlowPilot MUST NOT rewrite that blocker lifecycle status.
