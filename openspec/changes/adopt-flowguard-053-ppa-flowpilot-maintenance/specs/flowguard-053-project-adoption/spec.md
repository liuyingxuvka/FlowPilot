## ADDED Requirements

### Requirement: Project Record Matches Installed FlowGuard
FlowPilot SHALL update its managed FlowGuard project adoption record when the
installed FlowGuard check engine is newer than the project-recorded version
before claiming broad FlowGuard confidence.

#### Scenario: Installed engine is newer
- **WHEN** `python -m flowguard project-audit --root .` reports that the installed FlowGuard version is newer than `.flowguard/project.toml`
- **THEN** the maintenance change SHALL run the explicit project-upgrade path
- **AND** it SHALL record adoption evidence before broad completion or release confidence is claimed.

#### Scenario: Upgrade report is not validation proof
- **WHEN** project-upgrade updates adoption records or reports artifact upgrade findings
- **THEN** FlowPilot SHALL rerun affected model, test, topology, and install evidence instead of treating the upgrade report as a validation pass.

### Requirement: FlowGuard 0.53 Routes Are Available To Maintenance
FlowPilot maintenance SHALL verify that the active FlowGuard installation
exposes schema `1.0`, package version `0.53.0` or newer, and the route concepts
required by Behavior Commitment Ledger and Primary Path Authority before using
those routes for no-fallback evidence.

#### Scenario: Toolchain preflight runs
- **WHEN** the maintenance pass begins implementation
- **THEN** it SHALL record the FlowGuard schema version, package version, import path, and project audit result
- **AND** it SHALL keep any missing or stale route evidence visible as a blocker or scoped confidence.
