## ADDED Requirements

### Requirement: Parent backward review uses review result fields
FlowPilot SHALL validate parent backward closure with review-owned result
fields: `reviewed_by_role`, `passed`, `findings`, `blockers`,
`pm_suggestion_items`, `parent_node_id`, `child_node_ids`,
`child_evidence_refs`, and `contract_self_check`.

#### Scenario: Passing review shape is accepted
- **WHEN** a `review.parent_backward_replay` result includes all required
  fields with `passed=true`
- **AND** the parent id, child ids, child evidence refs, blocker state, and
  self-check match the current packet and route node
- **THEN** FlowPilot SHALL accept the review result as current parent backward
  review evidence

#### Scenario: Inconsistent review shape is reissued
- **WHEN** a `review.parent_backward_replay` result omits a required field,
  cites the wrong parent, omits a required child, cites stale child evidence,
  has `passed=true` with blockers, or has `passed=false` without blockers
- **THEN** FlowPilot SHALL reject or reissue the same current parent backward
  review packet with actionable missing-field or blocker feedback
- **AND** FlowPilot SHALL NOT route to a second review packet
