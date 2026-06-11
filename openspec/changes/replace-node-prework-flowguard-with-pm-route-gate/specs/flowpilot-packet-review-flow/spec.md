# flowpilot-packet-review-flow Delta

## ADDED Requirements

### Requirement: Ordinary node acceptance plans release Reviewer without pre-work FlowGuard
FlowPilot SHALL not require a pre-worker FlowGuard packet for ordinary `task.node_acceptance_plan` results that keep the current route structure.

#### Scenario: Node plan pass goes to Reviewer
- **WHEN** PM submits `decision=pass` with a current top-level `node_context_package`
- **THEN** Router SHALL stage `commit_node_acceptance_plan`
- **AND** Router SHALL issue the Reviewer packet for the node acceptance plan without issuing `node_prework_flowguard`.

#### Scenario: Accepted leaf node plan opens worker packet
- **WHEN** Reviewer and system validation accept the ordinary node acceptance plan
- **AND** the node is a worker-dispatchable leaf
- **THEN** Router SHALL issue the node worker packet directly
- **AND** no `node_prework_flowguard` work order SHALL be required for worker release.

### Requirement: Structural node acceptance decisions use the PM FlowGuard acceptance gate
FlowPilot SHALL route any node acceptance result that changes route/node structure through mandatory FlowGuard, PM absorption, Reviewer, and system validation.

#### Scenario: PM splits active node
- **WHEN** PM submits `decision=redesign_route` from a node acceptance packet with strict `route_plan`
- **THEN** Router SHALL stage `commit_route_redesign`
- **AND** Router SHALL require FlowGuard pass, PM FlowGuard acceptance, Reviewer pass, and system validation before route mutation commits.
