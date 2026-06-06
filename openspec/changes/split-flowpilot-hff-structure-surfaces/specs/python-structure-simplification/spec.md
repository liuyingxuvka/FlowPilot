## MODIFIED Requirements

### Requirement: Preserve Baseline And Unsupported historical

The maintenance pass SHALL record a baseline before production-code edits and
SHALL preserve existing current public module names, CLI entrypoints, command
arguments, import paths, event names, and persisted JSON payload shapes for the
supported current contract only. Preserving a parent entrypoint SHALL NOT
permit legacy field aliases, obsolete command names, old packet/result shapes,
repo-root fallback, newest-run fallback, missing-field defaults, or automatic
translation from unsupported historical artifacts.

#### Scenario: Baseline before edits

- **WHEN** the simplification pass begins
- **THEN** the current local `main` commit and local backup location are
  recorded before changing source files.

#### Scenario: Current entrypoint remains without legacy acceptance

- **WHEN** a large module is split into helper modules
- **THEN** the original current module or CLI path remains importable or
  invokable for the supported current contract
- **AND** the split SHALL NOT introduce a compatibility branch, fallback parser,
  legacy alias, old JSON-field acceptance path, or missing-field default.

### Requirement: Sync Installed Skill And Local Git

The maintenance pass SHALL synchronize the repository-owned installed FlowPilot
skill and local git state after validation, without performing release
publication.

#### Scenario: Installed skill freshness

- **WHEN** source changes are validated
- **THEN** repository-owned install sync, install check, and installed
  freshness audit are run in order before final local git completion evidence.

#### Scenario: Peer edits are not absorbed silently

- **WHEN** local git state is finalized while peer-agent dirty files exist
- **THEN** the pass SHALL either stage only files owned by this change or report
  local git commit completion as blocked
- **AND** it SHALL NOT revert, overwrite, or silently stage unrelated peer
  changes.

#### Scenario: No release publication

- **WHEN** the pass completes
- **THEN** no tag, GitHub Release, deploy, binary package, or remote publication
  is performed unless explicitly requested separately.
