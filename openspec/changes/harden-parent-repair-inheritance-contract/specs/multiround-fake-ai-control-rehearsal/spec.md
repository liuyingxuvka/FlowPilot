## ADDED Requirements

### Requirement: Fake AI rehearsal covers parent repair empty-node loops
FlowPilot SHALL include prepared fake AI control rehearsals that prove empty
replacement parent repair nodes, prose-only child routing, and format-only
FlowGuard passes cannot advance the route.

#### Scenario: Bad PM parent repair is rejected
- **WHEN** a fake PM chooses `repair_parent_scope` without repair child specs
- **THEN** the rehearsal MUST show Runtime rejecting the PM result
- **AND** the route MUST NOT advance to an empty replacement parent repair node.

#### Scenario: Prose-only child plan is rejected
- **WHEN** a fake PM node acceptance plan describes child leaves in prose but the route node has no active child ids
- **THEN** the rehearsal MUST show Runtime or Reviewer blocking the plan
- **AND** the rehearsal MUST NOT count the plan as parent repair progress.

#### Scenario: Bad FlowGuard pass is rejected
- **WHEN** a fake FlowGuard report returns `passed: true` while its evidence artifact reports a blocker or `missing_code_contract`
- **THEN** the rehearsal MUST show FlowPilot rejecting the pass claim
- **AND** the blocker or missing contract MUST remain visible in the rehearsal evidence.

#### Scenario: Correct parent repair advances
- **WHEN** a fake PM chooses `repair_parent_scope` with inherited history and one or more repair child specs
- **AND** fake child results and parent backward replay satisfy the repair contract
- **THEN** the rehearsal MUST show the replacement parent progressing through the legal child subtree and replay path
- **AND** inherited children MUST remain context-only in the evidence.
