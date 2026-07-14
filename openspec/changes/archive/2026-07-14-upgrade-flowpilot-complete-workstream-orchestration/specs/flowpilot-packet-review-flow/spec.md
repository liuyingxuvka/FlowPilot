## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Reviewer audits plan execution with the actual artifact
Reviewer SHALL inspect the role's returned `Workstream Plan and Completion` against the current artifact, evidence, delegated outputs, verification, and unresolved items rather than treating plan prose or mechanical conformance as proof.

#### Scenario: Plan is specific and fully evidenced
- **WHEN** every required step has current evidence, deviations are explained, delegated work is integrated, and the final claim matches the plan status
- **THEN** Reviewer MAY accept the plan-execution surface as part of the quality decision.

#### Scenario: Plan is ceremonial or incomplete
- **WHEN** the plan is generic, written after the fact without evidence, leaves a required step unresolved, or cites delegated work that was not integrated
- **THEN** Reviewer SHALL report a quality gap and SHALL block when the accepted outcome or proof boundary is not trustworthy.
