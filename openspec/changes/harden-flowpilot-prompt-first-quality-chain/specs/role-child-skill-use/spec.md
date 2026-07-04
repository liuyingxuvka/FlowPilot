## ADDED Requirements

### Requirement: Child skills act as standards lenses in the same route
FlowPilot SHALL require PM child-skill prompts to treat selected child skills
as standards and evidence sources inside the existing FlowPilot route, not as
separate artifact-family workflows.

#### Scenario: PM selects child skill with concrete standard purpose
- **WHEN** PM marks a child skill as required or conditional
- **THEN** PM SHALL state what quality risk or acceptance standard the skill
  covers, which role uses it, what evidence proves use, and where the standard
  is projected into existing route, node, review, or final-ledger surfaces.

#### Scenario: Selected skill standards cannot be theme-only
- **WHEN** a selected child skill contains concrete MUST, VERIFY, LOOP,
  ARTIFACT, FORBID, or WAIVER standards
- **THEN** PM SHALL carry the relevant standards into existing
  `skill_standard_projection`, `active_child_skill_bindings`, role-skill
  bindings, or gate evidence expectations
- **AND** Reviewer SHALL block if those standards are omitted, weakened, or
  replaced by generic wording.

### Requirement: Child-skill use remains minimum-complexity aware
FlowPilot SHALL require PM prompts to reject, defer, or scope child skills that
do not improve the current acceptance, evidence, review, modeling, validation,
or repair confidence.

#### Scenario: Child skill not needed for simple task
- **WHEN** a child skill exists locally but adds no current acceptance or
  evidence value
- **THEN** PM SHALL record a rejected or deferred decision with reason
- **AND** PM SHALL NOT create extra route branches merely because the skill
  exists.
