## ADDED Requirements

### Requirement: PM repair obligation lifecycle aligns model, code, and tests
FlowPilot SHALL bind PM repair evidence obligation lifecycle requirements to
FlowGuard model obligations, owner code contracts, and current tests before
claiming the repair class is covered.

#### Scenario: Field lifecycle projections feed alignment
- **WHEN** FieldLifecycleMesh adds the PM repair obligation source,
  disposition, and downstream-consumption fields
- **THEN** Model-Test Alignment MUST include corresponding obligations and
  owner code contracts for packet creation, PM result validation, and recheck
  consumption.

#### Scenario: Observed model miss gets same-class evidence
- **WHEN** the model miss is represented as reason-only or registry-only PM
  repair output after a semantic blocker
- **THEN** Model-Test Alignment MUST include both observed-regression evidence
  and same-class generated bad-case evidence for the owner runtime contract.

#### Scenario: Broad coverage waits for TestMesh evidence
- **WHEN** generated PM repair obligation cases are routed through broad
  Cartesian, synthetic, or background validation
- **THEN** TestMesh MUST own the required shard or child-suite evidence before
  a broad coverage claim may be made.

### Requirement: Sealed-body consumption aligns model, code, prompts, and tests
FlowPilot SHALL bind required sealed-body consumption requirements to
FlowGuard model obligations, owner code contracts, runtime prompt/card
guidance, and current tests before claiming the repair information-flow class is
covered.

#### Scenario: Authorized-read lifecycle feeds alignment
- **WHEN** FieldLifecycleMesh represents authorized result reads,
  required-before-submit reads, packet body opens, and open receipts
- **THEN** Model-Test Alignment MUST include owner code contracts for related
  blocker reads, handoff contract projection, authorized material delivery, and
  submit-time receipt rejection
- **AND** prompt/card tests MUST check that PM, repair worker, Reviewer, and
  FlowGuard operator guidance requires reading every delivered related body.

#### Scenario: Multi-body repair coverage is required
- **WHEN** tests or synthetic rows cover sealed-body repair/recheck behavior
- **THEN** at least one current regression MUST include multiple related bodies
  so a one-body-only implementation cannot satisfy the model.
