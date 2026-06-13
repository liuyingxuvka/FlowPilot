## ADDED Requirements

### Requirement: Progress fraction uses the active route order
When a current active route has a materialized `node_order`, FlowPilot SHALL
calculate `progress_fraction` from that order only. Historical route nodes,
superseded repair-chain nodes, and nodes outside the active route order SHALL
NOT contribute to `ended_nodes` or `expanded_nodes`.

#### Scenario: Superseded route history exists
- **WHEN** the ledger contains route nodes from old route versions
- **AND** the active route has `node_order` with four current node ids
- **THEN** `progress_fraction.expanded_nodes` is `4`
- **AND** only ended statuses for those four current node ids contribute to
  `progress_fraction.ended_nodes`

### Requirement: Repair replacement preserves the active route slot count
FlowPilot SHALL treat a repair replacement as the current active route's
replacement node occupying the original route slot, not as an additional
historical node in user-visible progress.

#### Scenario: A node is replaced for repair
- **WHEN** an old route node is superseded by a replacement node
- **AND** the active route `node_order` contains the replacement node id and
  omits the superseded node id
- **THEN** the superseded node does not increase `progress_fraction.expanded_nodes`
- **AND** the replacement node contributes one unit according to its current
  status

### Requirement: Packet projection remains an early-route fallback
Before a materialized active route order exists, FlowPilot SHALL allow the
existing packet projection to provide `progress_fraction`. Once active route
order is available, route order SHALL take precedence over packet projection.

#### Scenario: Route nodes are not materialized yet
- **WHEN** no active route `node_order` is available
- **AND** public task packets exist
- **THEN** FlowPilot may calculate `progress_fraction` from eligible public
  task packets

#### Scenario: Active route order is available
- **WHEN** active route `node_order` is available
- **THEN** packet projection is not used for the denominator or numerator
