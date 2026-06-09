## ADDED Requirements

### Requirement: FlowGuard consistency has model-test-code binding
FlowPilot SHALL model FlowGuard evidence consistency as a behavior-bearing
obligation and bind it to owner runtime code contracts plus ordinary test
evidence before claiming packet-result or Reviewer-handoff coverage.

#### Scenario: Field projection covers hard evidence status
- **WHEN** FieldLifecycleMesh or the field contract model audits FlowGuard
  result fields
- **THEN** it MUST include the behavior-bearing projection from child hard
  evidence status and `contract_self_check` booleans to the top-level
  FlowGuard result outcome.

#### Scenario: Information-flow alignment covers consistency before Reviewer
- **WHEN** information-flow alignment audits the FlowGuard-to-Reviewer path
- **THEN** it MUST require hard evidence consistency before a matching
  FlowGuard report can be consumed as Reviewer input.

#### Scenario: Model-test alignment rejects missing consistency evidence
- **WHEN** model-test alignment audits packet result family coverage
- **THEN** it MUST report a gap unless the FlowGuard consistency obligation has
  an owner code contract and current ordinary tests for consistent pass,
  failed self-check, blocked child evidence, and old-shape rejection.

#### Scenario: Scoped green output cannot close live-run miss
- **WHEN** only field presence, old-shape rejection, or happy-path fake AI tests
  are current
- **THEN** model-test alignment MUST NOT claim the FlowGuard evidence
  consistency miss is closed.
