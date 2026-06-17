# flowguard-boundary-test-alignment Spec Delta

## ADDED Requirements

### Requirement: Model-test alignment must cover FlowGuard artifact hard decisions

FlowGuard model-test alignment SHALL register obligations, code contracts, and tests for packet-owned FlowGuard artifact hard-decision gating.

#### Scenario: Artifact decision obligation has current evidence

- **GIVEN** the packet result family model includes FlowGuard evidence consistency obligations
- **WHEN** model-test alignment runs
- **THEN** it includes the artifact hard-decision obligation
- **AND** it includes negative, happy, and replay evidence for that obligation

### Requirement: Model-test alignment must cover blocker-bound semantic rechecks

FlowGuard model-test alignment SHALL register obligations and tests proving blocker identity continuity and subject-bound semantic recheck behavior.

#### Scenario: Shape-only recheck is modeled as invalid

- **GIVEN** a repair FlowGuard packet has a semantic recheck contract
- **WHEN** a result reports only shape/current-contract coverage
- **THEN** the model-test alignment evidence includes a negative test for rejecting that pass
