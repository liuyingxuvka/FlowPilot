# flowguard-test-obligation-ownership Delta

## ADDED Requirements

### Requirement: Node entry test obligations do not imply a pre-work FlowGuard gate
FlowPilot SHALL keep PM-owned node-entry test obligations in the node acceptance plan without requiring a separate pre-work FlowGuard packet for ordinary nodes.

#### Scenario: PM derives pre-worker obligations
- **WHEN** PM writes an ordinary node acceptance plan
- **THEN** the plan SHALL include `test_obligation_matrix.pre_worker`
- **AND** those rows SHALL become Worker, Reviewer, and PM disposition obligations without creating a `node_prework_flowguard` packet.

#### Scenario: Structural obligations still require FlowGuard
- **WHEN** the node acceptance decision changes the route or node topology
- **THEN** FlowGuard SHALL inspect the structural decision before Reviewer review
- **AND** PM SHALL absorb FlowGuard model obligations and missing-test kinds before sending the structural plan to Reviewer.
