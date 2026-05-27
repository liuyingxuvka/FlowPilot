## ADDED Requirements

### Requirement: PM owns FlowGuard test-obligation disposition

FlowPilot SHALL require PM to maintain a test obligation matrix that converts
FlowGuard model obligations and missing test kinds into explicit test,
validation-mesh, model-test-alignment, waiver, deferral, or blocker
dispositions.

#### Scenario: Node entry derives pre-worker test obligations

- **WHEN** PM writes a node acceptance plan for a worker-dispatchable node
- **THEN** the plan MUST include a `test_obligation_matrix.pre_worker` section
- **AND** each row MUST name the source obligation, required test kind, owner
  role, expected evidence, freshness rule, and current disposition.

#### Scenario: Officer reports become PM disposition inputs

- **WHEN** a Product or Process FlowGuard Officer returns a report with
  `model_obligations`, `ordinary_test_evidence`, or `missing_test_kinds`
- **THEN** PM MUST absorb those rows into the current test obligation matrix
- **AND** PM MUST choose a concrete disposition before the dependent gate can
  close.

#### Scenario: Worker results refresh post-worker obligations

- **WHEN** worker output changes code, tests, artifacts, or validation evidence
- **THEN** PM MUST update `test_obligation_matrix.post_worker` from changed
  paths, result evidence, skipped checks, failed checks, stale evidence, and
  newly discovered missing test kinds
- **AND** undispositioned rows MUST block PM node-completion approval.

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
