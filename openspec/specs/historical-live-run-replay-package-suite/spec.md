# historical-live-run-replay-package-suite Specification

## Purpose
TBD - created by archiving change add-historical-live-run-replay-package-suite. Update Purpose after archive.
## Requirements
### Requirement: Historical replay packages cover named real-run failure families
The system SHALL provide a deterministic historical live-run replay package
matrix that enumerates each required real-run failure family, binds it to real
FlowPilot control surfaces, and states the expected standard state.

#### Scenario: Required package families are present
- **WHEN** the historical live-run replay package matrix is built
- **THEN** it includes packages for historical snapshots, host/role lifecycle,
  production replay adapter boundaries, relay/receipt mechanics, parallel
  stress, background proof edges, install split-brain, route mutation stale
  evidence, semantic contract failures, UI/display projection staleness, and
  Windows filesystem hazards

### Requirement: Historical packages disclose confidence boundaries
The system SHALL prevent historical replay rows from claiming live AI semantic
quality or destructive live-state coverage.

#### Scenario: Replay row cannot overclaim live AI quality
- **WHEN** a replay row declares evidence for a prepared fake AI package
- **THEN** the row marks live AI semantic quality as unproven, marks destructive
  live-state mutation as forbidden, and provides a confidence boundary

### Requirement: Known-bad historical packages fail the matrix gate
The system SHALL reject known-bad package rows that omit required replay
surfaces, stale current evidence, production replay adapter boundaries,
historical snapshots, relay mutations, or semantic-contract disclaimers.

#### Scenario: Known-bad package is rejected
- **WHEN** a known-bad row is validated by the matrix gate
- **THEN** the report contains the expected failure code and the package cannot
  be counted as current primary evidence

### Requirement: Runtime replay proves selected package rows through real control surfaces
The system SHALL exercise selected historical replay packages through real
Router, packet runtime, role-output runtime, resume, background artifact, and
install-check surfaces.

#### Scenario: Runtime replay blocks unsafe completion
- **WHEN** a fake AI package carries stale proof, partial host recovery,
  relay-only completion, install drift, stale projection, or filesystem residue
- **THEN** the runtime replay blocks completion, records a recognized
  recoverable state, or keeps the system waiting for the correct evidence
