## ADDED Requirements

### Requirement: Tiered validation consumes executable matrix child suites

Tiered FlowPilot validation SHALL register executable matrix bridge checks as
child suites when parent confidence depends on model-to-runtime coverage.

#### Scenario: Parent tier requires bridge child evidence

- **WHEN** a parent tier claims current-contract executable confidence
- **THEN** it MUST consume current child evidence for every required bridge case
  id in scope

#### Scenario: Stale bridge child blocks parent pass

- **WHEN** a bridge child suite result is stale, failed, timeout, skipped,
  running, or progress-only
- **THEN** the parent tier MUST NOT report broad pass for executable coverage

### Requirement: Routine and release bridge scopes remain visible

Tiered validation SHALL distinguish routine bridge rows from release-only full
rehearsal rows.

#### Scenario: Routine tier defers release bridge rows honestly

- **WHEN** routine validation passes without running release-only bridge rows
- **THEN** routine confidence MAY be reported
- **AND** release executable matrix confidence MUST remain pending
