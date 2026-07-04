## ADDED Requirements

### Requirement: Reviewer gates preserve source intent
FlowPilot SHALL require reviewer-facing gate prompts to compare the reviewed
artifact or package against the user's source intent, the accepted requirement
trace, and the current acceptance rows when those materials are available to
the gate.

#### Scenario: Reviewer blocks generic root contract
- **WHEN** Reviewer reviews a root contract or acceptance package for a
  non-trivial user request
- **AND** the contract reduces concrete source requirements to generic wording
  such as completing the user goal without preserving the concrete acceptance
  force
- **THEN** Reviewer SHALL block the gate through existing blocked-review fields
- **AND** Reviewer SHALL recommend PM repair by returning to the source intent
  and current acceptance rows rather than asking runtime to judge semantics.

#### Scenario: Reviewer compares actual artifact, not only process evidence
- **WHEN** Reviewer reviews a worker result, evidence package, or final replay
- **THEN** Reviewer SHALL compare the actual result or delivered artifact
  against the current acceptance slice and source-intent obligations
- **AND** Reviewer SHALL NOT pass solely because a FlowGuard report, ledger row,
  file, screenshot, or process artifact exists.

### Requirement: FlowGuard process evidence remains separate from product quality
FlowPilot SHALL require reviewer and FlowGuard-operator prompts to keep process
or model evidence separate from final user-facing quality evidence.

#### Scenario: FlowGuard report cannot prove product quality alone
- **WHEN** a gate has a current FlowGuard report but lacks direct product,
  artifact, or user-intent satisfaction evidence
- **THEN** FlowGuard evidence MAY support process/state freshness
- **AND** Reviewer SHALL still require semantic quality evidence before passing
  a user-facing quality claim.
