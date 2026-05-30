# flowpilot-diagnostic-convergence Specification

## Purpose
TBD - created by archiving change complete-flowpilot-diagnostic-convergence. Update Purpose after archive.
## Requirements
### Requirement: Full Diagnostic Contract Convergence

FlowPilot SHALL maintain a full diagnostic layer that binds model obligations,
externally visible code contracts, ordinary tests, structure ownership, and
background evidence for all inventoried surfaces.

#### Scenario: Owner module has an externally visible contract

- **WHEN** an owner module appears in the full diagnostic inventory
- **AND** the module has externally visible inputs, outputs, writes, errors, or
  public import behavior
- **THEN** the diagnostic SHALL require ordinary test evidence for that
  external contract
- **AND** the evidence SHALL point at exact test ids
- **AND** source-contract rows SHALL point at concrete owner function
  definitions rather than import-only facades.

#### Scenario: Owner module is write-only or error-only

- **WHEN** an owner function exposes its behavior by writing files, updating
  state, queueing events, or raising a contract error
- **THEN** the code-contract row SHALL declare the observable side effect
- **AND** it SHALL avoid claiming a returned external output where none exists.

#### Scenario: Structure split is proposed

- **WHEN** an oversized runtime module, unsupported historical facade, script entrypoint,
  or model-check runner is split
- **THEN** StructureMesh evidence SHALL preserve public entrypoints, import
  names, event names, JSON schemas, command-line behavior, and config
  ownership
- **AND** ordinary external-contract or parity tests SHALL pass before the split
  is counted as release-ready.

#### Scenario: Background evidence is used for release confidence

- **WHEN** background validation is cited as evidence
- **THEN** final `.meta.json` and exit artifacts SHALL be inspected
- **AND** progress-only, stale, incomplete, failed, or local-only evidence SHALL
  not be counted as a pass.

#### Scenario: Diagnostic convergence is claimed

- **WHEN** this change is complete
- **THEN** `missing_test`, `internal_only_test`, `missing_model`, and
  `extra_code` SHALL be zero
- **AND** `source_audit_ok` SHALL be true
- **AND** all remaining structure gaps SHALL either be resolved or have an
  explicit StructureMesh deferral reason
- **AND** local install sync and local git synchronization SHALL be complete.
