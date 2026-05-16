# controller-ledger-table-prompt Specification

## Purpose
TBD - created by archiving change harden-controller-ledger-table-prompt. Update Purpose after archive.
## Requirements
### Requirement: Controller action ledger includes a table-local prompt
FlowPilot SHALL emit an English `controller_table_prompt` at the top of each
generated `runtime/controller_action_ledger.json` before Controller action
rows. The prompt SHALL remind Controller that the ledger is its work board, that
it must work ready rows from top to bottom, that each completed row needs a
receipt before moving onward, and that Controller must not invent route items,
read sealed bodies, implement worker work, approve gates, or close the route
from Controller evidence.

#### Scenario: Ledger prompt precedes action rows
- **WHEN** Router rebuilds `runtime/controller_action_ledger.json`
- **THEN** the ledger contains `controller_table_prompt` before `actions`

#### Scenario: Row order and receipt duty are visible
- **WHEN** Controller reads the generated ledger
- **THEN** `controller_table_prompt.text` tells Controller to work from top to
  bottom, process every ready Controller row, write a receipt, and mark the row
  complete before moving to the next row

### Requirement: Foreground Controller remains attached while FlowPilot runs
The Controller ledger prompt and standby payload SHALL state that as long as
FlowPilot is still running, foreground Controller work remains attached. Quiet
tables, blockers, user waits, repair waits, role waits, diagnostic timeouts, or
the absence of ordinary ready rows MUST NOT be represented as permission for
Controller to stop or close the foreground Controller work.

#### Scenario: Running FlowPilot blocks foreground closure
- **WHEN** FlowPilot is still running and the action ledger has no ordinary
  ready Controller row
- **THEN** Controller is instructed to keep foreground Controller work attached
  instead of stopping or closing foreground work

#### Scenario: Waiting states do not release Controller
- **WHEN** the live run is blocked, waiting for a user, waiting for repair, or
  waiting for another role
- **THEN** the Controller prompt still states that foreground Controller work
  remains attached while FlowPilot is running

### Requirement: Continuous standby row is a watch duty that returns to row processing
FlowPilot SHALL expose the final fallback row
`continuous_controller_standby` as a continuous monitoring duty when all
ordinary Controller rows are complete and FlowPilot is still running. The row
SHALL remain `in_progress`, watch
`router_daemon_status` and `controller_action_ledger`, keep the visible Codex
plan synchronized from ledger rows and receipts, and return Controller to
top-to-bottom row processing when Router exposes new Controller work.

#### Scenario: Standby is not a finishable checklist item
- **WHEN** Controller reaches `continuous_controller_standby`
- **THEN** the standby row and payload state that it is a continuous monitoring
  duty, not a finishable checklist item, and the visible Codex plan status stays
  `in_progress`

#### Scenario: New Controller work wakes standby
- **WHEN** Router exposes new Controller work while `continuous_controller_standby`
  is active
- **THEN** Controller updates or rereads the action ledger and resumes
  top-to-bottom processing of ready Controller rows
