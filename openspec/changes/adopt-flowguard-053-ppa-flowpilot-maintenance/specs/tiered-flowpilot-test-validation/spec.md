## ADDED Requirements

### Requirement: Release Claims Require Current Release Suites
FlowPilot SHALL require current release-scope evidence for release-only suites,
layered full proofs, install sync, historical replay, fake-agent chaos, and
live-host readiness before claiming release confidence.

#### Scenario: Routine evidence is green
- **WHEN** routine model, topology, install, or alignment evidence passes but release-only suites remain deferred
- **THEN** FlowPilot MAY claim routine maintenance confidence only
- **AND** it SHALL keep release confidence pending.

#### Scenario: Release evidence is requested
- **WHEN** a release, publish, archive, or broad local-version completion claim depends on release evidence
- **THEN** each required release suite SHALL have current final result and exit evidence, not progress-only or stale proof.

### Requirement: Background Evidence Has Final Artifacts
Background FlowGuard checks SHALL count as completion evidence only when their
stdout, stderr, combined log, exit artifact, metadata, result artifact, and
proof reuse status are inspected.

#### Scenario: Long check runs in background
- **WHEN** meta, capability, or release TestMesh checks run in the background
- **THEN** the completion report SHALL cite log root, exit code, final status, latest update time, and whether a valid proof was reused.
