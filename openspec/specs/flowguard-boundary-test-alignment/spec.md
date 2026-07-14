# flowguard-boundary-test-alignment Specification

## Purpose
TBD - created by archiving change add-flowguard-boundary-tests. Update Purpose after archive.
## Requirements
### Requirement: Boundary surfaces have source-audited test evidence

FlowPilot SHALL map each selected FlowGuard boundary-test gap to a model
obligation, code contract, and ordinary test evidence row before claiming the
gap is closed.

#### Scenario: Controller process aside boundary is covered

- **WHEN** the model-test alignment runner inspects `controller_process_aside`
- **THEN** it MUST find a model obligation, source code contract, and ordinary
  test evidence proving that Controller asides are metadata only and cannot
  satisfy waits, authorize progress, create Router events, or carry formal
  evidence.

#### Scenario: Material artifact map boundary is covered

- **WHEN** the model-test alignment runner inspects
  `flowpilot_material_artifact_map`
- **THEN** it MUST find a model obligation, source code contract, and ordinary
  test evidence proving that the material artifact map is index-only,
  excludes sealed packet/result body text, and exposes reviewable source
  metadata without changing authority.

### Requirement: Alignment evidence remains executable

FlowPilot SHALL keep the focused boundary tests and the FlowGuard model-test
alignment runner executable after the new evidence rows are added.

#### Scenario: Focused evidence passes

- **WHEN** the focused boundary tests and
  `run_flowpilot_model_test_alignment_checks.py` are run after the change
- **THEN** the focused tests MUST pass and the model-test alignment report MUST
  no longer report the selected boundary surfaces as missing ordinary
  source-audited coverage.

### Requirement: Complete-workstream obligations align model, source, and tests
FlowPilot SHALL map each complete-workstream lifecycle step, report-plan audit, PM integration duty, Reviewer challenge, and FlowGuard self-approval boundary to one primary FlowGuard obligation owner, one source contract, and current ordinary test evidence.

#### Scenario: Plan-report obligation lacks ordinary evidence
- **WHEN** Model-Test Alignment finds a complete-workstream obligation with only prompt text or generated model evidence
- **THEN** the alignment gate SHALL fail until an ordinary test exercises the current role/report/review path.

### Requirement: Material contraction aligns positive and negative evidence
FlowPilot SHALL map retained skill discovery, ordinary material work packets, optional material-map behavior, and every removed material-special surface to current source and test evidence.

#### Scenario: Removed material field remains positive
- **WHEN** `material_sources` or `material_sufficiency` remains in a successful current discovery skeleton, prompt contract, fake response, runtime fallback read, or positive model obligation
- **THEN** the alignment gate SHALL fail and classify the hit for deletion rather than compatibility support.

#### Scenario: Historical material label remains
- **WHEN** an old material name appears only in a forbidden/deleted-field registry, negative test, or clearly historical evidence label
- **THEN** alignment MAY retain the hit with that explicit disposition.

