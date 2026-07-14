# flowguard-test-obligation-ownership Specification

## Purpose
TBD - created by archiving change clarify-flowguard-test-obligation-ownership. Update Purpose after archive.
## Requirements
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

### Requirement: Missing test kinds route to the smallest sufficient owner

FlowPilot SHALL route every missing or stale test obligation to the smallest
sufficient owner and evidence path rather than leaving it as residual prose.

#### Scenario: Ordinary packet-scoped test work goes to workers

- **WHEN** the missing evidence can be added or rerun inside the current node's
  allowed reads, allowed writes, and acceptance slice
- **THEN** PM MUST route it through a worker current-node packet, repair packet,
  or PM role-work request with a test obligation coverage section
- **AND** the worker result MUST return test obligation coverage rows and
  current evidence.

#### Scenario: Broad validation routes to TestMesh

- **WHEN** the missing evidence is broad, slow, layered, stale, skipped,
  progress-only, release-only, or requires parent/child validation confidence
- **THEN** PM MUST classify the row as `testmesh_required` or block with reason
- **AND** completion MUST NOT describe the parent validation confidence as
  passed until child evidence status is visible.

#### Scenario: Obligation/test mismatch routes to Model-Test Alignment

- **WHEN** model obligations, public code contracts, and ordinary test evidence
  do not line up
- **THEN** PM MUST classify the row as `model_test_alignment_required` or block
  with reason
- **AND** completion MUST NOT claim the obligation is covered until alignment
  evidence is current.

### Requirement: Review and final closure reject undispositioned test gaps

FlowPilot SHALL block node completion, evidence quality approval, final ledger
approval, and terminal closure when test obligation rows are missing,
undispositioned, stale, skipped, failed, progress-only, or running without
complete background artifacts.

#### Scenario: Reviewer blocks incomplete PM package

- **WHEN** Reviewer reviews a PM-built node-completion package
- **THEN** Reviewer MUST inspect the cited test obligation matrix
- **AND** Reviewer MUST block if any current-row disposition is missing,
  unsupported, stale, or contradicted by worker/officer evidence.

#### Scenario: Final ledger preserves the same boundary

- **WHEN** PM builds the evidence quality package or final route-wide ledger
- **THEN** every active FlowGuard-backed gate MUST carry model obligation,
  ordinary test evidence, missing test kind, conformance boundary, residual
  blindspot, PM disposition, and background-artifact completion rows
- **AND** terminal closure MUST treat progress-only or skipped validation as a
  gap, not as passed evidence.

### Requirement: Formal FlowGuard remains independent at named boundaries
FlowPilot SHALL preserve independent formal FlowGuard review at product architecture, route creation or structural mutation, applicable post-result, model-miss, parent composition, and terminal coverage/closure boundaries.

#### Scenario: Role-local model exists
- **WHEN** the producing role used FlowGuard locally during its workstream
- **THEN** the local evidence SHALL support but SHALL NOT replace an applicable independent formal FlowGuard boundary or Reviewer decision.

