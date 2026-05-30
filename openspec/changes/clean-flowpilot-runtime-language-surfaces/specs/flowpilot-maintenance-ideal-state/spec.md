## ADDED Requirements

### Requirement: Clean runtime-language migration is locally synchronized
FlowPilot maintenance completion SHALL include clean-language validation,
regenerated affected evidence, installed-skill synchronization, local install
audit, and local git synchronization when prompt, template, model, runtime, or
check surfaces change.

#### Scenario: Changed clean-language surfaces are validated before install sync
- **WHEN** current prompt, template, runtime, model, test, or install-check
  surfaces are changed to remove old topology or unsupported historical terminology
- **THEN** focused clean-language scans and owning model/test checks pass before
  the installed FlowPilot copy is synchronized

#### Scenario: Installed copy matches validated repository state
- **WHEN** validation passes and local install sync is run
- **THEN** the installed FlowPilot skill reports source-fresh status for the
  changed repository-owned files
- **AND** the local git commit captures only the validated current change set
  plus any intentional regenerated evidence
