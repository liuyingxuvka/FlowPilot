# pm-control-plane-exits Delta

## ADDED Requirements

### Requirement: PM control-plane blocker decisions can choose break-glass
FlowPilot SHALL expose `break_glass` as a legal PM decision whenever a current
PM decision contract already exposes a stop-for-user or stop-for-environment
exit for a blocker that cannot safely continue through normal repair.

#### Scenario: PM selects break-glass for a control-plane defect
- **GIVEN** a current PM decision packet exposes evidence that normal repair
  cannot form a legal next action because the FlowPilot control plane is
  missing material, contradicting its contracts, or has an invalid return path
- **WHEN** PM submits decision `break_glass`
- **THEN** FlowPilot records the PM decision
- **AND** FlowPilot MUST route foreground duty to `control_plane_blocker`
- **AND** FlowPilot MUST NOT wait for user resume.

#### Scenario: PM stop for user remains a user decision
- **GIVEN** PM submits decision `stop_for_user`
- **WHEN** the current blocker is otherwise validly stopped for user input
- **THEN** FlowPilot MUST keep the existing wait-for-resume behavior
- **AND** FlowPilot MUST NOT treat the stop as break-glass.

#### Scenario: Break-glass does not close authority gates
- **WHEN** PM submits decision `break_glass`
- **THEN** FlowPilot MUST NOT mark PM, Reviewer, FlowGuard Operator, system
  validation, route, node, or terminal gates passed
- **AND** FlowPilot MUST NOT waive the blocker
- **AND** FlowPilot MUST NOT mutate the route.

#### Scenario: Synonym decisions remain invalid
- **WHEN** PM submits a decision such as `glass_break`, `controller_repair`,
  `runtime_repair`, or `ask_user_about_runtime_bug`
- **THEN** FlowPilot MUST reject the result as an allowed-value violation.

### Requirement: PM-facing guidance distinguishes user stops from break-glass
FlowPilot PM cards and packet bodies SHALL define `stop_for_user` as a
substantive user-content or authority decision and `break_glass` as a
FlowPilot control-plane repair escalation.

#### Scenario: Prompt lists the exact machine token
- **WHEN** PM receives a repair or FlowGuard-acceptance packet with a
  non-repair stop exit
- **THEN** the packet/card guidance includes the exact token `break_glass`
- **AND** it explains that `break_glass` uses existing Controller break-glass
  repair rather than asking the user to diagnose FlowPilot internals.
