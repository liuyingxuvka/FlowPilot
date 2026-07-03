## ADDED Requirements

### Requirement: Runtime counts expanded route nodes by lifecycle disposition
FlowPilot runtime public outputs SHALL calculate `progress_fraction` from the display-only initial planning node plus current-run expanded work nodes recorded in `route_nodes`. The runtime SHALL NOT use active route `node_order` as the sole denominator once route nodes exist.

#### Scenario: No route nodes exist
- **WHEN** the current run has no materialized `route_nodes`
- **THEN** `progress_fraction.display` is `0/1`
- **AND** `progress_fraction.source` identifies the initial planning node

#### Scenario: Supplemental materialization narrows active node order
- **WHEN** an earlier materialization created multiple route nodes
- **AND** a later materialization overwrites active `node_order` with a shorter supplemental list
- **AND** the earlier nodes have no formal removal disposition
- **THEN** the earlier nodes still contribute to `progress_fraction.expanded_nodes`
- **AND** progress SHALL NOT collapse to the shorter active `node_order`

### Requirement: Denominator reduction requires formal node or route disposition
FlowPilot SHALL allow `progress_fraction.expanded_nodes` to shrink only when formal runtime state proves removed nodes are no longer effective obligations through supersession, cancellation, or an explicit route mutation disposition that marks the old node non-effective. Absence from active `node_order` alone SHALL NOT remove a node from the denominator.

#### Scenario: Node is formally superseded
- **WHEN** a route node status is `superseded`
- **THEN** the runtime may remove the node from `progress_fraction.expanded_nodes`
- **AND** the node MUST NOT remain as an unfinished progress obligation

#### Scenario: Node disappears only from node_order
- **WHEN** a route node remains in `route_nodes`
- **AND** the node is not formally superseded, cancelled, or otherwise dispositioned as non-effective by route mutation evidence
- **AND** active `node_order` no longer lists the node
- **THEN** the node still contributes to `progress_fraction.expanded_nodes`

### Requirement: Route structure changes map to progress consistently
FlowPilot progress SHALL treat route replanning and mutation categories according to their formal topology: ordinary node additions and child-node expansions add expanded nodes; node-internal replans do not change the denominator unless they materialize route nodes; repair nodes add expanded nodes while formally superseded replaced nodes may leave the denominator; branch-then-continue keeps the continuation nodes; sibling-branch replacement counts replacement nodes and removes superseded siblings according to formal disposition.

#### Scenario: Branch then continue
- **WHEN** a route mutation adds a bounded detour and declares a continue target
- **THEN** the detour nodes and unchanged continuation nodes remain represented in `progress_fraction.expanded_nodes`

#### Scenario: Full route rewrite
- **WHEN** a full route rewrite formally supersedes or cancels old effective nodes
- **THEN** `progress_fraction.expanded_nodes` may reflect the new effective node set
- **AND** the old nodes MUST NOT disappear without corresponding lifecycle or mutation disposition

### Requirement: Control-plane records remain excluded
FlowPilot progress counting SHALL exclude packets, ACKs, leases, patrols, liveness checks, role assignment, Controller receipts, and sealed packet/result bodies from both numerator and denominator.

#### Scenario: Packet activity occurs without route-node lifecycle change
- **WHEN** packet, lease, ACK, or role-assignment records change
- **AND** no route node is added or lifecycle-dispositioned
- **THEN** `progress_fraction.ended_nodes` and `progress_fraction.expanded_nodes` do not change because of those control-plane records

### Requirement: Progress lifecycle coverage is Cartesian within the declared finite universe
FlowPilot SHALL maintain executable coverage for the finite progress lifecycle universe covering node status, route topology, active `node_order` projection, route node kind, control-plane noise, and repair generation. The coverage SHALL include a FlowGuard ContractExhaustion receipt and TestMesh evidence for the generated combination shards.

#### Scenario: Declared progress universe is exhaustively exercised
- **WHEN** the progress lifecycle Cartesian runner executes
- **THEN** every declared axis value appears in at least one generated cell
- **AND** every generated cell's runtime `progress_fraction` matches the lifecycle oracle
- **AND** active `node_order` projection variants do not change numerator, denominator, or source
- **AND** control-plane noise variants do not change numerator, denominator, or source
