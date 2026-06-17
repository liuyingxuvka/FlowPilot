## ADDED Requirements

### Requirement: Parent repair replacement inherits history and requires active repair children
FlowPilot SHALL materialize `repair_parent_scope` as a replacement parent
repair node that inherits old child history as read-only context and uses only
new repair child nodes as the active executable child subtree.

#### Scenario: Parent repair creates current repair children
- **WHEN** PM chooses `repair_parent_scope` for a blocked child or parent scope
- **THEN** Runtime MUST supersede the nearest explicit parent scope and its descendants as current authority
- **AND** Runtime MUST create a replacement parent repair node
- **AND** Runtime MUST create one or more active repair child nodes from PM-provided repair child specs
- **AND** the replacement parent's active `child_node_ids` MUST contain those new repair child ids.

#### Scenario: Old children are inherited as context only
- **WHEN** Runtime creates a replacement parent repair node
- **THEN** Runtime MUST record the superseded parent's previous child ids as inherited historical child ids
- **AND** Runtime MUST record eligible accepted child result refs as inherited context evidence
- **AND** Runtime MUST NOT treat inherited child ids as current executable child ids.

#### Scenario: Empty replacement parent is rejected
- **WHEN** `repair_parent_scope` would create a replacement parent or module repair node with no active repair children
- **THEN** Runtime MUST reject the repair transition
- **AND** Runtime MUST NOT open a fresh parent repair packet for an empty parent.

### Requirement: PM parent repair contracts define new child work structurally
FlowPilot SHALL require PM parent-scope repair decisions to provide a structured
parent repair contract that names the new repair child work to be created.

#### Scenario: Structured repair child specs are present
- **WHEN** PM submits a `repair_parent_scope` decision
- **THEN** the result MUST include a parent repair contract with `inherit_existing_children: true`
- **AND** the contract MUST include nonempty `repair_child_specs`
- **AND** each repair child spec MUST name the child id or id seed, purpose, and required evidence.

#### Scenario: Prose-only child work is invalid
- **WHEN** PM text says the replacement parent will route to child leaves but the parent repair contract lacks repair child specs
- **THEN** Runtime MUST reject the PM result as mechanically incomplete
- **AND** Reviewer and FlowGuard MUST NOT treat the prose as route-node authority.

#### Scenario: PM does not hand-copy inherited child history
- **WHEN** PM submits a parent repair contract
- **THEN** Runtime MUST derive inherited child ids and inherited accepted result refs from current ledger state
- **AND** PM-provided inherited child lists MUST NOT override Runtime's derived current-authority view.
