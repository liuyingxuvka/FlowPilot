## MODIFIED Requirements

### Requirement: PM owns FlowGuard test-obligation disposition
FlowPilot SHALL require PM to disposition FlowGuard model obligations and missing test kinds through existing node acceptance, packet-scoped coverage, post-result evidence, TestMesh, Model-Test Alignment, waiver, deferral, or blocker paths. Ordinary leaves SHALL NOT require a universal second pre-worker FlowGuard model or a duplicate PM test matrix when current route/acceptance evidence already owns the risk.

#### Scenario: Node entry chooses the smallest sufficient evidence route
- **WHEN** PM writes a node acceptance plan for a worker-dispatchable node
- **THEN** PM SHALL identify the node's current risk, proof obligations, and existing FlowGuard evidence
- **AND** SHALL either bind applicable current obligations, issue a scoped FlowGuard work order, or record why no additional local model is required.

#### Scenario: FlowGuard reports become PM disposition inputs
- **WHEN** a formal or role-local FlowGuard report returns model obligations, ordinary test evidence, or missing test kinds that affect the accepted work
- **THEN** PM SHALL absorb applicable rows into the existing node/result/closure evidence path
- **AND** SHALL choose a concrete disposition before the dependent gate closes.

#### Scenario: Worker results refresh post-result obligations
- **WHEN** Worker output changes code, tests, artifacts, or validation evidence
- **THEN** PM SHALL account for changed paths, result evidence, skipped checks, failed checks, stale evidence, and newly discovered missing test kinds through the current post-result coverage path
- **AND** undispositioned applicable obligations SHALL block PM node-completion approval.

## ADDED Requirements

### Requirement: Formal FlowGuard remains independent at named boundaries
FlowPilot SHALL preserve independent formal FlowGuard review at product architecture, route creation or structural mutation, applicable post-result, model-miss, parent composition, and terminal coverage/closure boundaries.

#### Scenario: Role-local model exists
- **WHEN** the producing role used FlowGuard locally during its workstream
- **THEN** the local evidence SHALL support but SHALL NOT replace an applicable independent formal FlowGuard boundary or Reviewer decision.
