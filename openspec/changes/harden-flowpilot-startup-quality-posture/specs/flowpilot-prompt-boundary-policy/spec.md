## ADDED Requirements

### Requirement: Operational role prompts present one normal formal path
FlowPilot SHALL keep role-facing operational startup, PM, Reviewer, Worker, and
packet prompts focused on the current formal work path and SHALL NOT present
alternate non-operational route labels as choices for role agents.

#### Scenario: Backend role receives a work packet
- **WHEN** a Worker, Reviewer, PM, or FlowGuard operator receives a current
  work packet or role card
- **THEN** the prompt MUST describe the assignment as normal high-quality
  current-run work within the Router-authorized packet boundary
- **AND** the prompt MUST NOT ask the role to classify whether the invocation
  belongs to an alternate non-operational path.

#### Scenario: Validation models bad prompt variants
- **WHEN** FlowPilot validates prompt drift with tests or FlowGuard models
- **THEN** validation artifacts MAY name forbidden or bad-case variants
- **AND** those variant names MUST NOT be required as role-facing operational
  prompt text.

#### Scenario: Launcher remains single operational entry surface
- **WHEN** a fresh FlowPilot startup is initiated through the public skill
  guidance
- **THEN** the operational path remains the existing fresh formal startup path
- **AND** this change MUST NOT add a new launcher, fallback route, or entry
  surface.
