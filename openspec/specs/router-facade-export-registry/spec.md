# router-facade-export-registry Specification

## Purpose
TBD - created by archiving change collapse-router-export-manifest-shards. Update Purpose after archive.
## Requirements
### Requirement: Router facade export registry keeps current public exports
FlowPilot SHALL preserve the public router facade export contract while moving
export rows into a single canonical registry owner.

#### Scenario: Aggregate exports remain available
- **WHEN** `flowpilot_router_facade_exports.install_facade_exports()` installs
  exports into `flowpilot_router.py`
- **THEN** every previously exported public router name remains available from
  the facade
- **AND** no event name, ledger shape, CLI command, or runtime protocol field is
  changed.

#### Scenario: Canonical registry views remain importable
- **WHEN** existing callers import manifest shard functions such as
  `owner_exports_actions()`, `owner_exports_controller()`,
  `owner_exports_route()`, `owner_exports_startup()`, or
  `owner_exports_terminal_work()`
- **THEN** those functions remain importable
- **AND** they return domain views derived from the canonical registry.

### Requirement: Export contraction is FlowGuard evidence backed
FlowPilot SHALL treat the export-registry contraction as a StructureMesh-backed
maintenance change, not as an unmodeled cleanup.

#### Scenario: Structure and model-test evidence cover the registry
- **WHEN** maintenance validation runs for this change
- **THEN** the router facade split checks pass
- **AND** the model-test alignment source contracts cover the canonical registry
  and unsupported historical view functions.

#### Scenario: Unsafe contraction remains blocked
- **WHEN** validation finds a removed public export, missing unsupported historical view,
  stale parity, or missing model-test evidence
- **THEN** the maintenance pass is blocked
- **AND** local install sync and local git completion are not claimed.
