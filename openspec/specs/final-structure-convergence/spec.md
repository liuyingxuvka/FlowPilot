# final-structure-convergence Specification

## Purpose
TBD - created by archiving change final-flowpilot-structure-convergence. Update Purpose after archive.
## Requirements
### Requirement: Compatibility-Preserving Final Structure

FlowPilot SHALL complete remaining Python structure convergence through
compatibility-preserving module splits.

#### Scenario: Public entrypoints stay stable

- **GIVEN** a caller imports or runs an existing FlowPilot router, packet,
  role-output, model, or script entrypoint
- **WHEN** implementation bodies are moved into helper modules
- **THEN** the existing import or command SHALL still work
- **AND** event names, persisted JSON shapes, output keys, and protocol
  semantics SHALL remain stable unless a documented bug fix requires a scoped
  behavior repair.

### Requirement: Router Runtime Tests Are Domain-Owned

Router runtime test implementations SHALL move from the aggregate runtime test
source into domain-owned modules without losing coverage.

#### Scenario: Domain test migration is complete

- **GIVEN** the aggregate router runtime test inventory
- **WHEN** domain modules are generated or maintained
- **THEN** every aggregate test SHALL be present in exactly one domain
- **AND** no domain SHALL include unknown or duplicate test names
- **AND** the aggregate compatibility entrypoint SHALL either load the domain
  suites or remain a thin compatibility layer until explicitly retired.

### Requirement: Child FlowGuard Models Remain Semantically Equivalent

Large child FlowGuard models SHALL be split only when the resulting modules keep
the model's accepted scenarios, rejected hazards, invariants, and result shape
equivalent for the supported check command.

#### Scenario: Model split preserves hazards

- **GIVEN** a child model is split into state, transition, hazard, invariant, or
  audit helper modules
- **WHEN** the focused model check is run
- **THEN** the check SHALL pass
- **AND** known bad hazards SHALL still be detected
- **AND** the result JSON SHALL remain valid for installer, hierarchy, and smoke
  checks.

### Requirement: Verification Matrix Is Current

The repository SHALL document the validation command set for each touched
structure boundary.

#### Scenario: Future agent selects validation

- **GIVEN** a future maintenance task touches router, test, runtime, model, or
  install-boundary files
- **WHEN** the agent consults the verification matrix
- **THEN** it SHALL identify focused tests, model checks, slow background checks,
  install sync, smoke, and public-boundary checks required for that boundary
- **AND** slow background checks SHALL require exit, stdout, stderr, combined,
  and metadata artifacts before completion is claimed.

### Requirement: Local Install And Git Sync Complete The Change

Final structure convergence SHALL end with local installed FlowPilot freshness,
clean local git state, and no extra local work branches.

#### Scenario: Final sync is complete

- **GIVEN** source changes under `skills/flowpilot` or repository-owned support
  scripts
- **WHEN** final validation completes
- **THEN** repository-owned install sync, install check, and installed freshness
  audit SHALL pass
- **AND** the local result SHALL be committed on `main`
- **AND** no tag, push, release, deployment, or binary package SHALL be
  performed unless explicitly requested.
