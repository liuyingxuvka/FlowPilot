## ADDED Requirements

### Requirement: Role Assignment Resolves Before Surface Creation

FlowPilot SHALL resolve whether a packet needs an existing role surface, a new
role surface, or a blocker before Controller opens any new same-responsibility
role surface.

#### Scenario: Existing role is reusable

- **WHEN** a packet is ready for a responsibility whose current-run role slot
  has a reusable agent id
- **THEN** the role-assignment result is `reuse_existing_role`
- **AND** it names the existing agent id
- **AND** it does not require or expose a fresh candidate agent id.

#### Scenario: No current-run role exists

- **WHEN** a packet is ready for a responsibility with no role slot and no
  same-responsibility current-run lease history
- **THEN** the role-assignment result is `create_new_role`
- **AND** Controller may open a new role surface only for the assignment id
  returned by the runtime.

#### Scenario: Controller-facing action uses resolver

- **WHEN** the lifecycle guard asks Controller to dispatch a role packet
- **THEN** the public next action names the role-assignment resolver
- **AND** it does not instruct Controller to pass `<new-agent-id>` to
  `lease-agent`.

### Requirement: Missing Continuity Slots Do Not Silently Initialize

FlowPilot SHALL NOT silently initialize a fresh same-responsibility role when a
current run has same-responsibility lease history but no role-continuity slot.

#### Scenario: Same-run history can be hydrated

- **WHEN** a packet is ready for a responsibility with no role slot
- **AND** the current run has a usable same-responsibility public lease history
  row
- **THEN** the resolver hydrates the role slot from that current-run lease
  metadata
- **AND** the role-assignment result is `reuse_existing_role`.

#### Scenario: Same-run history is not safely reusable

- **WHEN** a packet is ready for a responsibility with no role slot
- **AND** the current run has same-responsibility lease history that cannot be
  safely reused
- **THEN** the role-assignment result is `blocked`
- **AND** the blocker names role-continuity recovery instead of creating a new
  role.

### Requirement: Lease Commit Uses Authorized Assignment

FlowPilot SHALL commit a role lease only from a current role-assignment
authorization.

#### Scenario: Reuse assignment is committed

- **WHEN** Controller commits a `reuse_existing_role` assignment
- **THEN** the lease uses the assignment's existing agent id
- **AND** no rejected fresh candidate id is recorded for that lease.

#### Scenario: New role assignment is committed

- **WHEN** Controller commits a `create_new_role` assignment with the newly
  opened role surface id
- **THEN** the lease uses the authorized new agent id
- **AND** the assignment is marked consumed so it cannot be reused for another
  packet.

#### Scenario: Raw agent id commit is rejected

- **WHEN** Controller calls the public lease commit with a raw agent id but no
  current assignment authorization
- **THEN** FlowPilot rejects the call as an unsupported current-contract path.
