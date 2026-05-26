## ADDED Requirements

### Requirement: Shadow regression background evidence uses final artifacts
The system SHALL require final background `out`, `err`, `combined`, `exit`, and
`meta` artifacts before any shadow launcher, soak, Meta, Capability, or fast-tier
background run is counted as passed.

#### Scenario: Progress-only background output is not completion
- **WHEN** a background shadow regression has progress output but lacks final
  exit or meta evidence
- **THEN** the evidence is classified as incomplete and cannot satisfy the
  regression gate

#### Scenario: Final background artifacts prove completion
- **WHEN** the background artifact set has exit code `0`, meta status `passed`,
  current timestamps, and no proof reuse overclaim
- **THEN** the regression may count the background run as current pass evidence
