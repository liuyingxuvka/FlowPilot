## ADDED Requirements

### Requirement: Same-Responsibility Leasing Prefers Current-Run Agent

FlowPilot SHALL prefer an existing usable current-run agent identity for every
same responsibility before assigning a fresh agent identity to that
responsibility. This applies uniformly to PM, Reviewer, FlowGuard operator,
worker-class, UI QA, planner, and any other current FlowPilot responsibility
registered in the runtime.

#### Scenario: PM receives another PM packet

- **WHEN** a PM packet is leased and the current-run role slot for `pm` has a
  reusable agent id
- **THEN** the new lease uses that same PM agent id
- **AND** the lease records that role continuity was reused.

#### Scenario: Reviewer receives another review packet

- **WHEN** a review packet is leased and the current-run role slot for
  `reviewer` has a reusable agent id
- **THEN** the new lease uses that same Reviewer agent id
- **AND** the lease records that role continuity was reused.

#### Scenario: FlowGuard operator receives another evidence packet

- **WHEN** a FlowGuard packet is leased and the current-run role slot for
  `flowguard_operator` has a reusable agent id
- **THEN** the new lease uses that same FlowGuard operator agent id
- **AND** the lease records that role continuity was reused.

#### Scenario: Fresh candidate is ignored while prior role is usable

- **WHEN** Controller supplies a fresh candidate agent id for a role whose
  current-run slot is still reusable
- **THEN** FlowPilot uses the current-run slot's agent id instead
- **AND** the fresh candidate is recorded as a rejected replacement candidate.

#### Scenario: Worker-class responsibility receives another packet

- **WHEN** a worker, research worker, UI QA, planner, or other registered
  responsibility receives another packet and its current-run role slot has a
  reusable agent id
- **THEN** the new lease uses that same-responsibility agent id
- **AND** the lease records that role continuity was reused.

### Requirement: Replacement Leases Carry Same-Responsibility Memory

FlowPilot SHALL attach current-run role memory to any replacement lease before
the replacement same-responsibility role opens its assigned packet.

#### Scenario: Prior PM is unavailable

- **WHEN** the current-run PM slot reports an unavailable, expired, superseded,
  or cancelled role state and Controller leases PM work to a new agent id
- **THEN** the new lease records the prior PM agent id
- **AND** the lease carries a current-run role memory seed.

#### Scenario: Prior non-PM role is unavailable

- **WHEN** the current-run Reviewer, FlowGuard operator, or worker slot reports
  an unavailable, expired, superseded, or cancelled role state and Controller
  leases same-role work to a new agent id
- **THEN** the new lease records the prior same-role agent id
- **AND** the lease carries a current-run role memory seed for that role.

#### Scenario: Missing memory blocks replacement open

- **WHEN** a replacement lease requires role memory but no memory seed can be
  created from the current run ledger
- **THEN** FlowPilot blocks packet opening for that replacement lease
- **AND** it records a role-memory blocker instead of letting the new role act
  without history.

### Requirement: Role Memory Uses Metadata Only

FlowPilot SHALL keep role memory summaries free of sealed packet and result
body text.

#### Scenario: Role opens a packet with memory

- **WHEN** a role opens an assigned packet whose lease has a memory seed
- **THEN** the open-packet result includes bounded role memory metadata for
  that role
- **AND** the memory contains no sealed packet body text and no sealed result
  body text.

#### Scenario: Controller receives handoff

- **WHEN** Controller receives the public role handoff
- **THEN** it may see whether role memory is present
- **AND** it cannot read the sealed packet body or role memory body through the
  handoff text.
