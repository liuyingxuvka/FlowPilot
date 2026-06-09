## ADDED Requirements

### Requirement: Display projection is derived from canonical route state

FlowPilot SHALL treat host-visible route displays as projections of the
canonical route and execution frontier. PM SHALL NOT maintain a second
PM-authored route solely for display.

#### Scenario: Display needs concise route status

- **WHEN** Controller needs a concise visible route status
- **THEN** FlowPilot derives it from current route nodes, active path, completed
  nodes, and frontier status
- **AND** the display artifact remains non-authoritative.

#### Scenario: Display artifact exists as cache

- **WHEN** a display artifact is written for UI or host consumption
- **THEN** it is treated as a cache or projection of canonical route state
- **AND** it cannot add, remove, merge, split, or reorder route nodes.
