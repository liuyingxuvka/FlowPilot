## ADDED Requirements

### Requirement: New-Only Cleanup Completes With Install And Git Sync
FlowPilot compatibility removal SHALL end with repository-owned installed skill
sync, install freshness audit, and a local git commit containing the intended
changes.

#### Scenario: Source validation completes
- **WHEN** source changes, model updates, prompt cleanup, and focused tests have
  completed
- **THEN** the repository-owned installed FlowPilot skill is synced
- **AND** install check and installed freshness audit pass or any failure is
  reported as a blocker

#### Scenario: Local git result is finalized
- **WHEN** validation and install sync are complete
- **THEN** the intended changes are committed locally
- **AND** no tag, push, release, deployment, or binary package is performed
  unless explicitly requested
