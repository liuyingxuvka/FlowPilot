## ADDED Requirements

### Requirement: Protocol stress assets are synchronized locally
Repository maintenance SHALL complete protocol stress-testing additions with
version notes, installed-skill source freshness evidence, install check
evidence, and local git evidence before claiming the work complete.

#### Scenario: Protocol stress change completes
- **WHEN** protocol stress assets, simulations, tests, and result artifacts are
  added or changed
- **THEN** the repository-owned FlowPilot skill is synced into the local
  installed skill
- **AND** install audit and install check commands pass after the sync
- **AND** the local git commit contains only the intended OpenSpec, source,
  model/test, docs, evidence, and version updates for the stress change.

#### Scenario: Publication remains separate
- **WHEN** the protocol stress change is locally committed
- **THEN** the maintenance flow does not push, tag, publish, deploy, or create a
  release unless the user explicitly authorizes that separate action.
