# flowpilot-packet-review-flow Specification

## Purpose
TBD - created by archiving change simplify-flowpilot-packet-review-flow. Update Purpose after archive.
## Requirements
### Requirement: PM-issued packet results return to PM before Reviewer gates
FlowPilot SHALL route results from PM-issued ordinary evidence/research, current-node, and PM role-work packets to the project manager for package-result disposition and whole-route integration before any Reviewer gate may inspect or pass the work.

#### Scenario: Substantive role result returns to PM for disposition
- **WHEN** a Worker, Reviewer consultant, FlowGuard Operator consultant, or other substantive role returns a result for a PM-issued packet whose expected recipient is `project_manager`
- **THEN** Router SHALL expose a Controller-visible result relay to PM disposition
- **AND** Router SHALL NOT expose the dependent Reviewer gate before PM records package-result disposition and integration fit.

#### Scenario: Raw role result cannot satisfy dependent gate
- **WHEN** a raw substantive role result exists without an absorbed PM package-result disposition
- **THEN** Reviewer gate evidence SHALL reject the result as premature
- **AND** PM SHALL NOT complete the node, evidence dependency, or research dependency from that raw result alone.

### Requirement: Absorbed PM disposition releases a formal Reviewer package
FlowPilot SHALL treat an absorbed PM package-result disposition as Reviewer release evidence only when it writes a reviewer-readable formal gate package with a path, hash, review scope, and raw-result boundary.

#### Scenario: Absorbed disposition releases package
- **WHEN** PM records package-result disposition `absorbed`
- **AND** the disposition includes `formal_gate_package_released: true`, `formal_gate_package_path`, `formal_gate_package_hash`, and `reviewer_review_scope`
- **THEN** Router and Reviewer gates SHALL treat that disposition as the PM release for Reviewer review.

#### Scenario: Absorbed disposition without package is insufficient
- **WHEN** PM records package-result disposition `absorbed` without a formal gate package path and hash
- **THEN** Reviewer review SHALL remain blocked
- **AND** PM SHALL NOT use the disposition as node, material, or research acceptance evidence.

### Requirement: Reviewer reviews formal packages, not dispatch requests
FlowPilot SHALL keep Reviewer review on PM-built formal gate packages and independent quality/source/fact checks, not pre-dispatch approval of PM-authored worker packets.

#### Scenario: New packet flow skips Reviewer dispatch approval
- **WHEN** PM issues a valid work packet for a Worker or Officer
- **AND** Router direct-dispatch validation and packet-ledger checks pass
- **THEN** Controller may relay the packet envelope to the assigned role without a Reviewer dispatch approval event.

#### Scenario: Reviewer quality gate remains required
- **WHEN** PM has released a formal gate package after absorbed disposition
- **THEN** Reviewer SHALL inspect the formal package and required direct evidence before pass or block
- **AND** PM SHALL NOT advance solely from Router mechanical proof.

### Requirement: Unsupported reviewer-dispatch flags cannot satisfy new flow gates
FlowPilot SHALL treat old reviewer-dispatch cards, events, or flags as unsupported
audit history only. They MUST NOT satisfy new PM disposition, formal package
release, or Reviewer package-review requirements.

#### Scenario: Unsupported flag is ignored for current acceptance
- **WHEN** a run contains `reviewer_dispatch_allowed`, `reviewer_dispatch_card_delivered`, or an equivalent old reviewer-dispatch flag
- **THEN** Router and PM package gates SHALL NOT count that flag as PM package-result disposition
- **AND** Reviewer gates SHALL still require a formal PM gate package for new-flow acceptance.

### Requirement: Reviewer audits plan execution with the actual artifact
Reviewer SHALL inspect the role's returned `Workstream Plan and Completion` against the current artifact, evidence, delegated outputs, verification, and unresolved items rather than treating plan prose or mechanical conformance as proof.

#### Scenario: Plan is specific and fully evidenced
- **WHEN** every required step has current evidence, deviations are explained, delegated work is integrated, and the final claim matches the plan status
- **THEN** Reviewer MAY accept the plan-execution surface as part of the quality decision.

#### Scenario: Plan is ceremonial or incomplete
- **WHEN** the plan is generic, written after the fact without evidence, leaves a required step unresolved, or cites delegated work that was not integrated
- **THEN** Reviewer SHALL report a quality gap and SHALL block when the accepted outcome or proof boundary is not trustworthy.

