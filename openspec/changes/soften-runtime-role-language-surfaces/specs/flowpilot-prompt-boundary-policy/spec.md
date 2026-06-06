## ADDED Requirements

### Requirement: User-visible role assistance language is topology-neutral
FlowPilot user-visible startup, prompt, and handoff surfaces SHALL describe
additional runtime assistance as host-supported role bindings requested by the
current runtime responsibility, not as a fixed crew, fixed role count, or
background-agent topology.

#### Scenario: Startup UI avoids fixed crew wording
- **WHEN** the startup intake UI asks whether FlowPilot may use additional
  runtime assistance
- **THEN** the visible label and body describe runtime role assistance or
  additional role bindings requested when needed
- **AND** they do not mention a fixed crew size as current behavior

#### Scenario: PM startup activation checks binding coverage
- **WHEN** PM reviews startup activation evidence
- **THEN** PM checks coverage for the runtime-requested role bindings, same-task
  rehydration evidence, or explicit blocked-role recovery authorization
- **AND** PM does not require a fixed role-count phrase as the checklist item

#### Scenario: Reference handoffs use recipient-role language
- **WHEN** active reference docs describe Controller handoff or role return
  reminders
- **THEN** they name the addressed recipient role or role binding
- **AND** they avoid sub-agent wording unless quoting or preserving historical
  evidence

#### Scenario: Internal schema names are not prompt authority
- **WHEN** current implementation still uses compatibility field names such as
  `background_agents`, `crew_ledger`, or `spawn_result`
- **THEN** prompt and public guidance explain the behavior with current
  runtime-requested role binding language
- **AND** the compatibility field name alone is not treated as user-facing
  current terminology
