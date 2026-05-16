# formal-daemon-startup Specification

## Purpose
TBD - created by archiving change enforce-flowpilot-daemon-startup. Update Purpose after archive.
## Requirements
### Requirement: Formal Startup Starts Router Daemon

Formal FlowPilot startup SHALL start the persistent Router daemon as an
internal startup step before Controller core is loaded.

#### Scenario: New formal invocation starts daemon

- **WHEN** the startup intake result has been validated and a run exists
- **THEN** startup starts the run-scoped Router daemon
- **AND** the daemon uses a one-second tick
- **AND** the daemon writes lock, status, and controller action ledger files
- **AND** Controller core is loaded only after the daemon startup step
  succeeds.

#### Scenario: Daemon startup fails

- **WHEN** the startup daemon process cannot be started or cannot prove live
  lock/status/ledger state within the startup timeout
- **THEN** formal startup fails with an explicit error
- **AND** startup does not continue in a non-daemon Controller loop.

#### Scenario: Same-run daemon already live

- **WHEN** formal startup observes a live same-run daemon lock
- **THEN** startup attaches to the existing daemon state
- **AND** startup does not start a second Router writer.

### Requirement: Daemon Is Not User Optional In Formal Runs

Formal FlowPilot startup SHALL NOT expose a user-facing option or startup flag
that disables the persistent Router daemon.

#### Scenario: Manual commands remain diagnostic

- **WHEN** an operator uses `daemon`, `next`, or `apply` directly
- **THEN** those commands are treated as diagnostics or repair tooling
- **AND** they do not define an alternate formal startup path without the
  persistent Router daemon.

### Requirement: Terminal Stop Still Owns Daemon Shutdown

FlowPilot SHALL stop or release the daemon during user-requested stop or
terminal lifecycle reconciliation.

#### Scenario: User stops the run

- **WHEN** the user requests FlowPilot stop
- **THEN** lifecycle reconciliation stops the daemon, releases or marks the
  daemon lock, and records terminal daemon status.
