## ADDED Requirements

### Requirement: Parent replay closure requires independent review
FlowPilot SHALL treat an accepted `task.parent_backward_replay` result as raw
parent replay evidence only. A parent/module/top-level replay obligation SHALL
be considered fully closed only after a current independent
`review.any_current_subject` packet accepts the replay result under the
`parent_backward_replay_review` review window.

#### Scenario: Raw parent replay does not close the node
- **WHEN** a `task.parent_backward_replay` packet has an accepted result and
  matching FlowGuard evidence
- **AND** no accepted independent review packet exists for that replay result
- **THEN** FlowPilot SHALL keep the parent replay review obligation open
- **AND** FlowPilot SHALL NOT treat the parent/module/top-level node as fully
  closeable from raw replay alone

#### Scenario: Independent review closes replay evidence
- **WHEN** a `task.parent_backward_replay` packet has an accepted result
- **AND** a current independent `review.any_current_subject` packet accepts that
  exact result
- **THEN** FlowPilot SHALL treat the parent replay obligation as reviewed and
  eligible for the next PM or parent/topology progression gate

### Requirement: Parent replay repairs are dependency ordered
FlowPilot SHALL select missing parent replay reviews by effective route
topology, deepest child/module first and parent/top-level last. Diagnostic
closure output MAY list all missing reviews, but the current actionable repair
SHALL target only the deepest/earliest unresolved replay review.

#### Scenario: Child and top-level replay reviews are both missing
- **WHEN** an effective child/module parent replay and the top-level replay both
  have accepted raw replay results without independent reviews
- **THEN** FlowPilot SHALL expose only the child/module replay review as the
  current actionable Reviewer packet
- **AND** FlowPilot SHALL NOT expose the top-level replay review as actionable
  until the child/module review is accepted

#### Scenario: Repeated patrol does not duplicate review packets
- **WHEN** FlowPilot has already issued a current review packet for the selected
  missing parent replay result
- **AND** lifecycle patrol or final closure refresh runs again
- **THEN** FlowPilot SHALL reuse the existing current review packet
- **AND** FlowPilot SHALL NOT create a duplicate review packet for the same
  subject/result pair

### Requirement: No fallback for old parent replay state
FlowPilot SHALL NOT migrate, translate, or compatibility-promote old or
currently running parent replay state into the new reviewed replay contract.
Historical runs MAY be used as regression evidence only.

#### Scenario: Old replay state is not promoted
- **WHEN** a historical or old-contract run contains parent replay evidence that
  lacks the current review contract
- **THEN** FlowPilot SHALL NOT convert that state into current completion
  evidence
- **AND** the new runtime path SHALL require a fresh current-contract run or a
  separately designed explicit repair outside this change
