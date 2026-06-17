## ADDED Requirements

### Requirement: Review Packets Use Stage-Owned Contracts

FlowPilot review and FlowGuard packets SHALL use the subject packet family's
stage matrix row to determine the only valid blocker classes and next actions.
They SHALL NOT carry future-stage evidence requirements into earlier packet
families.

#### Scenario: Reviewer reviews planning package
- **WHEN** Reviewer reviews a `task.planning` subject
- **THEN** Reviewer SHALL judge route structure, parent/child consistency, and
  acceptance item assignment, and SHALL NOT block for missing worker result or
  terminal replay evidence

#### Scenario: FlowGuard reviews node result
- **WHEN** FlowGuard reviews a `task.node` subject
- **THEN** FlowGuard SHALL model current node evidence, stale-evidence risk,
  and process risk using the node-stage blocker classes

### Requirement: Role Result Bodies Stay Compact

FlowGuard and Reviewer result bodies SHALL expose PM-facing summaries,
findings, blockers, and suggestions only. Role-specific deep evidence SHALL
live in the role-owned run-local evidence path declared by the packet family.

#### Scenario: Reviewer submits compact blocker
- **WHEN** Reviewer blocks a current-stage quality issue
- **THEN** the result body SHALL contain the PM-facing finding, fixed blocker
  class, fixed next action, and contract self-check

