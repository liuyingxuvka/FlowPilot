# model-code-test-gap-burn-down Specification

## Purpose
TBD - created by archiving change burn-down-model-code-test-alignment-gaps. Update Purpose after archive.
## Requirements
### Requirement: Prioritized gap burn-down
The diagnostic repair workflow SHALL reduce high-priority model-code-test gaps
by release relevance and repair type, while preserving a truthful residual gap
report for work that remains unsafe or too broad to finish in the pass.

#### Scenario: High-priority gaps are targeted first
- **WHEN** the burn-down pass selects repair targets from the diagnostic
- **THEN** release-gate and validation-gate findings with external-contract or
  model-binding repairs are selected before low-risk extra-code findings

#### Scenario: Residual gaps remain visible
- **WHEN** a gap cannot be safely repaired in the current pass
- **THEN** the diagnostic keeps the gap with owner, repair type, severity,
  release relevance, and concrete next-action metadata

### Requirement: External contract evidence upgrade
The repository SHALL provide fast external-contract tests for selected
model-check runners, script entrypoints, test-tier commands, facades, and owner
modules so internal-only tests are not counted as full model-code-test coverage.

#### Scenario: Aggregate model-runner contract evidence
- **WHEN** model-check runner surfaces are validated by an aggregate test
- **THEN** the test verifies stable public behavior such as importability,
  callable entrypoints, JSON result shape, or safe dry-run/list behavior for
  each selected runner

#### Scenario: Internal-only evidence remains distinct
- **WHEN** a test exercises implementation details without asserting the public
  input/output contract of the modeled surface
- **THEN** the diagnostic reports internal-only evidence rather than full
  external-contract coverage

### Requirement: Model binding for intentional code surfaces
Intentional owner modules, compatibility facades, and public script entrypoints SHALL have explicit model binding or diagnostic classification so code is not left as unowned extra surface by default.

#### Scenario: Intentional code receives model binding
- **WHEN** a code surface is an intentional owner module, facade, or public
  entrypoint
- **THEN** the diagnostic maps it to a model obligation, source contract, or
  accepted compatibility classification

#### Scenario: Unowned code remains actionable
- **WHEN** a code surface has no clear model obligation or compatibility
  classification
- **THEN** the diagnostic reports it as extra code with the owner path and
  repair action to classify, bind, remove, or split it

### Requirement: Safe structure-split burn-down
The burn-down pass SHALL only split modules when the ownership boundary is
isolated and verifiable; otherwise it SHALL preserve a deferred split repair
item.

#### Scenario: Isolated split can be completed
- **WHEN** a module has an isolated responsibility that can be moved without
  public API or peer-agent collision risk
- **THEN** the code is split behind a facade and parity tests verify the public
  contract remains stable

#### Scenario: Broad split is deferred
- **WHEN** a structure split requires wide edits or overlaps active owner-module
  polish
- **THEN** the diagnostic reports a deferred structure-split repair rather than
  claiming the module is fully repaired

### Requirement: Evidence, install, and local git synchronization
The burn-down pass SHALL finish with regenerated diagnostic JSON, focused tests,
background artifact inspection, local FlowPilot install sync, FlowGuard adoption
evidence, KB postflight, and a local git commit that excludes unrelated peer or
timestamp-only changes.

#### Scenario: Final evidence is synchronized
- **WHEN** implementation for the pass is complete
- **THEN** diagnostic JSON, docs, tests, install checks, and FlowGuard adoption
  records are updated and validated

#### Scenario: Local git excludes unrelated changes
- **WHEN** unrelated peer-agent or timestamp-only files are present in the
  worktree
- **THEN** the local commit stages only files required for the burn-down pass
  and leaves unrelated changes unstaged
