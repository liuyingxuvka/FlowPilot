## ADDED Requirements

### Requirement: Next-step contracts project into FlowGuard step contracts
FlowPilot SHALL project externally visible `next_step_contract` records into
FlowGuard `WorkflowStepContract` evidence with stable step ids, prerequisite
receipts, produced receipts, invalidated receipts, required claims, and release
scope metadata.

#### Scenario: Controller receipt action becomes receipt-oriented step
- **WHEN** a Router action is projected into a Controller action row
- **AND** its `next_step_contract.controller_completion_command` is `controller-receipt`
- **THEN** the workflow-step contract MUST require the Router action receipt
- **AND** it MUST produce a Controller receipt completion receipt
- **AND** it MUST NOT require the normal pending-action apply path.

#### Scenario: ACK-only clearance stays separate from work completion
- **WHEN** a `next_step_contract` marks `ack_is_read_receipt_only`
- **AND** it marks `target_work_completion_evidence_required_separately`
- **THEN** the workflow-step contract MUST produce only ACK-settlement receipts
- **AND** it MUST require a separate work-output receipt before any work-complete claim.

### Requirement: Step-contract review blocks stale or skipped workflow claims
FlowPilot SHALL run FlowGuard step-contract traces that fail when a required
receipt is missing, a produced receipt is stale, a required step is skipped, or
a claim is emitted before the required workflow step completes.

#### Scenario: Missing prerequisite blocks claim
- **WHEN** a trace claims Controller row completion before the Router action
  receipt exists
- **THEN** the step-contract check MUST fail with a missing prerequisite or
  missing claim receipt finding.

#### Scenario: Stale receipt is not reused
- **WHEN** a trace invalidates an ACK receipt
- **AND** a later work-complete claim tries to rely on that stale ACK receipt
- **THEN** the step-contract check MUST fail rather than treating stale ACK
  evidence as current work output.

### Requirement: Workflow-step evidence participates in final confidence
FlowPilot SHALL include workflow-step contract checks in the model-test
alignment and full diagnostic evidence path before the final confidence gate
can pass.

#### Scenario: Final confidence consumes workflow-step evidence
- **WHEN** the final confidence gate runs
- **THEN** model-test alignment MUST include workflow-step contract obligations
- **AND** the full diagnostic MUST include the step-contract runner and tests
  as current evidence.
