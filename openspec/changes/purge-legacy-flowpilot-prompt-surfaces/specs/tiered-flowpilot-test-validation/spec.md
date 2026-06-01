## ADDED Requirements

### Requirement: Current prompt surfaces have forbidden-token validation

FlowPilot validation SHALL include a focused scan that fails when current
prompt, card, template, skill, or installed-skill surfaces expose old
FlowPilot prompt/control paths.

#### Scenario: Repository current surfaces reject old paths

- **WHEN** focused prompt/card validation runs against repository-owned current
  surfaces
- **THEN** it SHALL fail on old role-output commands, old Router daemon prompt
  authority, active-holder lease submission authority, old template control
  paths, and compatibility prompt wording.

#### Scenario: Installed skill rejects old paths

- **WHEN** install sync and install validation run
- **THEN** the installed `flowpilot` skill SHALL be scanned for the same
  forbidden current-surface prompt/control paths
- **AND** validation SHALL fail if stale installed prompt text remains.
