# flowguard-background-observability Specification

## Purpose
TBD - created by archiving change standardize-flowguard-background-logs. Update Purpose after archive.
## Requirements
### Requirement: FlowPilot declares a stable background log root
FlowPilot repository guidance SHALL declare `tmp/flowguard_background/` as the default evidence root for long-running FlowGuard project checks.

#### Scenario: Agent runs a long project check
- **WHEN** an agent runs a FlowPilot FlowGuard check in the background
- **THEN** the agent writes or reports artifacts under `tmp/flowguard_background/` unless a stricter task-specific path is explicitly declared

### Requirement: FlowPilot reports long-check evidence
FlowPilot repository guidance SHALL require final reports to cite stdout, stderr, combined output, exit status, metadata, timestamp, and proof-reuse status for long project checks.

#### Scenario: Agent summarizes verification
- **WHEN** an agent summarizes `run_meta_checks.py` or `run_capability_checks.py`
- **THEN** the summary includes the relevant log paths, exit code, last update time, and whether a valid proof was reused

### Requirement: Legacy project runners emit stderr progress
The `run_meta_checks.py` and `run_capability_checks.py` runners SHALL emit bounded progress to stderr while building reachable graphs, without changing stdout final reports.

#### Scenario: Full graph build runs
- **WHEN** a legacy runner builds its reachable graph
- **THEN** stderr contains start, progress, and complete messages while stdout retains the final report sections

### Requirement: Progress output is configurable
Legacy project runner progress SHALL be disabled when `FLOWGUARD_PROGRESS=0`.

#### Scenario: Strict environment disables progress
- **WHEN** `FLOWGUARD_PROGRESS=0` is set
- **THEN** the legacy runner suppresses progress messages while preserving check behavior

### Requirement: Historical replay evidence requires final current background artifacts
The system SHALL classify background proof artifacts by final exit and metadata
state before a historical live-run replay package can count as current primary
evidence.

#### Scenario: Stale or progress-only proof is rejected
- **WHEN** a replay package points to progress-only logs, stale run metadata,
  missing exit artifacts, or exit/meta mismatches
- **THEN** the package is rejected or classified as non-current evidence rather
  than a pass

### Requirement: Proof reuse is explicit in historical package evidence
The system SHALL expose proof reuse metadata for historical replay packages
whose evidence comes from prior artifacts.

#### Scenario: Reused proof stays scoped
- **WHEN** a replay package consumes a reused proof artifact
- **THEN** the artifact records proof reuse metadata and the package confidence
  boundary states whether the proof applies to the current run

### Requirement: Shadow regression background evidence uses final artifacts
The system SHALL require final background `out`, `err`, `combined`, `exit`, and
`meta` artifacts before any shadow launcher, soak, Meta, Capability, or fast-tier
background run is counted as passed.

#### Scenario: Progress-only background output is not completion
- **WHEN** a background shadow regression has progress output but lacks final
  exit or meta evidence
- **THEN** the evidence is classified as incomplete and cannot satisfy the
  regression gate

#### Scenario: Final background artifacts prove completion
- **WHEN** the background artifact set has exit code `0`, meta status `passed`,
  current timestamps, and no proof reuse overclaim
- **THEN** the regression may count the background run as current pass evidence

### Requirement: Known-friction validation rejects progress-only evidence
FlowPilot SHALL reject progress-only, path-only, skipped, timed-out, or
model-only background evidence when validating known-friction regression gates.

#### Scenario: Background check is still running
- **WHEN** a long model or daemon check has stdout/stderr progress but no final
  exit artifact and metadata completion status
- **THEN** FlowPilot MUST report the check as in progress and MUST NOT count it
  as passed.

#### Scenario: Background check timed out
- **WHEN** a background or daemon check times out before producing a successful
  final artifact set
- **THEN** FlowPilot MUST report the timeout as a validation gap for any
  affected known-friction gate.

#### Scenario: Proof reuse is claimed
- **WHEN** a long check reuses proof evidence
- **THEN** FlowPilot MUST report whether the proof was valid for the final
  source artifact versions before counting the result as passed.
