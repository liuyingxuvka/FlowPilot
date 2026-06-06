## ADDED Requirements

### Requirement: FlowPilot requires background or parallel role capability

FlowPilot SHALL require a host-supported isolated addressable background or
parallel role surface before it continues formal startup, manual resume
rehydration, role recovery, or runtime-requested role work.

#### Scenario: Host role surface is available
- **WHEN** FlowPilot starts or resumes and the host can provide an isolated
  addressable role surface
- **THEN** FlowPilot proceeds only through the current on-demand role assignment
  path
- **AND** role surfaces are opened, reused, replaced, or leased only when
  authorized by the current `resolve-role-assignment` / `lease-agent` flow

#### Scenario: Host role surface is unavailable
- **WHEN** FlowPilot starts or resumes and no current background or parallel
  role surface is available
- **THEN** FlowPilot records a structured stop reason
- **AND** FlowPilot MUST NOT continue through single-agent continuity, fixed
  startup roles, heartbeat automation, or historical role evidence

### Requirement: Startup enters PM work through Runtime mechanical entry

FlowPilot SHALL enter PM first-round work only after Runtime/Router completes
the current mechanical startup entry.

#### Scenario: Runtime mechanical entry passes
- **WHEN** Runtime has created the current run, sealed startup input, written
  startup mechanical audit, written display status, and audited current run
  identity
- **THEN** Router delivers the sealed `user_intake` packet to PM for the first
  material/intake decision
- **AND** FlowPilot MUST NOT require `reviewer.startup_fact_check`,
  `reviewer_reports_startup_facts`, `pm.startup_activation`, or
  `pm_approves_startup_activation`

#### Scenario: Legacy startup gate is submitted
- **WHEN** an AI or host submits an old Reviewer startup fact output, PM startup
  activation output, startup repair request, or startup protocol dead-end event
- **THEN** Runtime rejects it as unsupported current input
- **AND** protected startup, packet, route, role, or terminal state does not
  advance

### Requirement: Startup background control is an acknowledgement, not fallback selection

FlowPilot SHALL treat the startup background collaboration control as an
acknowledgement of a required capability, not as a product-mode selector.

#### Scenario: User leaves acknowledgement enabled
- **WHEN** the startup intake result records
  `background_collaboration_authorized=true`
- **THEN** FlowPilot may attempt current background or parallel role work after
  the remaining startup gates pass

#### Scenario: User disables acknowledgement
- **WHEN** the startup intake result records
  `background_collaboration_authorized=false`
- **THEN** FlowPilot records that the required background role acknowledgement is
  disabled and stops formal startup
- **AND** FlowPilot MUST NOT generate downstream startup, route, role, or
  implementation work

### Requirement: Legacy single-agent and heartbeat paths are unsupported

FlowPilot SHALL reject legacy startup, resume, and role paths as unsupported
current input.

#### Scenario: AI submits old startup fields
- **WHEN** a startup result includes `runtime_role_assistances`, `single-agent`,
  scheduled heartbeat fields, or fixed role startup fields
- **THEN** the router rejects the result as unsupported current input
- **AND** no compatibility translation is applied

#### Scenario: AI submits legacy resume or heartbeat events
- **WHEN** a role output, fake-AI package, or host event submits
  `heartbeat_or_manual_resume_requested`, `host_records_heartbeat_binding`, or
  `create_heartbeat_automation`
- **THEN** FlowPilot rejects or quarantines the legacy input as a negative-path
  event
- **AND** protected route, packet, role, or terminal state does not advance

### Requirement: Fake-AI packages cover mandatory background failures

FlowPilot SHALL include fake-AI package tests for missing or disabled background
role capability.

#### Scenario: Fake AI omits required capability evidence
- **WHEN** a fake AI package tries to complete startup, resume rehydration, or
  role recovery without required background role capability evidence
- **THEN** FlowPilot rejects the package with a repairable structured error that
  names the missing field or disabled acknowledgement
- **AND** the same test proves a corrected package is accepted through the one
  current path
