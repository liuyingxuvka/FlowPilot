# flowpilot-maintenance-ideal-state Specification

## Purpose
TBD - created by archiving change complete-flowpilot-maintenance-ideal-state. Update Purpose after archive.
## Requirements
### Requirement: Ideal Maintenance State Is Evidence Backed

FlowPilot SHALL treat an ideal maintenance-state claim as valid only when current evidence covers runtime owners, model/test/script maintenance pressure, peer-completed changes, install freshness, and local git synchronization.

#### Scenario: Maintenance map supports bug localization

- **GIVEN** FlowPilot has many runtime, model, test, and script files
- **WHEN** the ideal-state pass completes
- **THEN** a maintainer SHALL be able to identify owner modules, facades, script entries, test tiers, and large-file pressure from a current maintenance map
- **AND** the map SHALL reference current model-code-test diagnostic coverage.

#### Scenario: Peer completed changes are adopted only with evidence

- **GIVEN** completed peer-agent changes exist in the working tree
- **WHEN** they are included in the final local commit
- **THEN** their OpenSpec tasks SHALL be complete
- **AND** focused model/tests SHALL pass
- **AND** install freshness SHALL be rechecked after adoption.

#### Scenario: Further splitting is bounded by ownership

- **GIVEN** a large model, test, or script file remains
- **WHEN** the file is considered for splitting
- **THEN** the split SHALL preserve the old import path or command when public
- **AND** it SHALL have a clear owner boundary and focused validation
- **AND** purely line-count-driven splits MAY be deferred when they would weaken clarity or increase risk.

#### Scenario: Final state is locally synchronized

- **GIVEN** code, prompt, template, or validation artifacts changed
- **WHEN** the pass finishes
- **THEN** the installed FlowPilot skill SHALL be synced from the repository
- **AND** local install audit/check commands SHALL pass
- **AND** a local git commit SHALL capture the validated state without pushing to GitHub.
