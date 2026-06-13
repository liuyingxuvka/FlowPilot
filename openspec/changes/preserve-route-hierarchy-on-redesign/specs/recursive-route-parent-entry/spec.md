## ADDED Requirements

### Requirement: Route redesign preserves executable hierarchy

FlowPilot SHALL treat PM route redesign output as one canonical executable
route tree. When a route redesign decomposes complex work, the redesigned plan
MUST preserve parent/module composition boundaries with existing
`node_kind`, `parent_node_id`, and `child_node_ids` fields instead of flattening
all work into unrelated top-level leaf nodes.

#### Scenario: Complex redesign is not flattened
- **WHEN** PM returns a route redesign containing many related executable
  leaves that share stage-level goals such as source collection, modeling,
  implementation, validation, reporting, or closure
- **THEN** the redesigned route records parent/module nodes for the shared
  goals and ordered child leaves under those parents/modules
- **AND** Reviewer or FlowGuard blocks the redesign if PM presents the related
  work as unrelated top-level leaves without a concrete no-parent rationale.

#### Scenario: Parent and leaf shapes are mechanically consistent
- **WHEN** Runtime validates a strict route plan
- **THEN** every parent or module node with effective child work has explicit
  child node ids
- **AND** every leaf node is worker-dispatchable and has no child node ids
- **AND** child node references resolve to nodes in the same route plan.

#### Scenario: Recursive depth is preserved
- **WHEN** a child node is itself too broad and PM decomposes it further
- **THEN** that child becomes a parent/module for its own ordered descendants
- **AND** the resulting route tree may have more than two levels while still
  preserving serial execution order.

### Requirement: Node-entry decomposition promotes the active node

FlowPilot SHALL treat node-entry `redesign_route` for an over-broad current
node as a local subtree redesign. The active node or its replacement scope MUST
become a parent/module that owns the newly decomposed child nodes before any
worker packet is dispatched for the decomposed work.

#### Scenario: Current leaf becomes parent when split
- **WHEN** PM determines during node acceptance planning that the active leaf is
  too broad for one bounded worker outcome
- **THEN** PM returns `decision: "redesign_route"` with a route plan that
  promotes the active node or replacement scope to parent/module
- **AND** the new child nodes are attached under that parent/module instead of
  being appended as unrelated peers.

#### Scenario: Reviewer blocks peer append split
- **WHEN** Reviewer inspects a node-entry redesign that decomposes the active
  node but leaves the active node as a leaf and appends the proposed pieces as
  peer nodes
- **THEN** Reviewer blocks the plan before worker dispatch
- **AND** the required PM repair is to preserve the active node's subtree
  ownership and rerun the route-redesign gate.

#### Scenario: Parent closure remains required after local split
- **WHEN** all children introduced by a node-entry split are completed
- **THEN** FlowPilot returns to the promoted parent/module for parent backward
  replay and PM parent disposition
- **AND** the route does not leave the parent scope until that parent-level
  review and disposition pass.
