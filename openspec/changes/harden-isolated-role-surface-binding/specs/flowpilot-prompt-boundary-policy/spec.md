## ADDED Requirements

### Requirement: Controller dispatch instructions are runtime-disposition driven
FlowPilot prompt surfaces SHALL describe role-surface dispatch as a mechanical
execution of the runtime's current role-assignment disposition.

#### Scenario: Reuse assignment uses runtime-named surface
- **WHEN** the runtime returns `reuse_existing_role` for a current packet
- **THEN** Controller-facing instructions SHALL require delivery to the
  existing runtime-named `effective_agent_id` surface
- **AND** the instructions SHALL forbid opening a fresh AI execution surface for
  that reuse assignment

#### Scenario: New surface opens only after runtime authorization
- **WHEN** the runtime returns `create_new_role` with `role_surface_required`
- **THEN** Controller-facing instructions SHALL allow opening a new
  host-supported isolated addressable AI execution surface only for that
  runtime assignment
- **AND** the instructions SHALL require retrying or committing through the
  runtime-provided command or assignment path

#### Scenario: Blocked assignment does not continue as foreground role work
- **WHEN** the runtime returns `blocked` for role dispatch
- **THEN** Controller-facing instructions SHALL require the blocker or recovery
  path
- **AND** the instructions SHALL forbid Controller from performing the role
  packet work in the foreground

### Requirement: Role work uses host-neutral isolated AI execution surfaces
FlowPilot prompt surfaces SHALL require formal PM, reviewer, worker,
FlowGuard-operator, and equivalent role packet work to run in a
host-supported isolated addressable AI execution surface instead of the
Controller foreground.

#### Scenario: Host provides equivalent non-background surfaces
- **WHEN** a host provides a separate conversation, thread, worker, independent
  AI session, background agent, or equivalent isolated addressable mechanism
- **THEN** FlowPilot prompt surfaces SHALL treat that mechanism as a valid role
  surface when the runtime requests a role binding
- **AND** the prompt surfaces SHALL NOT require a Codex-specific subagent,
  thread, or background-agent feature

#### Scenario: Controller foreground remains dispatch-only
- **WHEN** a formal role packet requires ACK, `open-packet`, or `submit-result`
- **THEN** prompt surfaces SHALL state that those role commands run inside the
  addressed isolated AI execution surface
- **AND** Controller SHALL remain limited to dispatch, wait, patrol, and
  runtime-directed recovery without reading sealed role bodies

### Requirement: Missing reuse surfaces are recovery or blocker conditions
FlowPilot prompt surfaces SHALL classify unreachable runtime-named reuse
surfaces as current recovery or blocker conditions unless the runtime
explicitly authorizes replacement.

#### Scenario: Existing surface is not addressable after resume
- **WHEN** a `reuse_existing_role` assignment names an existing
  `effective_agent_id`
- **AND** the host cannot address that surface after resume, compaction, or
  host limitation
- **THEN** Controller-facing instructions SHALL require the current
  recovery/blocker path
- **AND** the instructions SHALL forbid creating a fresh same-role surface as a
  silent substitute

### Requirement: Prompt-boundary validation covers isolated-surface drift
FlowPilot SHALL include focused validation that detects prompt drift around
runtime-directed isolated AI execution surfaces.

#### Scenario: Fresh-surface wording appears in reuse path
- **WHEN** active prompt or protocol text allows a fresh role surface for a
  `reuse_existing_role` assignment
- **THEN** prompt-boundary validation SHALL fail before installed-skill
  synchronization is claimed

#### Scenario: Product-specific wording becomes mandatory
- **WHEN** active prompt or protocol text requires a Codex-specific background
  agent, thread, subagent, or product feature as the only valid role surface
- **THEN** prompt-boundary validation SHALL fail before installed-skill
  synchronization is claimed
