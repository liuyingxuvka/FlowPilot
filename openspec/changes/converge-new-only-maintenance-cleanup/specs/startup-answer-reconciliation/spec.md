## ADDED Requirements

### Requirement: Native Startup Intake Owns Startup Answers
FlowPilot SHALL treat the native startup intake result and deterministic seed evidence
as the current owner of startup answers.

#### Scenario: Startup answers are already seeded
- **WHEN** native startup intake has recorded valid startup answers and deterministic
  seed evidence for the current run
- **THEN** Router does not create, expose, or reconcile a separate legacy
  answer-recording row for those answers
- **AND** stale receipts for retired answer-recording work SHALL NOT overwrite the
  durable startup answers.
