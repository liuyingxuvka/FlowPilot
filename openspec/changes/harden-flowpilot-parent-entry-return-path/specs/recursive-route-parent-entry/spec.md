## ADDED Requirements

### Requirement: Parent entry gate precedes child descent

FlowPilot SHALL require every selected effective parent or module node to have its own current accepted `node_acceptance_plan` and `node_context_package` before runtime enters any child descendant.

#### Scenario: Later sibling parent requires its own entry gate

- **WHEN** one parent/module node has completed and the next effective sibling parent/module has incomplete children
- **THEN** runtime keeps the frontier on the sibling parent/module until that parent/module has its own accepted node plan and context package
- **AND** runtime MUST NOT jump directly to the sibling parent's first child.

#### Scenario: Child plan cannot substitute for parent plan

- **WHEN** a child node has a current accepted node plan and context package
- **AND** its parent/module node lacks its own current accepted node plan or context package
- **THEN** runtime MUST treat the parent/module entry gate as incomplete
- **AND** runtime MUST NOT use the child artifacts to satisfy the parent/module gate.

#### Scenario: Mutation-created parent starts at its own gate

- **WHEN** route mutation commits a new parent/module or promotes a node into a parent/module
- **THEN** the new parent/module MUST enter the normal node-entry gate before child execution
- **AND** inherited or superseded child history MUST remain historical context only.

### Requirement: Parent late-stage gates assert impossible missing entry state

FlowPilot SHALL treat a missing current parent/module entry gate at parent replay, PM disposition, or final-dispatch preflight as a control-plane hard-gate escape, not as a late evidence-gathering opportunity.

#### Scenario: Parent replay sees missing parent entry gate

- **WHEN** runtime is about to issue or accept parent backward replay for a parent/module
- **AND** that parent/module lacks its own current accepted node plan or context package
- **THEN** runtime MUST stop normal parent replay and return a `control_plane_hard_gate_escape` for that parent/module's node-entry gate.

#### Scenario: PM disposition sees missing parent entry gate

- **WHEN** PM disposition is attempted for a parent/module
- **AND** that parent/module lacks its own current accepted node plan or context package
- **THEN** runtime MUST reject the disposition as a control-plane hard-gate escape instead of letting PM accept or waive the missing gate.
