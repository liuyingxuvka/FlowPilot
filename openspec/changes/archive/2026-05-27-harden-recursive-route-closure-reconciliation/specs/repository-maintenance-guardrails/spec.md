## MODIFIED Requirements

### Requirement: Local install freshness is verified after maintenance

After maintenance source changes, the local installed FlowPilot skill SHALL be
synchronized from the repository and audited for source freshness.

#### Scenario: Installed skill matches repo-owned source

- **WHEN** repository-owned install sync completes
- **THEN** the freshness audit passes
- **AND** the final maintenance report includes the install sync and audit
  commands' pass/fail status.

#### Scenario: Recursive closure maintenance completes

- **WHEN** this recursive-route and closure-reconciliation maintenance pass is
  complete
- **THEN** the local installed skill has been refreshed from the repository
- **AND** the final evidence includes strict OpenSpec validation, focused
  FlowGuard checks, background Meta and Capability artifact inspection, install
  checks, and a local git commit.

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
