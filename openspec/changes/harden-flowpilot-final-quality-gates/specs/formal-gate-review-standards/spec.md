## ADDED Requirements

### Requirement: Reviewer Evidence Counts Only When Accepted And Current
FlowPilot SHALL treat Reviewer evidence as final-gate proof only when the
review decision is accepted, the review is independent, the reviewed subject
belongs to the active route, the reviewed result is mechanically valid, the
review checked direct evidence, and the review has no blocker.

#### Scenario: Self-review cannot close final gate
- **WHEN** a review was produced by the same lease or agent as the reviewed
  result producer
- **THEN** the review MUST remain blocked as self-review
- **AND** final ledger, final matrix, and closure MUST NOT count it as
  independent review proof.

#### Scenario: Weak review cannot close final gate
- **WHEN** a review did not check direct evidence or carries a non-empty blocker
  list
- **THEN** the review MUST remain unresolved for final-gate purposes
- **AND** PM must obtain a current passing review or use the existing repair,
  reissue, route mutation, quarantine, or stop path.
