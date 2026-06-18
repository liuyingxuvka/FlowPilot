## ADDED Requirements

### Requirement: Reviewer packets declare a structured review window
FlowPilot SHALL provide every formal Reviewer packet with a runtime-checkable
review window that identifies what stage and material scope the Reviewer is
authorized to judge.

#### Scenario: Existing structured fields express the review window
- **WHEN** `packet_kind`, `route_scope`, `gate_kind`, `reviewer_review_scope`, `subject_stage_evidence_matrix`, `authorized_result_reads`, or `current_handoff_contract` can express the review window
- **THEN** FlowPilot MUST use those structured fields as the review-window authority
- **AND** prose instructions MUST NOT be the only source of the review window.

#### Scenario: Minimal review_window is added only when needed
- **WHEN** no existing structured field can express the review window for a Reviewer packet
- **THEN** FlowPilot MAY add one runtime-checkable `review_window` metadata object
- **AND** the object MUST name the review kind, current stage, allowed material scope, forbidden future-stage demands, and required upstream material classes.

### Requirement: Reviewer material scope matches the review window
Reviewer packets SHALL deliver or authorize the upstream material needed for
the declared review window without authorizing unrelated sealed bodies.

#### Scenario: Planning review sees planning materials
- **WHEN** Reviewer is asked to review a planning or node-acceptance plan
- **THEN** the packet MUST expose the current plan contract, PM planning result, active acceptance items, and stage evidence matrix needed to judge plan quality
- **AND** Reviewer MUST NOT require final worker or terminal evidence solely because it is absent at planning stage.

#### Scenario: Terminal review sees terminal materials
- **WHEN** Reviewer is asked to perform terminal backward replay
- **THEN** the packet MUST expose the route-wide segment targets, final artifacts or their authorized refs, acceptance-item closure data, blocker/waiver context, and current terminal evidence needed for replay.

### Requirement: Reviewer hard blockers return through PM repair
Reviewer hard blockers SHALL enter the existing PM repair path and return to
Reviewer for recheck rather than being bypassed by PM judgement alone.

#### Scenario: Reviewer block creates repair work
- **WHEN** Reviewer returns a current-gate hard blocker with repair guidance
- **THEN** PM MUST create or select an executable repair path under the existing blocker repair policy
- **AND** the repaired result MUST return to Reviewer before the blocked gate can pass.
