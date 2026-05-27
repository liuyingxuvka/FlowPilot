# flowpilot-structure-debt-convergence Specification

## Purpose
TBD - created by archiving change finish-flowpilot-structure-debt. Update Purpose after archive.
## Requirements
### Requirement: Remaining StructureMesh Gaps Are Cleared By Evidence

The FlowPilot structure-maintenance workflow SHALL treat a remaining model-code-test StructureMesh gap as complete only when the corresponding parent entrypoint is below its diagnostic threshold and the split has current model, code, and external test evidence.

#### Scenario: Validation runner split preserves command behavior

- **GIVEN** an oversized `simulations/run_*checks.py` runner appears as a `validation_gate` StructureMesh gap
- **WHEN** the runner is split
- **THEN** the original runner file SHALL still define `main`
- **AND** it SHALL still have a `__main__` guard
- **AND** its command-line behavior and JSON output options SHALL remain covered by runner contract tests
- **AND** the regenerated full diagnostic SHALL no longer report `needs_structure_split` for that runner.

#### Scenario: Runtime contract split preserves public facade behavior

- **GIVEN** an oversized `skills/flowpilot/assets/*.py` runtime contract surface appears as a `runtime_contract` StructureMesh gap
- **WHEN** the module is split into child modules
- **THEN** the original module path SHALL continue to provide its public imports or exported data
- **AND** tests SHALL prove the child modules combine to the same externally visible contract where tables or manifests are split
- **AND** new child modules SHALL have model/test/code diagnostic evidence rather than becoming `missing_test` or `internal_only_test` gaps.

#### Scenario: Peer work is preserved

- **GIVEN** unrelated peer-agent changes are present in the working tree
- **WHEN** the structure-debt batch is committed
- **THEN** only files owned by this change SHALL be staged
- **AND** peer dirty files SHALL remain unstaged unless they are explicitly adopted into this change with validation evidence.
