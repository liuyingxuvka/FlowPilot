## ADDED Requirements

### Requirement: Current prompt surfaces expose only packet lifecycle authority

FlowPilot SHALL expose only current `flowpilot_new.py` packet lifecycle
commands in active role-facing prompt, card, skill, and template surfaces.

#### Scenario: Role output uses current packet result submission

- **WHEN** a current role-facing prompt instructs a formal role to acknowledge,
  open, or return work
- **THEN** the prompt SHALL use the current packet lifecycle commands
- **AND** the prompt SHALL NOT instruct the role to use old Router/runtime
  output submission commands.

#### Scenario: Old prompt authority is absent from active surfaces

- **WHEN** prompt-surface validation scans repository-owned current surfaces
- **THEN** old Router daemon, active-holder lease, old runtime-kit submission,
  old current-state template, and compatibility-alias prompt authority SHALL
  be absent.

### Requirement: Historical material is not current prompt authority

FlowPilot SHALL keep preserved backups and historical notes out of current
prompt authority.

#### Scenario: Preserved backups are excluded from active prompt validation

- **WHEN** forbidden-surface validation scans for current prompt authority
- **THEN** preserved backup directories SHALL be excluded from active-surface
  pass/fail decisions
- **AND** active skill, install, and template surfaces SHALL remain subject to
  the forbidden-surface scan.

### Requirement: Installed skill mirrors cleaned current surfaces

FlowPilot SHALL synchronize the local installed skill after current prompt
surface cleanup.

#### Scenario: Installed skill has no stale prompt remnants

- **WHEN** repository prompt cleanup and install sync finish
- **THEN** the installed `flowpilot` skill SHALL pass the same current-surface
  forbidden-token scan as the repository skill source.
