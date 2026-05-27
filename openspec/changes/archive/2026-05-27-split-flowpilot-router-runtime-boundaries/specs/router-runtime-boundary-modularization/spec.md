## ADDED Requirements

### Requirement: Router facade remains the public entrypoint

FlowPilot SHALL preserve `skills/flowpilot/assets/flowpilot_router.py` as the
public CLI and import facade while runtime responsibilities are moved into
narrower helper modules.

#### Scenario: Existing CLI commands still parse

- **WHEN** `flowpilot_router.py` is invoked with an existing supported CLI
  command
- **THEN** the command parses through the router facade
- **AND** the command dispatches to the same public behavior as before the
  extraction.

#### Scenario: Existing imports remain compatible

- **WHEN** repository tests or install checks import `flowpilot_router`
- **THEN** existing public constants, exceptions, and entrypoint functions remain
  available from the facade
- **AND** helper-module extraction does not require callers to import private
  modules directly.

### Requirement: Boundary extraction is behavior preserving

FlowPilot SHALL split router internals only when the target boundary can be
verified as behavior-preserving for the current runtime schemas and artifact
formats.

#### Scenario: Runtime artifact schema remains stable

- **WHEN** constants, paths, JSON helpers, Controller ledger helpers, card ACK
  settlement, packet orchestration, startup, daemon, gate, or terminal helpers
  move into a new module
- **THEN** existing `.flowpilot` runtime JSON schema names and required fields
  remain unchanged
- **AND** existing install and runtime checks do not require migration of
  current run files.

#### Scenario: Behavior change blocks the extraction

- **WHEN** an extraction requires changing CLI semantics, packet schemas,
  Controller/PM/Reviewer authority, ACK semantics, or terminal completion
  semantics
- **THEN** the extraction SHALL stop until a separate OpenSpec requirement
  captures the behavior change
- **AND** the behavior change SHALL NOT be hidden inside a refactor task.

### Requirement: ACK settlement and work completion stay separate

FlowPilot SHALL keep card ACK wait settlement separate from output-bearing work
completion during and after module extraction.

#### Scenario: ACK-only wait can clear

- **WHEN** a stale Controller wait row watches an ACK-only system card and valid
  ACK evidence already exists
- **THEN** the card-return settlement boundary may reconcile that ACK wait
- **AND** the target role is not kept busy only by the reconciled ACK wait.

#### Scenario: Output-bearing work remains busy after ACK

- **WHEN** a system card or work package requires a report, result, decision, or
  packet-spec output
- **THEN** ACK evidence alone SHALL NOT mark that output-bearing work complete
- **AND** the target role remains busy until the matching durable output event
  is recorded.

### Requirement: Controller wait boundaries remain visible and non-executable

FlowPilot SHALL preserve the distinction between executable Controller work and
passive wait status while Controller ledger helpers are extracted.

#### Scenario: Passive wait is not ordinary Controller work

- **WHEN** Router is waiting for a role decision, card return, or current-scope
  reconciliation and no executable Controller action is ready
- **THEN** the Controller action ledger active ordinary work count remains zero
- **AND** the wait remains visible through Router monitor/current status.

#### Scenario: Reconciled waits rebuild derived views

- **WHEN** an extracted helper reconciles a Controller wait row
- **THEN** the Controller action ledger and derived status views are rebuilt or
  refreshed before Router exposes the next dependent action.

### Requirement: Verification evidence gates completion

FlowPilot SHALL run focused checks for each extracted boundary and broad
FlowGuard/install checks before claiming the modularization complete.

#### Scenario: Focused checks validate each boundary

- **WHEN** a boundary extraction changes source files
- **THEN** matching focused unit tests and focused FlowGuard checks run before
  the task is marked complete
- **AND** skipped checks are recorded with reason and residual risk.

#### Scenario: Background regressions use complete artifacts

- **WHEN** heavy FlowGuard regressions run in the background
- **THEN** stdout, stderr, combined, exit, and meta artifacts are written under
  `tmp/flowguard_background/`
- **AND** completion is reported only after the exit and meta artifacts show a
  completed successful run or valid proof reuse.

#### Scenario: Installed skill matches repository source

- **WHEN** repository validation passes
- **THEN** the local installed FlowPilot skill is synchronized from the
  repository
- **AND** the install freshness audit passes before the change is considered
  complete.
