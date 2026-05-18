## ADDED Requirements

### Requirement: Terminal projections share one terminal fact
FlowPilot SHALL refresh current-run status, run index, router state, daemon
status, and daemon lock projection from the same terminal lifecycle fact after a
run stop.

#### Scenario: Stop projection is refreshed
- **WHEN** user stop or cancel is recorded for a run
- **THEN** `.flowpilot/current.json`, `.flowpilot/index.json`, the run router
  state, the daemon status, and the daemon lock projection MUST agree that the
  run is terminal or stopped
- **AND** visible next-step text MUST NOT describe creating heartbeat
  automation, starting roles, startup intake, or route work as the active next
  task.

#### Scenario: Historical ledger rows remain
- **WHEN** historical Controller ledger rows or retry rows remain after terminal
  projection refresh
- **THEN** they MAY remain as history
- **AND** they MUST be marked cancelled, superseded, terminal-only, or otherwise
  not active for nonterminal execution.
