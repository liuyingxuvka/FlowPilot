## ADDED Requirements

### Requirement: Preserve Baseline And Compatibility
The maintenance pass SHALL record a rollback baseline before production-code
edits and SHALL preserve existing public module names, CLI entrypoints, command
arguments, import paths, event names, and persisted JSON payload shapes.

#### Scenario: Baseline before edits
- **WHEN** the simplification pass begins
- **THEN** the current local `main` commit and local backup location are recorded before changing source files

#### Scenario: Compatibility facade remains
- **WHEN** a large module is split into helper modules
- **THEN** the original module remains importable and delegates or re-exports the compatible public surface

### Requirement: Simplify One Boundary Per Slice
The maintenance pass SHALL change one structural boundary at a time and SHALL
run focused validation before moving to the next boundary.

#### Scenario: Packet runtime slice
- **WHEN** packet runtime logic is moved into helper modules
- **THEN** packet runtime tests, output-contract tests, and install checks pass before the slice is marked complete

#### Scenario: Router hotspot slice
- **WHEN** router event or action logic is moved into helper modules
- **THEN** focused router runtime tests for the touched domains pass before the slice is marked complete

### Requirement: Preserve Validation And Release Honesty
The maintenance pass SHALL run or explicitly defer the strongest practical
validation for each touched boundary and SHALL report release-grade regression
requirements separately from routine maintenance success.

#### Scenario: Model files touched
- **WHEN** Meta or Capability model files are changed
- **THEN** Meta and Capability checks are run or their background artifacts are inspected before final completion

#### Scenario: Release confidence downgraded
- **WHEN** a check exits successfully but reports release confidence requiring full regression
- **THEN** the final status reports that as a release gate rather than claiming publication readiness

### Requirement: Layer Meta And Capability Evidence
The maintenance pass SHALL keep Meta and Capability parent validation layered so
routine checks stay fast while release-grade full regressions remain explicit.

#### Scenario: Routine thin parent validation
- **WHEN** Meta or Capability parent checks are run without an explicit full-regression flag
- **THEN** the runner validates the thin-parent evidence contract rather than expanding the legacy full graph

#### Scenario: Ledger-owned parent partitions
- **WHEN** the model hierarchy inventory is built
- **THEN** parent partitions, child evidence ids, invariant families, and release obligations come from `flowpilot_parent_responsibility_ledger.json`

#### Scenario: Background full regression obligation
- **WHEN** a full Meta or Capability proof is stale or absent
- **THEN** routine confidence MAY remain current if the thin parent is valid, but release confidence SHALL expose the background/full-regression obligation

### Requirement: Sync Installed Skill And Local Git
The maintenance pass SHALL synchronize the repository-owned installed FlowPilot
skill and local git state after validation, without performing release
publication.

#### Scenario: Installed skill freshness
- **WHEN** source changes are validated
- **THEN** repository-owned install sync, install check, and installed freshness audit are run before final local commit

#### Scenario: No release publication
- **WHEN** the pass completes
- **THEN** no tag, GitHub Release, deploy, binary package, or remote publication is performed unless explicitly requested separately
