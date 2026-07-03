## ADDED Requirements

### Requirement: Progress fraction uses the initial node plus active route order
When a current active route has a materialized `node_order`, FlowPilot SHALL
calculate `progress_fraction` from one display-only initial planning node plus
that active route order only. Historical route nodes, superseded repair-chain
nodes, task packets, and nodes outside the active route order SHALL NOT
contribute to `ended_nodes` or `expanded_nodes`.

#### Scenario: Superseded route history exists
- **WHEN** the ledger contains route nodes from old route versions
- **AND** the active route has `node_order` with four current node ids
- **THEN** `progress_fraction.expanded_nodes` is `5`
- **AND** the display-only initial planning node contributes one ended node
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

### Requirement: Initial planning node replaces packet projection fallback
Before a materialized active route order exists, FlowPilot SHALL report
`progress_fraction` as one display-only initial planning node with zero ended
nodes. Packet counts SHALL NOT become the public numerator or denominator.
Once active route order is available, FlowPilot SHALL keep the same initial
node and append current route nodes after it.

#### Scenario: Route nodes are not materialized yet
- **WHEN** no active route `node_order` is available
- **AND** public task packets may exist
- **THEN** `progress_fraction.display` is `0/1`
- **AND** `progress_fraction.packet_projection_used` is `false`

#### Scenario: Active route order is available
- **WHEN** active route `node_order` is available
- **THEN** packet projection is not used for the denominator or numerator
- **AND** `progress_fraction.display` is based on
  `1 + ended current route nodes` over `1 + current route nodes`
