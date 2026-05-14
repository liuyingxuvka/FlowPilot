## ADDED Requirements

### Requirement: Router-owned state writes do not require Controller receipts
The Router SHALL perform Router-owned display/status state writes directly and
SHALL NOT wait for a Controller receipt when the write can be completed inside
Router.

#### Scenario: Router writes display status files
- **WHEN** Router needs to refresh public display/status files that it can write
  itself
- **THEN** Router SHALL write the files and continue without creating a hard
  Controller postcondition wait

### Requirement: Controller display work is nonblocking
The Router SHALL treat Controller display and user-communication work as
nonblocking soft records unless that work is explicitly classified as
workflow-critical external action.

#### Scenario: Display sync is missing a compatibility flag
- **WHEN** `sync_display_plan` writes public display state but
  `visible_plan_synced` is missing or false
- **THEN** Router SHALL NOT escalate the display-only condition to PM repair and
  SHALL allow route progress to continue

### Requirement: External continuation actions use lightweight hard confirmation
The Router SHALL require lightweight hard confirmation for external actions
whose failure can stop autonomous continuation.

#### Scenario: Heartbeat binding must be confirmed
- **WHEN** a Controller or host action creates a continuation heartbeat binding
- **THEN** Router SHALL require the existing action receipt or marker before
  treating the keepalive action as complete

### Requirement: Role decisions keep file-backed evidence
The Router SHALL continue to require role-output decisions to carry a
file-backed body reference, body hash, and runtime receipt before the decision
can affect workflow state.

#### Scenario: PM repair decision lacks body reference
- **WHEN** PM submits a control-blocker repair decision through a status or
  progress surface without a file-backed body reference and hash
- **THEN** Router SHALL reject the event and SHALL NOT treat the status or
  progress packet as decision evidence

### Requirement: Evidence tiers are modeled
FlowGuard coverage SHALL distinguish Router-owned state writes, nonblocking
Controller display work, external continuation actions, and heavyweight
role-output decisions.

#### Scenario: Display action escalates despite being nonblocking
- **WHEN** a Controller display/status action is routed to PM repair solely
  because a display-only marker or compatibility flag is missing
- **THEN** the FlowGuard control-plane model SHALL classify the path as an
  invalid escalation
