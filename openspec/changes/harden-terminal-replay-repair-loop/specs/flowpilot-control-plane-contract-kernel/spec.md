## ADDED Requirements

### Requirement: Terminal replay repair packets preserve replay context
FlowPilot SHALL preserve terminal backward replay target context when PM opens
a current-scope repair packet for a terminal replay blocker.

#### Scenario: Terminal current-scope repair packet includes segment targets
- **WHEN** terminal backward replay records a semantic blocker
- **AND** PM chooses `repair_current_scope`
- **THEN** the fresh repair packet body MUST include runtime-issued
  `segment_targets`
- **AND** the packet MUST remain in the current terminal replay result family
  with `packet_kind=review` and `route_scope=terminal_backward_replay`
- **AND** the packet body MUST include the terminal replay validation context
  needed by Reviewer to submit a current result.

### Requirement: Final-ready router honors current packets first
FlowPilot router next-action selection SHALL prefer current open packet work
over final closure attempts.

#### Scenario: Open terminal repair packet preempts close project
- **WHEN** the execution frontier is `ready_for_final_closure`
- **AND** a current terminal replay repair or reissue packet is open
- **THEN** `router_next_action` MUST return `dispatch_current_role` or a
  current packet recovery action
- **AND** it MUST NOT return `close_project`.
