## ADDED Requirements

### Requirement: Router IO structure splits are locally synchronized

Repository maintenance SHALL finish FlowGuard-backed Router IO structure splits
with focused validation, background evidence, installed-skill freshness, and
local git evidence.

#### Scenario: Router IO split completion is evidence backed

- **WHEN** a Router IO owner split modifies repo-owned FlowPilot skill source
  files
- **THEN** focused IO, daemon, terminal, and model-test validation runs
- **AND** router, Meta, and Capability background regressions produce complete
  stdout, stderr, combined, exit, and meta artifacts before completion is
  claimed.

#### Scenario: Router IO split is installed and committed locally

- **WHEN** Router IO split validation passes
- **THEN** the repo-owned FlowPilot skill is synced into the local installed
  skill location
- **AND** installed-skill freshness checks pass
- **AND** local git captures only the intended OpenSpec, source, model/test,
  docs, and evidence updates for the split.
