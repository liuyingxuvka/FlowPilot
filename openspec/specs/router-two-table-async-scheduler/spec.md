# router-two-table-async-scheduler Specification

## Purpose
TBD - created by archiving change router-two-table-async-scheduler. Update Purpose after archive.
## Requirements
### Requirement: Router and Controller use separate tables
FlowPilot SHALL keep Router planning metadata in a Router-owned scheduler table and Controller executable work in a Controller-facing action table.

#### Scenario: Controller table remains simple
- **WHEN** Router enqueues work for Controller
- **THEN** the Controller action table contains executable row metadata, status, target role, action path, receipt path, and Router row traceability without requiring Controller to resolve Router dependency graphs.

#### Scenario: Router table owns scheduling
- **WHEN** Router records the same work
- **THEN** the Router scheduler table contains the row id, dependency summary, barrier classification, scope, receipt state, and reconciliation state.

### Requirement: Router daemon queues independent work until a barrier
The Router daemon SHALL reconcile visible tables once per tick and enqueue additional independent Controller rows while no barrier is active.

#### Scenario: Startup work is queued without waiting for every receipt
- **WHEN** a startup Controller row is already pending and the next startup card delivery is independent of that row
- **THEN** Router records the pending row and may enqueue the card delivery row in the same daemon tick.

#### Scenario: Barrier stops enqueueing
- **WHEN** Router reaches user input, host automation, control blocker handling, non-startup ACK waiting, role-result waiting, or current-scope reconciliation waiting
- **THEN** Router stops enqueueing new Controller rows and exposes the barrier as the current wait.

### Requirement: Controller has a continuous standby row during live waits
When the Router daemon is live and no ordinary Controller action is ready, FlowPilot SHALL expose a Controller-facing `continuous_controller_standby` row and a matching standby payload so the foreground Controller has a formal in-progress duty instead of an empty plan.

#### Scenario: Standby row is present during role wait
- **WHEN** Router is waiting for a role ACK, report, result, or current-scope wait and no ordinary Controller row is pending
- **THEN** the Controller action table contains one stable waiting `continuous_controller_standby` row that names the watched wait target, the monitor/status sources, and the next release conditions.

#### Scenario: Codex plan sync is required by the standby row
- **WHEN** Controller reads the standby row
- **THEN** the row instructs Controller to sync the visible Codex plan from the Controller action ledger, mark completed rows in the plan and receipts, keep the standby item `in_progress`, and check for missed unfinished Controller rows before waiting again.

#### Scenario: Standby is not completed after one check
- **WHEN** Controller performs one monitor poll, sees `timeout_still_waiting`, or sees the target role is still alive and working
- **THEN** the standby row remains waiting and Controller stays attached until Router exposes a new Controller action, reminder or liveness-check due state, blocker/recovery state, terminal state, user input, daemon repair, or an explicit host stop.

#### Scenario: Standby follows monitor wait times
- **WHEN** the current wait is an ACK wait
- **THEN** Controller treats three minutes as the reminder/liveness-check point and ten minutes as the blocker escalation point.
- **WHEN** the current wait is a report/result wait
- **THEN** Controller treats ten minutes as the reminder plus fresh liveness-check cycle and does not invent a shorter abnormal timeout.

### Requirement: Router reconciles Controller receipts before advancing gates
Router SHALL treat Controller receipts as local completion evidence and SHALL apply required Router-visible postconditions before considering a scheduler row reconciled.

#### Scenario: Stateful receipt needs postcondition
- **WHEN** Controller marks a stateful row done but the required Router-visible postcondition is missing
- **THEN** Router either reclaims or writes valid durable evidence for that postcondition or records a recoverable control blocker instead of advancing the gate.

#### Scenario: Generic receipt can reconcile locally
- **WHEN** Controller marks a receipt-only row done and no Router-visible postcondition is required
- **THEN** Router marks the matching scheduler row reconciled without requiring additional startup-only evidence.

### Requirement: Startup uses current-scope pre-review reconciliation
Startup Reviewer fact review SHALL use the same current-scope pre-review reconciliation rule used by later route scopes.

#### Scenario: Reviewer startup fact card waits for startup scope cleanup
- **WHEN** startup-local Controller rows, startup prep card deliveries, startup prep ACKs, heartbeat/boundary/display/mechanical evidence, or local blockers remain unresolved
- **THEN** Router returns `await_current_scope_reconciliation` with `scope_kind` set to `startup` instead of delivering `reviewer.startup_fact_check`.

#### Scenario: Reviewer startup fact event waits for startup scope cleanup
- **WHEN** `reviewer_reports_startup_facts` arrives before startup scope cleanup is complete
- **THEN** Router blocks the event as recoverable current-scope reconciliation and does not mark startup facts reported.

### Requirement: PM startup activation keeps existing ACK semantics
FlowPilot SHALL NOT add a second all-startup ACK gate before PM startup activation.

#### Scenario: PM activation waits on same-role ACK
- **WHEN** PM reports an activation decision before ACKing `pm.startup_activation`
- **THEN** Router uses the existing pending-card-return blocker for that PM card and does not require a separate startup-wide join.

#### Scenario: PM activation proceeds after reviewer report and PM card ACK
- **WHEN** Reviewer startup facts are recorded and PM has ACKed `pm.startup_activation`
- **THEN** Router may accept the PM startup activation decision through the existing event path.
