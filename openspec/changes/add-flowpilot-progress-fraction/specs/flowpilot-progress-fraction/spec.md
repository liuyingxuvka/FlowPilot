## ADDED Requirements

### Requirement: Runtime exposes current expanded progress fraction
FlowPilot runtime public outputs SHALL include a `progress_fraction` object
when current-run state is available. The object SHALL include numeric
`ended_nodes` and `expanded_nodes` fields and a `display` string formatted as
`<ended_nodes>/<expanded_nodes>`.

#### Scenario: One active work node has not ended
- **WHEN** the current run has one expanded work node and no ended work nodes
- **THEN** the runtime exposes `progress_fraction.display` as `0/1`

#### Scenario: Two of three expanded work nodes have ended
- **WHEN** the current run has three expanded work nodes and two ended work nodes
- **THEN** the runtime exposes `progress_fraction.display` as `2/3`

### Requirement: Progress counts expanded work nodes equally
FlowPilot progress counting SHALL treat every currently expanded work node as
one unit, including parent nodes, child nodes, and repair nodes. The runtime
MUST exclude control-plane mechanics such as acknowledgements, leases, patrols,
liveness checks, and role-assignment resolution from both counts.

#### Scenario: Repair work is expanded
- **WHEN** a repair work node is present in current-run state
- **THEN** the repair work node contributes one unit to `expanded_nodes`

#### Scenario: Control-plane mechanics occur
- **WHEN** runtime state contains ACK, lease, patrol, liveness, or
  role-assignment resolution records
- **THEN** those records do not change `ended_nodes` or `expanded_nodes`

### Requirement: Controller relays only runtime-owned progress
Controller-facing guidance SHALL permit user-facing status updates to include
the runtime-provided `progress_fraction.display` value when useful. The
Controller MUST NOT calculate progress, convert it to a percent, inspect sealed
packet bodies for progress, or treat the fraction as completion authority.

#### Scenario: Progress fraction is present
- **WHEN** a Controller status update is based on runtime output containing
  `progress_fraction.display`
- **THEN** the Controller may relay the value as the current expanded node
  fraction

#### Scenario: Progress fraction is absent
- **WHEN** runtime output does not contain `progress_fraction`
- **THEN** the Controller does not invent a progress value
