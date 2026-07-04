## ADDED Requirements

### Requirement: Prompt boundaries keep runtime mechanical
FlowPilot SHALL keep runtime/router prompts and policy text scoped to
mechanical authority while PM and Reviewer prompts own semantic interpretation,
source-intent preservation, quality review, and repair decisions.

#### Scenario: Runtime does not judge semantic vagueness
- **WHEN** a contract, review, or acceptance item uses vague wording
- **THEN** runtime MAY enforce that the required packet, result, review, or
  ledger surfaces exist
- **AND** runtime SHALL NOT decide whether the wording semantically satisfies
  the user request.

#### Scenario: Reviewer owns vague-contract blocking
- **WHEN** a reviewer prompt detects vague or source-losing acceptance wording
- **THEN** Reviewer SHALL block through existing review result fields
- **AND** PM SHALL repair through existing PM repair or reissue surfaces.

### Requirement: Prompt-card policy remains role-scoped
FlowPilot SHALL update shared and role-specific prompt language without giving
PM, Reviewer, FlowGuard operator, Worker, or Controller authority outside their
existing runtime-authorized role boundary.

#### Scenario: Quality wording does not leak repair authority
- **WHEN** prompt-card wording tells a role to improve quality or enforce
  source-intent preservation
- **THEN** the wording SHALL preserve the role's allowed read/write authority
- **AND** any out-of-role defect SHALL become a blocker, PM suggestion, or PM
  repair request rather than direct modification.
