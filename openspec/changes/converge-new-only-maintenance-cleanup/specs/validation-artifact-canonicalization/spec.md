## ADDED Requirements

### Requirement: Current Result Artifact Is Canonical
FlowPilot validation evidence SHALL use the current canonical result artifact for
each model or check family when both a current `*_results.json` artifact and a
shadow `*_checks_results.json` artifact exist.

#### Scenario: Canonical result exists
- **WHEN** a model/check family has both `family_results.json` and
  `family_checks_results.json`
- **THEN** parent evidence, install checks, hierarchy inventory, and maintenance
  audits prefer `family_results.json` as the current proof artifact
- **AND** the shadow artifact SHALL NOT be used to carry newer or different
  runtime semantics.

#### Scenario: Only check-named result exists
- **WHEN** a check family has no current `*_results.json` artifact
- **THEN** FlowPilot may keep the check-named result as current evidence
- **AND** that file remains subject to ordinary freshness and stale-content checks.

### Requirement: Stale Shadow Artifacts Do Not Teach Compatibility
FlowPilot SHALL remove or quarantine shadow validation artifacts that present retired
aliases as active accepted paths when a current canonical artifact exists.

#### Scenario: Shadow artifact contains retired alias semantics
- **WHEN** a shadow result artifact says old inputs are accepted aliases or
  accepted caller paths
- **AND** a current canonical result artifact says the old input is retired or
  non-completing
- **THEN** the shadow artifact is not valid current evidence
- **AND** validation cleanup SHALL remove it or make it historical-only.

### Requirement: Artifact Audit Reports Canonical Drift
FlowPilot maintenance tooling SHALL report duplicate or shadow result artifacts so
future cleanup can distinguish exact duplicates from stale semantic drift.

#### Scenario: Duplicate result artifacts are scanned
- **WHEN** the validation-artifact audit scans result JSON files
- **THEN** it reports exact duplicate groups, runner duplicate pairs, and shadow
  pairs that have canonical replacements
- **AND** it remains safe to run before cleanup without mutating files unless an
  explicit cleanup mode is provided.
