## ADDED Requirements

### Requirement: Current-node worker dispatch respects canonical route shape

FlowPilot SHALL check canonical route-node structure before issuing a
current-node worker task packet. PM disposition, Reviewer review, and accepted
node acceptance plans SHALL NOT override a non-worker-dispatchable node shape.

#### Scenario: Worker packet creation checks active node structure

- **WHEN** Runtime is about to create a worker task packet for the active node
- **THEN** it checks the active node's existing `node_kind` and
  `child_node_ids`
- **AND** it rejects worker dispatch for parent/module or child-bearing nodes.

#### Scenario: Node plan supports but does not replace route structure

- **WHEN** a node acceptance plan is accepted for a route node
- **THEN** the plan can provide execution context for a leaf
- **AND** it cannot turn a parent/module or child-bearing node into a worker
  task scope.
