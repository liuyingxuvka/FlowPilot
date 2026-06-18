## ADDED Requirements

### Requirement: Reviewer packets require declared structured review windows
FlowPilot SHALL reject or block any runtime-issued Reviewer packet whose
`review_window` is missing, orphaned, mismatched with the subject family or
lifecycle stage, inconsistent between envelope and body handoff, or represented
only as prose.

#### Scenario: Orphan review flow is not issuable coverage
- **WHEN** runtime prepares a Reviewer packet for a subject family and lifecycle
  stage that has no declared review-window row
- **THEN** the packet MUST be classified as an orphan review flow and MUST NOT
  count as covered runtime behavior.

#### Scenario: Review window mismatch fails before broad coverage
- **WHEN** the packet envelope review window and the body
  `current_handoff_contract.review_window` disagree on flow id, subject family,
  lifecycle stage, required paths, authorized reads, or repair return rule
- **THEN** runtime tests MUST fail the review-window coverage gate and identify
  the mismatched structured path.

### Requirement: Reviewer repair remains on the normal PM repair and recheck path
FlowPilot SHALL keep Reviewer blockers on the existing normal path: Reviewer
blocks, PM creates or selects repair work, repaired evidence returns to
Reviewer, and repeated unrepaired same-family failures use the existing
break-glass threshold.

#### Scenario: PM cannot bypass Reviewer blocker
- **WHEN** a Reviewer blocker is present for the current review window
- **THEN** a PM disposition that bypasses the blocker without repair evidence
  and Reviewer recheck MUST be rejected or kept blocked.

#### Scenario: Corrected repair returns to Reviewer
- **WHEN** PM supplies current repair evidence for a Reviewer blocker
- **THEN** FlowPilot MUST return the repaired subject to the same review window
  class for recheck before counting the gate as passed.
