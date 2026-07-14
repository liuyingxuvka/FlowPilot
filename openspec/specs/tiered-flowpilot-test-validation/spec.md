# tiered-flowpilot-test-validation Specification

## Purpose
TBD - created by archiving change tier-flowpilot-test-regressions. Update Purpose after archive.
## Requirements
### Requirement: Default test discovery is repository-test scoped

Default pytest configuration SHALL collect from the repository `tests/`
directory and SHALL exclude backup, temp, cache, git, FlowPilot, FlowGuard, and
local KB/control directories.

#### Scenario: Root pytest does not collect backup copies

- **GIVEN** the repository contains backup or temp directories with historical
  test files
- **WHEN** pytest is run without an explicit path
- **THEN** discovery is scoped to `tests/`
- **AND** backup/temp directories are not recursed.

### Requirement: Fast validation excludes long and release-only work

The fast tier SHALL include only focused model/tooling checks and small unit
tests. It SHALL NOT run release/public-boundary checks, release full
Meta/Capability regressions, or blocking coverage sweeps.

#### Scenario: Fast tier stays foreground-safe

- **GIVEN** a developer asks for the fast tier
- **WHEN** the tier runner plans commands
- **THEN** no command includes release full regressions
- **AND** no command invokes public release checks
- **AND** no command invokes the broad coverage sweep.

### Requirement: Parent test tiers own child suites explicitly

Parent tiers SHALL be composed from named child suites. A child suite SHALL
identify its command owner and SHALL not be counted green when import,
collection, execution, or evidence freshness failed.

#### Scenario: Router child suite failure blocks parent confidence

- **GIVEN** a router slice cannot import its helper module
- **WHEN** the parent router tier is evaluated
- **THEN** that child suite is not counted green
- **AND** the parent tier cannot report success from stale or hidden evidence.

### Requirement: Background regressions require completion artifacts

Background test or model regressions SHALL write stdout, stderr, combined
output, exit-code, and metadata artifacts. Progress output SHALL be liveness
evidence only, not completion evidence.

#### Scenario: Background progress is not reported as pass

- **GIVEN** a background regression has emitted progress lines
- **AND** the exit artifact is missing
- **WHEN** the result is reported
- **THEN** completion remains in progress or unknown
- **AND** pass/fail is not claimed.

### Requirement: Release obligations remain visible when deferred

Routine tiers SHALL keep release-only or release full regression obligations
visible whenever they defer those checks. A release claim SHALL require release
tier execution or valid background/proof evidence.

#### Scenario: Routine tier defers release gate honestly

- **GIVEN** routine validation has passed
- **AND** release/public-boundary checks have not run
- **WHEN** confidence is reported
- **THEN** routine confidence can be reported
- **AND** release confidence remains pending.

### Requirement: Workstream and resource-discovery tests participate in parent tiers
Focused tests for complete-workstream prompts, discovery field lifecycle, material special-path removal, canonical fake profiles, and Reviewer/PM semantics SHALL be registered under the smallest owning tier and its required release parents.

#### Scenario: Focused test passes but parent is stale
- **WHEN** a focused workstream test passes after source changes but the owning parent evidence predates those changes
- **THEN** parent confidence SHALL remain stale until rerun or valid proof reuse is established.

### Requirement: Background parents bind a frozen covered-source fingerprint
All, formal-submit-adversarial, release, repository final-confidence, Meta, and Capability background regressions SHALL record the covered-source fingerprint and final out/err/combined/exit/meta artifacts; a source change SHALL invalidate affected proof rather than silently preserving pass status.

#### Scenario: Source changes during background run
- **WHEN** a covered prompt, model, runtime, test, or tier file changes after the background run freezes its fingerprint
- **THEN** the run SHALL finish as stale/non-passing for final evidence
- **AND** the affected parent SHALL be rerun from the new freeze point.

### Requirement: Final confidence is an acyclic terminal consumer
Current all, formal-submit-adversarial, and release artifacts SHALL compile into the Acceptance TestMesh manifest before strict ContractExhaustion, Cartesian, Model-Test Alignment, Acceptance TestMesh, and ModelMesh consumers run. Repository final-confidence SHALL run only after those strict parents and SHALL NOT be embedded in release evidence or used to prove its own MTA input.

#### Scenario: Final confidence is placed inside release evidence
- **WHEN** release includes the final-confidence command, or TestMesh/MTA consumes a final-confidence result that itself invokes MTA
- **THEN** TestTiering SHALL reject the dependency graph as cyclic
- **AND** repository final-confidence SHALL remain a downstream terminal consumer
- **AND** formal terminal-return authority SHALL remain scoped to the active FlowPilot run's own final-preflight.

