## ADDED Requirements

### Requirement: Parent and module nodes are never worker task scopes

FlowPilot SHALL keep non-root parent and module nodes as composition, subtree
planning, and parent-replay scopes. Runtime SHALL NOT create worker task
packets for a parent/module node or for any node that still has effective
children.

#### Scenario: Accepted node plan does not override parent shape

- **WHEN** a parent/module node has an accepted node acceptance plan
- **AND** the node still has effective children
- **THEN** FlowPilot still refuses worker packet creation for that node
- **AND** FlowPilot enters child traversal or parent backward replay instead.

#### Scenario: Child-bearing leaf shape is refused

- **WHEN** a node is declared as a leaf but still lists child nodes
- **THEN** FlowPilot treats it as non-worker-dispatchable
- **AND** the route must be repaired or normalized before worker dispatch.
