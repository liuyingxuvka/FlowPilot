## ADDED Requirements

### Requirement: Parent replay uses normal review packet flow
FlowPilot SHALL use the existing current review-packet flow to review accepted
parent backward replay task results. The replay task responsibility MAY be
`reviewer`, but that task execution SHALL NOT count as the independent review.

#### Scenario: Reviewer-owned replay task still needs review
- **WHEN** a `task.parent_backward_replay` packet was executed by the reviewer
  responsibility
- **AND** the replay result has not been accepted by a separate review packet
- **THEN** FlowPilot SHALL treat independent review as missing
- **AND** FlowPilot SHALL issue or dispatch a current review packet for the
  replay result

#### Scenario: Review packet carries authorized replay material
- **WHEN** FlowPilot issues a review packet for a parent replay result
- **THEN** the packet SHALL name the replay subject packet id, target result id,
  route node id, current route version, required authorized read for the replay
  result, and matching FlowGuard evidence when required

### Requirement: Late final-closure review repair remains current-routable
FlowPilot SHALL ensure a missing parent replay review discovered at final
closure maps to a current, routable Reviewer packet instead of a generic
`final_closure` repair pseudo-packet.

#### Scenario: Final closure finds a missing parent replay review
- **WHEN** final closure finds an accepted parent replay result without an
  accepted independent review
- **THEN** the runtime next action SHALL be to issue or dispatch a concrete
  Reviewer packet for the selected replay result
- **AND** the action SHALL include a real packet id and reviewer responsibility
  once issued
