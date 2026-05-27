## ADDED Requirements

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
