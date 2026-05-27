## ADDED Requirements

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
