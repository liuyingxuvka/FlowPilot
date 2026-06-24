## ADDED Requirements

### Requirement: Parent backward closure is one Reviewer packet
FlowPilot SHALL represent parent/module backward closure as one current
`review.parent_backward_replay` packet/result. A passing result from that packet
SHALL be the reviewer signature for the parent/module closure gate and SHALL
NOT require a second `review.any_current_subject` packet over the same result.

#### Scenario: Parent backward review closes the review gate
- **WHEN** the current frontier parent/module node has all required child
  results accepted
- **AND** a current `review.parent_backward_replay` result passes mechanical,
  FlowGuard, and system validation
- **THEN** FlowPilot SHALL record the parent backward review closure evidence
- **AND** FlowPilot SHALL open or reuse the PM parent segment decision gate
- **AND** FlowPilot SHALL NOT issue a second review packet for the same parent
  backward review result

#### Scenario: Old task-shaped parent replay is rejected
- **WHEN** a submitted or injected parent backward result uses
  `task.parent_backward_replay`
- **THEN** FlowPilot SHALL reject it as an unsupported current-contract shape
- **AND** FlowPilot SHALL NOT translate, migrate, or promote it into current
  closure evidence

### Requirement: Parent backward review controls downstream progression
FlowPilot SHALL block sibling, ancestor, terminal, and final-preflight
progression until the current parent/module backward review is accepted and PM
has absorbed it through the parent segment decision.

#### Scenario: Parent review missing blocks downstream work
- **WHEN** a parent/module node with children is the current closure frontier
- **AND** no accepted current `review.parent_backward_replay` exists for that
  node
- **THEN** FlowPilot SHALL expose the parent backward review packet for that
  current node
- **AND** FlowPilot SHALL NOT open downstream sibling, ancestor, terminal, or
  final-closure work

#### Scenario: PM absorption missing blocks downstream work
- **WHEN** a parent/module backward review passed
- **AND** PM has not recorded a `continue` parent segment decision for that
  review
- **THEN** FlowPilot SHALL expose the PM parent segment decision as the current
  action
- **AND** FlowPilot SHALL NOT open downstream sibling, ancestor, terminal, or
  final-closure work

### Requirement: Multiple unclosed parent review gaps are corrupt state
FlowPilot SHALL treat multiple simultaneous unclosed parent/module backward
review gaps as control-plane corruption or injected impossible state, not as a
normal dependency-ordered repair queue.

#### Scenario: Injected multi-gap state hard-blocks
- **WHEN** the runtime state contains more than one unclosed parent/module
  backward review obligation
- **AND** downstream route state has advanced beyond at least one unclosed
  parent/module gate
- **THEN** FlowPilot SHALL return a hard control-plane blocker
- **AND** FlowPilot SHALL NOT select one gap for compatibility repair
- **AND** FlowPilot SHALL NOT continue terminal or final closure

### Requirement: Cartesian fake-AI coverage owns current parent review payloads
FlowPilot SHALL include a model-scoped fake-AI Cartesian coverage universe for
the single parent backward review contract, including valid payloads, missing
field profiles, wrong shape profiles, stale evidence profiles, timing profiles,
route-shape profiles, old-shape rejection, no-second-review assertions, and
corrupt multi-gap hard blockers.

#### Scenario: Coverage cells are complete
- **WHEN** the parent backward review Cartesian checker runs
- **THEN** every required legal and illegal coverage cell SHALL have an oracle
  and an owner
- **AND** the acceptance TestMesh SHALL report no missing parent backward
  review payload cells
