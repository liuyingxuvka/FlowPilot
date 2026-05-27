## ADDED Requirements

### Requirement: Route display refresh follows route and frontier changes

FlowPilot SHALL refresh chat route signs and UI-readable route snapshots when
route or execution-frontier state changes.

#### Scenario: Route frontier advances
- **WHEN** the active route, active node, completed nodes, repair state, or
  terminal status changes
- **THEN** FlowPilot writes a refreshed display artifact with route/frontier
  version, active node, completed state, and freshness timestamp.

#### Scenario: Display artifact is stale
- **WHEN** a display artifact references an older route/frontier version than
  current state
- **THEN** FlowPilot marks it stale or refreshes it before using it as the
  user-visible route sign.

### Requirement: Display artifacts are not route authority

FlowPilot SHALL treat route display artifacts as projections of route state,
not as the route source of truth.

#### Scenario: Display contradicts route state
- **WHEN** a chat route sign or UI snapshot contradicts the current route or
  execution frontier
- **THEN** FlowPilot keeps the route/frontier files authoritative and records a
  display refresh or blocker instead of advancing from display data.
