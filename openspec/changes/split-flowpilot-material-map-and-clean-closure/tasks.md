## 1. OpenSpec And Coordination

- [x] 1.1 Validate the new OpenSpec artifacts before implementation.
- [x] 1.2 Preserve peer-agent repair dossier and active-child-lineage files as external evidence unless this change explicitly owns a path.
- [x] 1.3 Record the FlowGuard routes used: DevelopmentProcessFlow, StructureMesh, TestMesh, and Model-Test Alignment.

## 2. Material Artifact-Map Structure Split

- [x] 2.1 Split packet/result envelope indexing from `flowpilot_material_artifact_map.py` into a focused child module.
- [x] 2.2 Split ordinary non-sealed work-material scanning from `flowpilot_material_artifact_map.py` into a focused child module.
- [x] 2.3 Keep `flowpilot_material_artifact_map.py` as the stable public facade and keep its public `__all__` names unchanged.
- [x] 2.4 Update model-test-code contracts/evidence so new child modules are owned by the material-map boundary.

## 3. Validation Mesh

- [x] 3.1 Run material-map py_compile, boundary tests, router material modeling tests, and material-map FlowGuard model checks.
- [x] 3.2 Run model-test alignment and require `alignment_ok`, `full_diagnostic_ok`, and `full_coverage_ok`.
- [x] 3.3 Run repair dossier historical replay tests and repair dossier TestMesh checks.
- [x] 3.4 Rebuild/check FlowGuard project topology after the split and result refresh.

## 4. Install, Git, And Closure

- [x] 4.1 Run source install self-check, then sync repo-owned FlowPilot skill to the installed local skill.
- [x] 4.2 Run local install sync audit, install check, and installed runtime self-check after sync.
- [x] 4.3 Run OpenSpec verification for this change and inspect the report.
- [x] 4.4 Stage and commit only owned closure files, preserving unrelated peer-agent work.
- [x] 4.5 Record FlowGuard adoption evidence and KB postflight observation.
