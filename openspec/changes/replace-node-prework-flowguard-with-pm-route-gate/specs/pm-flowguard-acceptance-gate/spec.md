# pm-flowguard-acceptance-gate Specification

## ADDED Requirements

### Requirement: PM absorbs structural FlowGuard reports before Reviewer review
FlowPilot SHALL require a PM-authored FlowGuard acceptance result after a mandatory FlowGuard report for every staged structural PM decision.

#### Scenario: FlowGuard pass waits for PM absorption
- **WHEN** a staged route/node structural decision receives a passing FlowGuard report
- **THEN** Router SHALL issue a PM FlowGuard acceptance packet before any Reviewer packet
- **AND** Reviewer review SHALL remain unavailable until PM records `decision=accept` with concrete `flowguard_absorption`.

#### Scenario: FlowGuard block prevents route mutation
- **WHEN** FlowGuard blocks a staged route/node structural decision
- **THEN** Router SHALL NOT commit route mutation
- **AND** PM SHALL receive the blocker through the current repair path instead of treating the structural decision as accepted.

### Requirement: PM may rewrite a structural plan after FlowGuard
FlowPilot SHALL allow PM to replace a staged structural route plan after reading the FlowGuard report, but the replacement plan SHALL start a fresh mandatory FlowGuard cycle.

#### Scenario: PM rewrites after FlowGuard pass
- **WHEN** PM FlowGuard acceptance returns `decision=redesign_route` with a strict `route_plan`
- **THEN** Router SHALL stage a new route redesign decision
- **AND** the new staged decision SHALL require FlowGuard, PM absorption, Reviewer review, and system validation before commit.

#### Scenario: Optional FlowGuard decisions are rejected
- **WHEN** PM returns an uncertain or optional FlowGuard decision such as `maybe`, `needs_flowguard`, or `optional_flowguard`
- **THEN** Router SHALL reject the result under the current packet-result contract
- **AND** no Reviewer packet or route mutation SHALL be released from that result.

### Requirement: FlowGuard cannot mutate routes directly
FlowGuard Operator SHALL report pass/block findings and PM suggestions only; it SHALL NOT become the route mutation authority.

#### Scenario: FlowGuard suggests child nodes
- **WHEN** FlowGuard suggests splitting or replacing route nodes
- **THEN** PM must absorb that suggestion into a PM route plan before any mutation can be staged
- **AND** Router SHALL reject any FlowGuard result that attempts to commit route changes directly.
