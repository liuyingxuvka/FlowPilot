## ADDED Requirements

### Requirement: Architecture reduction changes are synchronized locally
Repository maintenance SHALL complete FlowGuard architecture-reduction source
changes with local install freshness evidence and local git evidence before
claiming done.

#### Scenario: Local installed FlowPilot skill is refreshed
- **WHEN** a FlowPilot architecture-reduction maintenance change modifies
  repo-owned skill source files
- **THEN** the repo-owned FlowPilot install sync command runs
- **AND** the installed-skill freshness audit passes before completion is
  claimed.

#### Scenario: Local git captures only the intended change
- **WHEN** validation and install sync pass for a FlowPilot architecture
  reduction
- **THEN** the local git commit contains only the OpenSpec artifacts, source,
  model/test evidence, docs, and sync outputs for that change
- **AND** remote push, tag, deploy, and GitHub release publication remain out
  of scope unless separately authorized.
