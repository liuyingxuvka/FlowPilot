# router-io-boundaries Specification

## Purpose
TBD - created by archiving change split-router-io-boundaries. Update Purpose after archive.
## Requirements
### Requirement: Router IO facade keeps compatible exports

FlowPilot SHALL preserve the existing `flowpilot_router_io` import surface while
moving implementation into focused child owner modules.

#### Scenario: Existing IO helpers remain callable

- **WHEN** callers import runtime IO helpers from `flowpilot_router_io`
- **THEN** path helpers, JSON read/write helpers, runtime JSON lock helpers,
  runtime-scan helpers, and role-output hash helpers remain available
- **AND** their existing argument and return behavior is preserved.

#### Scenario: Parent facade exposes child-owned symbols

- **WHEN** `flowpilot_router_io` is imported
- **THEN** its exported functions resolve to the corresponding child-owner
  implementations
- **AND** child modules do not require callers to change import paths.

### Requirement: Runtime JSON write-lock behavior is unchanged

FlowPilot SHALL keep runtime JSON write-lock liveness, takeover, wait, cleanup,
and corruption behavior unchanged after the split.

#### Scenario: Dead or stale owner takeover still records diagnostics

- **WHEN** a runtime JSON write target has a dead-owner or safe self-owned
  stale write lock
- **THEN** the lock is recoverable as before
- **AND** takeover diagnostics are written with the same schema and fields.

#### Scenario: Unsafe or active locks remain blocking

- **WHEN** a runtime JSON write target has an active live owner, active self
  owner, or unsafe stale self-owned temporary artifact
- **THEN** write attempts still raise `RouterLedgerWriteInProgress`
- **AND** the lock is not silently removed.

### Requirement: Router IO split is FlowGuard evidence backed

FlowPilot SHALL treat the Router IO split as a StructureMesh-governed refactor
with explicit parity evidence.

#### Scenario: Structure evidence covers IO child modules

- **WHEN** FlowGuard structure-maintenance and model-test alignment checks run
- **THEN** the IO facade and child modules are represented in the model catalogs
- **AND** over-threshold IO module findings are removed only when the actual
  source files are below the threshold and parity checks pass.

#### Scenario: Unsafe IO split remains blocked

- **WHEN** validation finds a missing unsupported historical export, changed lock
  behavior, changed JSON read/write behavior, or missing child contract evidence
- **THEN** the change is blocked
- **AND** the failed evidence is reported instead of being treated as a
  successful optimization.
