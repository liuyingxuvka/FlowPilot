## ADDED Requirements

### Requirement: Review flows have fixed stage challenge bindings
FlowPilot SHALL bind every declared `review_flow_id` to one fixed Reviewer
stage card or fixed stage challenge focus before issuing a Reviewer review
window.

#### Scenario: Declared review flow has a binding
- **WHEN** the review-window completeness rows are enumerated
- **THEN** every declared `review_flow_id` SHALL have a deterministic stage
  challenge binding
- **AND** the binding SHALL be data-owned by the current runtime rather than
  selected by the AI recipient at review time.

#### Scenario: Existing result path is preserved
- **WHEN** a declared review flow uses `review.any_current_subject`
- **THEN** the review SHALL still submit through the existing review result
  family and existing result fields
- **AND** the stage binding SHALL NOT introduce a parallel review packet kind,
  fallback result family, or extra review result field.

### Requirement: Review packets project stage-specific challenge context
FlowPilot SHALL project stage-specific challenge context into the existing
`review_depth_rule` and Reviewer-facing packet guidance for each declared
review flow.

#### Scenario: Reviewer receives challenge focus
- **WHEN** runtime builds a review window for a declared flow
- **THEN** the review window SHALL tell Reviewer which current-stage object to
  challenge
- **AND** it SHALL require weakest-evidence analysis, a failure hypothesis or
  explicit no-hypothesis rationale, thin-success review, and PM-actionable
  decision support using existing fields.

#### Scenario: Future-stage demand remains forbidden
- **WHEN** the current review stage is plan or preplanning
- **THEN** the stage challenge context SHALL keep future worker, terminal, or
  post-result evidence demands forbidden unless the reviewed subject claims
  that evidence already exists.

### Requirement: Reviewer examples reject mechanical pass prose
FlowPilot SHALL ensure repository-owned Reviewer skeletons and examples do not
teach mechanical pass prose as a valid answer style.

#### Scenario: Minimal shape is a field checklist
- **WHEN** a Reviewer sees `minimal_valid_shape` or a result skeleton
- **THEN** the guidance SHALL identify it as a mechanical field checklist
- **AND** it SHALL warn that copying generic skeleton prose is low-quality
  review work.

#### Scenario: Sample suggestion is concrete
- **WHEN** repository-owned Reviewer examples include `pm_suggestion_items`
- **THEN** at least one sample SHALL name a concrete reviewed object, the
  weakest evidence or failure hypothesis, and a concrete PM action or
  no-action rationale.

### Requirement: PM FlowGuard absorption review has a stage challenge
FlowPilot SHALL provide a Reviewer stage challenge for PM absorption of
FlowGuard results before reviewed structural route effects advance.

#### Scenario: PM absorption package is challenged
- **WHEN** the review flow is `pm_flowguard_acceptance_review`
- **THEN** Reviewer guidance SHALL challenge whether PM absorbed the actual
  current FlowGuard report, residual risk, skipped/progress-only evidence, and
  structural decision scope
- **AND** Reviewer SHALL not treat PM prose alone as the reviewed evidence.
