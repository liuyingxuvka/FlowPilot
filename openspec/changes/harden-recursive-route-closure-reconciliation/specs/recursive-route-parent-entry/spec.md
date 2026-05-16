## ADDED Requirements

### Requirement: Parent and module nodes are entered before descendants

FlowPilot route traversal SHALL treat every effective non-root parent or module
node as an executable scope before entering any of its child descendants.

#### Scenario: Sibling module follows completed parent

- **WHEN** a parent/module and all of its children are completed
- **AND** the next effective sibling module has incomplete child nodes
- **THEN** the next route node is the sibling module itself
- **AND** FlowPilot does not jump directly to the sibling module's first leaf.

#### Scenario: Parent closes after its children

- **WHEN** all effective direct children of a parent/module are completed
- **AND** the parent/module itself is not completed
- **THEN** FlowPilot returns that parent/module for local parent review and
  completion before leaving the parent scope.

#### Scenario: Route root is not a worker scope

- **WHEN** the effective route contains a root node with children
- **THEN** route traversal does not select the root as a worker/reviewer node.
