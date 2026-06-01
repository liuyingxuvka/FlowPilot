## ADDED Requirements

### Requirement: Prompt-surface cleanup is locally synchronized

Repository maintenance SHALL finish FlowPilot prompt-surface cleanup with
installed-skill freshness evidence and local git evidence.

#### Scenario: Installed skill is refreshed after prompt cleanup

- **WHEN** FlowPilot prompt, card, template, or skill source files change
- **THEN** the repo-owned FlowPilot install sync command SHALL run
- **AND** the installed-skill freshness audit SHALL pass before completion is
  claimed.

#### Scenario: Local git captures prompt cleanup only

- **WHEN** validation and install sync pass for prompt-surface cleanup
- **THEN** local git SHALL capture only the intended OpenSpec, source,
  validation, topology, install-sync, and evidence changes for this cleanup
- **AND** unrelated peer-agent work SHALL remain untouched.
