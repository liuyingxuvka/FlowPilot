## ADDED Requirements

### Requirement: Completed OpenSpec work remains preserved when archived

Repository maintenance SHALL move completed OpenSpec changes only into an
archive location that remains tracked and reviewable.

#### Scenario: Completed changes leave the active list

- **GIVEN** OpenSpec reports a change as complete
- **WHEN** maintenance archives completed changes
- **THEN** the change directory is moved under `openspec/changes/archive/`
- **AND** its proposal, design, specs, and tasks files remain present.

#### Scenario: Incomplete task-count changes stay visible

- **GIVEN** OpenSpec reports a change as in-progress or its task checklist has
  unchecked items
- **WHEN** maintenance archives completed changes
- **THEN** that change remains under `openspec/changes/`
- **AND** the final report names it as intentionally left active.

### Requirement: Maintenance cleanup is report-first and non-destructive

Repository maintenance tools SHALL default to read-only reporting before any
cleanup of validation artifacts or runtime state.

#### Scenario: Validation artifact duplicates are reported

- **WHEN** the validation artifact audit runs
- **THEN** it reports duplicate result files, canonical candidates, sizes, and
  paths
- **AND** it does not delete, move, or rewrite artifacts.

#### Scenario: Runtime retention report protects current run pointers

- **WHEN** the runtime retention report runs
- **THEN** it reports `.flowpilot` size, run counts, current pointer status, and
  stale candidates
- **AND** it does not remove the current run, index, or runtime directory.

### Requirement: Local install freshness is verified after maintenance

After maintenance source changes, the local installed FlowPilot skill SHALL be
synchronized from the repository and audited for source freshness.

#### Scenario: Installed skill matches repo-owned source

- **WHEN** repository-owned install sync completes
- **THEN** the freshness audit passes
- **AND** the final maintenance report includes the install sync and audit
  commands' pass/fail status.

### Requirement: FlowGuard evidence remains executable and explicit

Maintenance SHALL run relevant focused checks and background FlowGuard model
regressions before claiming completion.

#### Scenario: Background model result has complete log artifacts

- **WHEN** a background FlowGuard regression is reported complete
- **THEN** stdout, stderr, combined, exit, and meta artifacts exist under the
  configured background log root
- **AND** the exit artifact shows a successful exit code.

#### Scenario: Skipped heavy checks remain visible

- **WHEN** a heavy check is not run
- **THEN** the final report names the skipped boundary, reason, and residual
  risk
- **AND** the skipped check is not described as passed.
