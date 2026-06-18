## ADDED Requirements

### Requirement: Review-window obligations are projected before response
FlowPilot SHALL project review-window completeness obligations into
runtime-checkable packet metadata before Reviewer submits a result.

#### Scenario: Packet contract exposes current review scope
- **WHEN** Runtime issues a Reviewer packet
- **THEN** the envelope and body handoff contract MUST expose the current
  subject, lifecycle stage, required current fields, allowed blocker classes,
  authorized read ids, required read ids, forbidden future-stage demands, and
  PM repair return rule.

#### Scenario: Window mismatch fails current-contract check
- **WHEN** the envelope `review_window` and body
  `current_handoff_contract.review_window` differ
- **THEN** the current-contract check MUST fail
- **AND** Runtime MUST not rely on the mismatched prose or stale body field.

### Requirement: Review-window feedback is precise and repairable
FlowPilot SHALL make review-window contract failures return precise, repairable
paths rather than hidden semantic rejections.

#### Scenario: Missing window field reports exact path
- **WHEN** a Reviewer packet or submitted result violates a required
  review-window field
- **THEN** Runtime or the focused test oracle MUST identify the exact missing
  or malformed field path
- **AND** the repair guidance MUST name the minimal structured field or material
  reference needed to continue.
