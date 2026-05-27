## ADDED Requirements

### Requirement: Large FlowGuard model splits preserve result meaning

Meta and Capability model phase extraction MUST preserve model state meaning,
hazard labels, invariant coverage, and pass/fail interpretation.

#### Scenario: Phase helpers preserve apply semantics

- **GIVEN** `meta_model.py` or `capability_model.py` splits its large `apply`
  function into startup, material, route, node execution, repair/mutation, and
  closure helpers
- **WHEN** the corresponding model check runs
- **THEN** the check MUST pass
- **AND** any result-count or fingerprint difference MUST be documented as a
  structure-only consequence or treated as a blocker.

### Requirement: Install checks split without output contract drift

`scripts/check_install.py` MUST call named check groups while preserving its
existing JSON shape and severity semantics.

#### Scenario: JSON output remains compatible

- **GIVEN** install checks are split into file presence, manifest, runtime card,
  JSON parse, retired-path, and optional local runtime groups
- **WHEN** `python scripts\check_install.py --json` runs
- **THEN** top-level `ok` and `checks` output MUST remain compatible with
  existing callers.

### Requirement: Final sync validates public and local boundaries

Before remote sync, the repository MUST validate local install freshness and
public-boundary privacy.

#### Scenario: Installed skill is source-fresh

- **GIVEN** source-owned FlowPilot skill files changed
- **WHEN** final validation runs
- **THEN** the local installed skill MUST be synchronized and audited as fresh.

#### Scenario: Public boundary is clean before push

- **GIVEN** docs, OpenSpec files, logs, or tooling changed
- **WHEN** public release/privacy preflight runs
- **THEN** tracked local paths, private state, and secret patterns MUST be
  absent before remote sync.
