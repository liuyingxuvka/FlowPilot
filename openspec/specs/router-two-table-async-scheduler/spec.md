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

#### Scenario: Equivalent Controller work in flight
- **WHEN** Router is considering a Controller action whose action type, scope, and registered postcondition match an existing pending, running, waiting, done, or reconciled row
- **THEN** Router MUST classify that existing row before enqueueing
- **AND** Router MUST NOT enqueue another ordinary row for the same work unless the existing row is explicitly terminal-failed and eligible for bounded retry

#### Scenario: Reconciled stateful row with drift blocks duplicate enqueue
- **WHEN** the existing equivalent row is done/reconciled but its Router-owned stateful postcondition flag is false
- **THEN** Router MUST enter reconciliation/repair for that row
- **AND** Router MUST NOT enqueue a fresh ordinary row for the same action in the same scope

#### Scenario: Independent startup work still queues
- **WHEN** a different startup Controller row is pending but the next startup action has a different action type or postcondition and no dependency on the pending row
- **THEN** Router MAY enqueue the independent row according to the existing nonblocking startup rules

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

### Requirement: Startup uses current-scope mechanical reconciliation
Startup runtime mechanical audit SHALL use the same current-scope reconciliation rule used by later route scopes before PM receives startup intake release.

#### Scenario: Runtime startup mechanical audit waits for startup scope cleanup
- **WHEN** startup-local Controller rows, startup prep card deliveries, startup
  prep ACKs, background collaboration, manual-resume lifecycle guard, display/mechanical
  evidence, or local blockers remain unresolved
- **THEN** Router returns `await_current_scope_reconciliation` with `scope_kind` set to `startup` instead of delivering `reviewer.startup_fact_check`.

#### Scenario: PM startup intake release waits for startup scope cleanup
- **WHEN** PM startup intake release is requested before startup scope cleanup is complete
- **THEN** Router blocks the release as recoverable current-scope reconciliation and does not mark startup runtime release complete.

### Requirement: PM startup intake release keeps same-role ACK semantics
FlowPilot SHALL NOT add a second all-startup ACK gate before PM startup intake release.

#### Scenario: PM startup intake release waits on same-role ACK
- **WHEN** PM reports a startup intake release decision before ACKing `pm.startup_intake_release`
- **THEN** Router uses the existing pending-card-return blocker for that PM card and does not require a separate startup-wide join.

#### Scenario: PM startup intake release proceeds after runtime audit and PM card ACK
- **WHEN** startup runtime mechanical audit is recorded and PM has ACKed `pm.startup_intake_release`
- **THEN** Router may accept the PM startup intake release decision through the existing event path.

### Requirement: Async scheduler waits on proven in-flight relay work
FlowPilot SHALL treat packet relay/open/ACK/progress evidence as in-flight work and SHALL NOT issue a duplicate ordinary relay action while the same packet family and packet ids are already in progress.

#### Scenario: Worker has opened relayed packet
- **WHEN** packet relay evidence exists for a packet family
- **AND** at least one addressed worker has opened, ACKed, or recorded progress for the packet
- **AND** the worker result has not yet returned
- **THEN** Router MUST wait for result or blocker evidence
- **AND** Router MUST NOT issue the same packet relay command again

#### Scenario: Relay evidence exists before aggregate flag is folded
- **WHEN** Router-visible relay evidence proves packet dispatch
- **AND** the aggregate dispatch flag is stale false at scheduler entry
- **THEN** Router MUST run the registered evidence fold before next-action selection
- **AND** duplicate-dispatch checks MUST see the folded in-flight state

### Requirement: Async scheduler escalates only after bounded proof failure
FlowPilot SHALL reserve Controller retry and PM repair escalation for cases where the registered evidence fold cannot prove completion or in-flight work from Router-visible records.

#### Scenario: Controller receipt is done but all relay evidence is absent
- **WHEN** a relay Controller row reports `done`
- **AND** packet/result relay evidence is absent from the registered sources
- **THEN** Router MAY use the existing retry budget and PM repair path
- **AND** Router MUST NOT silently continue as if the relay had succeeded

### Requirement: Scheduler ledger has one live mutation lane
Router scheduler rows SHALL be mutated through one live Router-owned lane while
daemon mode is active.

#### Scenario: Receipt reconciliation wants scheduler update
- **WHEN** Controller receipt reconciliation identifies a scheduler row that can
  be marked done, blocked, superseded, or reconciled
- **THEN** it submits that fact to the Router-owned fold lane
- **AND** it SHALL NOT also rewrite the scheduler row through an independent
  foreground path.

#### Scenario: No live daemon owns the run
- **WHEN** no live daemon lock exists and foreground recovery is explicitly
  operating as the Router-owned recovery lane
- **THEN** the foreground path may perform the scheduler fold
- **AND** it records that recovery ownership in the reconciliation result.
