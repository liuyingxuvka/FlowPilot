## ADDED Requirements

### Requirement: Pre-release maintenance validates public boundary before remote sync
Repository maintenance SHALL run a public-boundary and privacy preflight before
pushing pre-release source changes to the remote FlowPilot repository.

#### Scenario: Privacy preflight blocks local-state leakage
- **WHEN** tracked files include private runtime state, local KB records, cache
  directories, local environment files, machine-specific paths, or secret-shaped
  content
- **THEN** remote source sync is blocked until the tracked public boundary is
  corrected or the finding is explicitly documented as a false positive.

#### Scenario: Remote sync is source-only
- **WHEN** pre-release maintenance pushes the branch to `origin`
- **THEN** it does not create tags, GitHub Releases, binary packages, deploys,
  or companion skill publication side effects.

### Requirement: Skipped release-heavy checks remain visible
Repository maintenance SHALL record user-skipped heavy checks as skipped, not
passed, when finalizing pre-release work.

#### Scenario: Meta and Capability regressions are excluded by user request
- **WHEN** the user asks to skip the heavyweight Meta and Capability model
  regressions
- **THEN** final validation evidence names both skipped model boundaries, the
  reason for skipping, and the residual confidence boundary.
