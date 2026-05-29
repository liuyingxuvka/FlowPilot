# flowguard-runtime-path-alignment Specification

## ADDED Requirements

### Requirement: FlowPilot model-test families require runtime-path evidence

FlowPilot SHALL require FlowGuard runtime-path evidence for every major
model-test alignment family before the family can be reported green.

#### Scenario: Family plans include required runtime nodes

- **WHEN** the model-test alignment runner builds family plans
- **THEN** every family plan MUST set `require_runtime_path_evidence`
- **AND** every obligation in that plan MUST list at least one
  `required_runtime_node_id`
- **AND** each required runtime node MUST have a matching
  `RuntimeNodeContract`.

#### Scenario: Missing runtime-path evidence fails alignment

- **WHEN** a model-test alignment plan declares a required runtime node but has
  no current passing external observation for that node
- **THEN** FlowGuard MUST report the alignment as blocked with a runtime-path
  finding instead of accepting ordinary test evidence alone.

### Requirement: Runtime progress lines identify the compared FlowGuard model

FlowPilot SHALL expose runtime-path progress lines that are parseable by a
separate AI or test runner without local FlowGuard context.

#### Scenario: Progress lines name the model and node

- **WHEN** a runtime-path run is serialized or printed
- **THEN** each progress line MUST include the FlowGuard model id, model path,
  node id, run id, obligation id, input case, state case, evidence id, and
  result status.

#### Scenario: Progress lines preserve source evidence context

- **WHEN** a model-test family uses ordinary test evidence as the source for a
  runtime-path observation
- **THEN** the observation metadata MUST preserve the source test evidence id,
  command, path, and family so later maintenance can compare the real test/code
  path with the FlowGuard model node.

### Requirement: Runtime-path evidence remains diagnostic, not semantic replacement

FlowPilot SHALL keep runtime-path evidence as an additional diagnostic layer and
MUST NOT treat it as a replacement for ordinary tests, source-contract audits,
family parity checks, or parent/child FlowGuard checks.

#### Scenario: Existing validation gates still run

- **WHEN** runtime-path evidence is added to the model-test alignment runner
- **THEN** the existing model-test alignment, source audit, known-bad, full
  diagnostic, packet-result family parity, install, and smoke validation gates
  MUST remain runnable.
