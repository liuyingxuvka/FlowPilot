## ADDED Requirements

### Requirement: Reviewer windows are complete for every active review flow
FlowPilot SHALL declare a stable review-window completeness row for every
runtime-issued Reviewer flow. Each row MUST identify the review flow, subject
family, subject lifecycle stage, required structured window paths, required
material classes, authorized-read obligations, forbidden future-stage demands,
and Reviewer-blocker PM repair/recheck return path.

#### Scenario: Runtime review flow has a completeness row
- **WHEN** Runtime issues a Reviewer packet for a current subject family and
  lifecycle stage
- **THEN** that family/stage/review-kind combination MUST resolve to exactly
  one `review_flow_id`
- **AND** the `review_flow_id` MUST have a completeness row.

#### Scenario: Reviewer packet emits complete structured window
- **WHEN** Runtime issues a Reviewer packet for a declared `review_flow_id`
- **THEN** the packet envelope MUST include `review_window`
- **AND** the packet body `current_handoff_contract` MUST include the same
  `review_window`
- **AND** the window MUST include every required path declared by the
  completeness row.

#### Scenario: Orphan Reviewer flow fails
- **WHEN** Runtime can issue a Reviewer packet whose subject family, lifecycle
  stage, or review kind is not declared in the completeness matrix
- **THEN** the completeness gate MUST fail
- **AND** the failure MUST identify the orphan flow.

### Requirement: Reviewer material scope is authorized and bounded
FlowPilot SHALL make every Reviewer material obligation visible through
structured packet metadata. Required material reads MUST be listed as
authorized result reads, and unavailable or forbidden material MUST not be
silently implied by prose.

#### Scenario: Required read is authorized before submit
- **WHEN** a completeness row declares a result material as required before
  Reviewer submit
- **THEN** the emitted Reviewer packet MUST include that result id in
  `authorized_result_reads`
- **AND** `review_window.required_authorized_result_read_ids_before_submit`
  MUST include the same result id.

#### Scenario: Missing required read blocks completeness
- **WHEN** a Reviewer packet omits an authorized read required by its
  completeness row
- **THEN** the completeness gate MUST fail
- **AND** the failure MUST name the missing result material class or id.

#### Scenario: Future-stage demand is forbidden
- **WHEN** a Reviewer flow is at a plan-stage subject
- **THEN** the structured window MUST forbid requiring Worker/result-stage or
  terminal replay artifacts unless the subject claims they already exist.

### Requirement: Reviewer blockers return through one PM repair path
FlowPilot SHALL keep Reviewer hard blockers on the single PM repair and
Reviewer recheck path. PM MUST NOT close a Reviewer-blocked gate using prose or
by bypassing Reviewer.

#### Scenario: Reviewer blocker requires PM repair work
- **WHEN** Reviewer returns a hard blocker for a declared review flow
- **THEN** PM MUST create or select executable repair work
- **AND** repaired evidence MUST return to the same review class for Reviewer
  recheck before the blocked gate can pass.

#### Scenario: PM prose bypass is rejected
- **WHEN** PM attempts to close a Reviewer hard blocker with text only and no
  repaired evidence/recheck
- **THEN** Runtime or the control-flow tests MUST reject the bypass
- **AND** the blocker MUST remain on the normal repair/recheck path or escalate
  only through the existing threshold path.
