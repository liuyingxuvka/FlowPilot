## ADDED Requirements

### Requirement: Reviewer Blocks Missing Global Standard Context
FlowPilot SHALL require Reviewer gates to block PM or worker packages whose
existing referenced artifacts cannot recover the current user standard, PM
high-standard execution intent, acceptance criteria, risks, and verification
standard needed to judge the gate.

#### Scenario: Node plan lacks recoverable global context
- **WHEN** Reviewer reviews a node acceptance plan whose
  `relevant_references`, acceptance criteria, risks, or acceptance-item
  projection do not let Reviewer recover the current user/PM standard
- **THEN** Reviewer SHALL return a normal blocked review report using existing
  `blockers` and `recommended_resolution` fields.

#### Scenario: Worker result meets local text but downgrades source intent
- **WHEN** a Worker result satisfies a local task sentence but weakens,
  omits, or replaces a current user-sourced or PM high-standard acceptance item
- **THEN** Reviewer SHALL classify that as an unmet current gate standard and
  SHALL block or request PM repair through existing review fields.

#### Scenario: High-quality suggestion stays nonblocking when standard is met
- **WHEN** Reviewer identifies an improvement that would be better but does
  not prove any current user/PM standard, acceptance criterion, evidence
  requirement, role boundary, or protocol rule is unmet
- **THEN** Reviewer SHALL record it as PM decision support using existing
  suggestion fields instead of inventing a new hard gate.
