## ADDED Requirements

### Requirement: Runtime test boundaries are independently runnable

FlowPilot SHALL expose focused router runtime test entrypoints for the major
maintenance boundaries while preserving the existing router runtime facade
suite.

#### Scenario: Boundary suite selects existing runtime cases

- **WHEN** a focused router runtime boundary suite is run
- **THEN** it executes explicit existing runtime test methods for that boundary
- **AND** it does not duplicate the runtime fixture or test body logic.

#### Scenario: Facade suite remains available

- **WHEN** the original router runtime test module is run directly
- **THEN** its runtime test class remains importable and executable
- **AND** the focused suites do not require changing existing callers.

### Requirement: Helper extraction preserves stateful behavior ownership

FlowPilot SHALL extract router helper boundaries only when the extracted code is
pure, table-driven, or otherwise covered as behavior-preserving for the current
runtime flow.

#### Scenario: Pure helper can move

- **WHEN** a Controller, ACK/return, startup/daemon, dispatch gate, or terminal
  helper computes a classification, identity, table, command payload, or
  side-effect-free payload
- **THEN** the helper MAY move into a boundary module
- **AND** `flowpilot_router.py` SHALL keep compatibility imports for existing
  tests and scripts.

#### Scenario: Stateful finalizer stays in router without stronger contract

- **WHEN** a candidate extraction writes multiple runtime artifacts, rebuilds
  derived views, changes scheduler settlement, advances daemon lifecycle, or
  closes terminal state
- **THEN** the write-bearing finalizer SHALL remain in the router for this pass
- **AND** a future behavior-specific OpenSpec change SHALL be used before that
  finalizer owns a new module boundary.

### Requirement: ACK settlement remains distinct from output completion

FlowPilot SHALL keep ACK-only wait reconciliation separate from output-bearing
work completion during helper extraction.

#### Scenario: ACK-only wait helper identifies a clearable wait

- **WHEN** a helper checks a stale wait row for an ACK-only system card with
  matching durable ACK evidence
- **THEN** the helper may classify the wait as ACK-clearable
- **AND** the classification does not mark any output-bearing work complete.

#### Scenario: Output-bearing work is not cleared by ACK helper

- **WHEN** a pending card, packet, or work row requires a report, result,
  decision, or packet-spec output
- **THEN** ACK evidence alone SHALL NOT classify that work as complete
- **AND** the runtime remains responsible for waiting for matching durable
  output evidence.

### Requirement: Verification gates maintenance completion

FlowPilot SHALL complete the second maintenance pass only after focused
runtime checks, relevant FlowGuard checks, OpenSpec validation, install sync,
and local git state are completed or explicitly reported with residual risk.

#### Scenario: Focused verification passes before install sync

- **WHEN** source helper modules or focused tests change
- **THEN** matching focused runtime tests and applicable focused FlowGuard checks
  SHALL run before the installed local skill is synchronized
- **AND** failures SHALL be fixed or reported as blockers.

#### Scenario: Background FlowGuard completion evidence is inspected

- **WHEN** broad Meta or Capability FlowGuard regressions run in the background
- **THEN** stdout, stderr, combined, exit, and meta artifacts SHALL be inspected
  under `tmp/flowguard_background/`
- **AND** completion SHALL be claimed only for exit-zero runs or valid proof
  reuse recorded in the artifacts.

#### Scenario: Installed skill and local git are synchronized

- **WHEN** repository validation passes
- **THEN** the installed local FlowPilot skill SHALL be synchronized from the
  repository
- **AND** install freshness checks SHALL pass before the local maintenance
  commit is created.
