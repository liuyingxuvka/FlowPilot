## ADDED Requirements

### Requirement: Terminal coverage maintenance leaves complete local evidence

Repository maintenance for terminal FlowGuard coverage SHALL finish with
OpenSpec validation, focused FlowGuard model evidence, fake-response/cartesian
runtime regression evidence, local installed-skill freshness, and local git
evidence before claiming completion.

#### Scenario: OpenSpec validation is missing

- **WHEN** terminal FlowGuard coverage maintenance claims implementation is
  complete
- **THEN** `openspec change validate enforce-terminal-flowguard-coverage` MUST
  pass or the final report MUST name the validation failure as a blocker.

#### Scenario: Installed skill is stale

- **WHEN** terminal FlowGuard coverage source changes are complete
- **THEN** the repository-owned install sync and local install freshness audit
  MUST pass before final completion is claimed.

#### Scenario: Local git evidence is missing

- **WHEN** terminal FlowGuard coverage maintenance finishes validation
- **THEN** the final report MUST include the local git branch, changed-file
  scope, and commit status, or state the concrete blocker preventing commit.

#### Scenario: Heavy model regression runs in background

- **WHEN** heavyweight Meta or Capability regression is started in the
  background
- **THEN** maintenance evidence MUST cite stdout, stderr, combined, exit, and
  meta artifacts, and MUST treat missing exit artifacts as incomplete rather
  than passed.

