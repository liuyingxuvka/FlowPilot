## ADDED Requirements

### Requirement: Synthetic traces replay FlowGuard consistency through real APIs
Synthetic FlowPilot trace packs SHALL exercise FlowGuard evidence consistency
through real packet/result APIs instead of directly mutating work-order,
Reviewer, or route state.

#### Scenario: Contradictory FlowGuard trace uses packet runtime
- **WHEN** a synthetic trace submits a current-shaped contradictory FlowGuard
  result
- **THEN** it MUST submit through the same packet/result runtime path used by
  live roles
- **AND** the trace MUST prove the result is rejected before Reviewer dispatch.

#### Scenario: Directly seeded work-order pass is invalid evidence
- **WHEN** a synthetic trace marks a FlowGuard work order passed without an
  accepted current FlowGuard result that passed evidence consistency
- **THEN** trace replay review MUST reject that trace as invalid control-flow
  evidence.

#### Scenario: Fixture evidence stays non-live
- **WHEN** a historical or synthetic contradictory FlowGuard fixture is used
  for regression
- **THEN** FlowPilot MAY count it as control-flow regression evidence
- **AND** FlowPilot MUST NOT count it as live project completion evidence.
