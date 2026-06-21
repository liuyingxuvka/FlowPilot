## ADDED Requirements

### Requirement: Formal reviewer pass includes PM-facing improvement suggestions

FlowPilot SHALL require formal reviewer reports to include nonempty
`pm_suggestion_items` when the review passes, so PM receives higher-standard
decision support even when minimum gate requirements are met.

#### Scenario: Passing review omits PM suggestions
- **WHEN** a formal reviewer result claims pass
- **AND** `pm_suggestion_items` is missing or empty
- **THEN** runtime MUST reject or reissue the reviewer result as an incomplete
  review report contract
- **AND** runtime MUST NOT classify the reviewed work itself as failed solely
  because suggestions are missing

#### Scenario: Passing review includes improvement suggestions
- **WHEN** a formal reviewer result claims pass and includes at least one
  concrete PM-facing suggestion tied to the reviewed scope
- **THEN** runtime MAY accept the review report if all other review contract
  fields pass

### Requirement: Reviewer blockers stay tied to minimum gate failures

FlowPilot SHALL distinguish hard blockers from high-standard suggestions in
formal review reports.

#### Scenario: Quantitative or minimum requirement is not met
- **WHEN** the current gate requires a measurable amount, required artifact,
  acceptance item, evidence source, role boundary, or protocol condition
- **AND** the reviewed result does not satisfy that minimum
- **THEN** Reviewer MUST return a blocker with actionable repair guidance

#### Scenario: Minimum passes but quality could improve
- **WHEN** the reviewed result satisfies the minimum current gate standard
- **AND** Reviewer identifies a cleaner, deeper, better-structured, or more
  complete option
- **THEN** Reviewer MUST record the item in `pm_suggestion_items` rather than
  as a blocker

### Requirement: Reviewer packet explains current review scope and scoring standard

FlowPilot SHALL provide reviewers enough current structured context to judge the
current gate, including the current stage, source packet/result references,
review window, minimum blocker standard, and higher-standard scoring rubric.

#### Scenario: Review packet lacks current gate context
- **WHEN** a reviewer work packet omits the current gate kind, source packet or
  result reference, or review window needed to identify what is being reviewed
- **THEN** fake-AI and runtime coverage MUST classify the packet as incomplete
  and require repair before a quality pass can be trusted

#### Scenario: Reviewer has score guidance without new schema
- **WHEN** the reviewer receives a formal review packet
- **THEN** the packet text MUST include the scoring standard in prose while
  preserving existing structured result fields
