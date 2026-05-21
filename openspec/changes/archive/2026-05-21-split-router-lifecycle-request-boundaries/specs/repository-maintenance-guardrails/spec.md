## ADDED Requirements

### Requirement: Lifecycle request structure splits are locally synchronized
Repository maintenance SHALL finish FlowGuard-backed lifecycle request structure
splits with focused validation, background evidence, installed-skill freshness,
and local git evidence.

#### Scenario: Lifecycle request split completion is evidence backed
- **WHEN** a lifecycle request owner split modifies repo-owned FlowPilot skill
  source files
- **THEN** focused lifecycle, terminal, and control-blocker validation runs
- **AND** router, Meta, and Capability background regressions produce complete
  stdout, stderr, combined, exit, and meta artifacts before completion is
  claimed.

#### Scenario: Lifecycle request split is installed and committed locally
- **WHEN** lifecycle request split validation passes
- **THEN** the repo-owned FlowPilot skill is synced into the local installed
  skill location
- **AND** installed-skill freshness checks pass
- **AND** local git captures only the intended OpenSpec, source, model/test,
  docs, and evidence updates for the split.
