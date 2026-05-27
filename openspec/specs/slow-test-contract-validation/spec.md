# slow-test-contract-validation Specification

## Purpose
TBD - created by archiving change split-slow-route-mutation-test-contracts. Update Purpose after archive.
## Requirements
### Requirement: Slow test families are split by bound child contracts

Slow test families SHALL support parent contract tests that consume explicit
child input/output contracts instead of replaying the child workflow for every
parent assertion.

#### Scenario: Parent route-mutation test consumes child contract

- **GIVEN** the child contract provides active route, frontier, review block,
  model-miss triage, route-action-policy, and optional packet-ledger state
- **WHEN** the parent route-mutation test runs
- **THEN** it calls the real `pm_mutates_route_after_review_block` event
- **AND** it verifies only parent-owned route-mutation outputs.

### Requirement: Parent tests do not replay child setup

Parent contract tests SHALL fail if they call child-flow helpers such as
controller boot, pre-route gates, route checks, current-node card delivery, or
packet/result/review setup.

#### Scenario: Slow child helper is accidentally called

- **GIVEN** a parent contract test has already received a child contract
- **WHEN** it tries to call a child-flow helper
- **THEN** the test fails immediately
- **AND** the repeated child setup is not hidden inside the parent layer.

### Requirement: FlowGuard rejects unsafe slow-test contract evidence

FlowGuard TestMesh checks SHALL reject missing child owners, duplicate state
owners, unbound input or output contracts, stale child evidence, hidden child
skips, parent replay of child flow, and release claims without current child
oracle evidence.

#### Scenario: Parent confidence lacks child contract

- **GIVEN** a slow-test parent claims confidence
- **AND** the child input/output contract is missing or stale
- **WHEN** FlowGuard reviews the TestMesh contract
- **THEN** the parent confidence is rejected.
