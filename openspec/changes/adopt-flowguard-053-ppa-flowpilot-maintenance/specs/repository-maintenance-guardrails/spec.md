## ADDED Requirements

### Requirement: Maintenance Completion Consumes Upgrade And PPA Evidence
Repository maintenance SHALL consume current FlowGuard project-upgrade,
Behavior Commitment Ledger, Primary Path Authority, field lifecycle,
model-test alignment, TestMesh, install sync, and local git evidence before
claiming this maintenance change complete.

#### Scenario: Completion is claimed
- **WHEN** this maintenance change is marked complete
- **THEN** the final evidence SHALL include project audit success, OpenSpec strict validation, BCL/PPA evidence, field lifecycle disposition, focused tests, model-test alignment, topology freshness, install sync/audit/check results, and a local git commit.

#### Scenario: Release-only evidence is not current
- **WHEN** release-required evidence remains deferred, stale, skipped, not run, or progress-only
- **THEN** the maintenance report SHALL keep release confidence scoped and SHALL NOT claim publication readiness.

### Requirement: Parallel Work Is Preserved
Repository maintenance SHALL preserve unrelated peer-agent changes and untracked
parallel work while staging and committing only the files owned by this change.

#### Scenario: Unrelated untracked directories exist
- **WHEN** git status shows untracked or unrelated peer-agent paths during this maintenance pass
- **THEN** the maintenance pass SHALL leave those paths unstaged and unreverted unless the user explicitly includes them.
