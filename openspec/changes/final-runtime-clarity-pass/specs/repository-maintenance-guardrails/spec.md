## MODIFIED Requirements

### Requirement: FlowGuard evidence remains executable and explicit

Maintenance SHALL run relevant focused checks, StructureMesh/TestMesh checks, model-test alignment checks, and background FlowGuard model regressions before claiming completion.

#### Scenario: Background model result has complete log artifacts

- **WHEN** a background FlowGuard regression is reported complete
- **THEN** stdout, stderr, combined, exit, and meta artifacts exist under the
  configured background log root
- **AND** the exit artifact shows a successful exit code.

#### Scenario: Skipped heavy checks remain visible

- **WHEN** a heavy check is not run
- **THEN** the final report names the skipped boundary, reason, and residual
  risk
- **AND** the skipped check is not described as passed.

#### Scenario: Runtime StructureMesh evidence is current

- **WHEN** a maintenance pass splits runtime, router, prompt, packet, card, diagram, or model files
- **THEN** the final report includes current StructureMesh/TestMesh or equivalent focused FlowGuard evidence for the touched boundary
- **AND** known-bad missing-owner, stale-parity, and insufficient-evidence hazards are still rejected.

#### Scenario: Prompt asset movement is validated

- **WHEN** maintenance moves prompt-like text out of Python into runtime-kit prompt assets
- **THEN** prompt-store tests validate every moved asset path, content hash, and template variable declaration
- **AND** the installed local skill contains the same prompt assets as the repository source.
