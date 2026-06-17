## ADDED Requirements

### Requirement: FlowGuard pass acceptance reads subject-bound evidence artifacts
FlowPilot SHALL reject a FlowGuard or review pass when referenced evidence
artifacts contradict the top-level pass claim.

#### Scenario: Missing code contract overrides passed true
- **WHEN** a FlowGuard result reports `passed: true`
- **AND** a referenced evidence artifact reports `missing_code_contract`
- **THEN** Runtime MUST treat the FlowGuard result as failed for the gate
- **AND** Runtime MUST preserve the missing contract finding as the blocking reason.

#### Scenario: Blocker findings override passed true
- **WHEN** a FlowGuard result reports `passed: true`
- **AND** a referenced evidence artifact contains blocker-level findings, missing required obligations, stale evidence, skipped required checks, or progress-only status
- **THEN** Runtime MUST reject the pass claim
- **AND** Runtime MUST NOT allow the gate to close from result shape alone.

### Requirement: Parent repair FlowGuard work orders are subject-bound
FlowPilot SHALL require FlowGuard work orders for parent-scope repair to name
the concrete artifacts that must be inspected before pass.

#### Scenario: Parent repair work order names required artifacts
- **WHEN** Runtime or PM asks FlowGuard to check a parent-scope repair
- **THEN** the work order MUST name the PM repair decision, parent repair contract, replacement route-node record, inherited child/result refs, active repair child ids, node acceptance plan, and parent backward replay inputs when present
- **AND** FlowGuard MUST report whether each subject artifact was consumed.

#### Scenario: Format-only FlowGuard report blocks
- **WHEN** a FlowGuard report checks only current-contract fields, result shape, source existence, or top-level `passed`
- **THEN** Reviewer or Runtime MUST treat the report as insufficient for a subject-bound parent repair gate
- **AND** the gate MUST remain blocked until FlowGuard consumes the required subject artifacts or records why the work order is unmodelable.
