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
