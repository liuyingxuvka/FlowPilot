# controller-action-queue Specification

## Purpose
TBD - created by archiving change separate-wait-status-from-controller-actions. Update Purpose after archive.
## Requirements
### Requirement: Controller Work Board Contains Executable Actions Only
FlowPilot SHALL write ordinary Controller action rows only for actions the Controller can execute, receipt, relay, display, or repair.

#### Scenario: Passive role wait is not an ordinary action row
- **WHEN** Router is waiting for a role decision and no executable Controller work is ready
- **THEN** the Controller action ledger does not contain an ordinary `await_role_decision` work row, and the wait target is visible through Router status or current status

#### Scenario: Passive card return wait is not an ordinary action row
- **WHEN** Router is waiting for a card or card bundle return event and no executable Controller work is ready
- **THEN** the Controller action ledger does not contain an ordinary `await_card_return_event` or `await_card_bundle_return_event` work row, and the wait target remains visible through monitor status

#### Scenario: Passive scope reconciliation wait is not an ordinary action row
- **WHEN** Router is waiting for current-scope reconciliation and no executable Controller work is ready
- **THEN** the Controller action ledger does not contain an ordinary `await_current_scope_reconciliation` work row, and the reconciliation blockers remain visible through Router status

### Requirement: Router Wait Status Must Not Hide Local Obligations
FlowPilot MUST complete, expose, or reconcile Router-owned local obligations before preserving a passive wait status.

#### Scenario: Startup obligations preempt passive reconciliation wait
- **WHEN** startup mechanical audit, startup display status, controller-boundary projection, or equivalent Router-owned local obligations are missing
- **THEN** Router consumes or exposes those obligations before preserving a passive wait status

#### Scenario: Cleared blockers remove passive wait
- **WHEN** all blockers for a passive wait are cleared
- **THEN** Router removes the passive pending wait and recomputes the next executable action or standby status

### Requirement: Standby Represents Empty-Board Waiting
FlowPilot SHALL use continuous standby and Router monitor status to keep Controller attached when the ordinary Controller work board is empty and the run is nonterminal.

#### Scenario: Empty board enters standby
- **WHEN** the run is nonterminal, Router has no executable Controller action, and the system is waiting for an external role, card return, user, background check, or reconciliation status
- **THEN** Controller is directed to standby/patrol rather than given a pure waiting action to complete

#### Scenario: Standby names the wait target
- **WHEN** Controller enters standby during a passive wait
- **THEN** standby/current status names the wait class, target role or event, allowed external events where applicable, and whether reminder, liveness, or blocker handling is due

### Requirement: Due Wait-Target Reminders Are Generic Executable Work
FlowPilot SHALL create a distinct executable Controller row when any current waiting role is due for a reminder or reminder-plus-liveness check.

#### Scenario: Role result reminder becomes executable work
- **WHEN** Router is waiting for any role to return a result and the report reminder interval is due
- **THEN** the Controller action ledger contains a `send_wait_target_reminder` row naming the target role, wait class, source wait identity, Router-authored reminder text, reminder text hash, and fresh liveness-probe requirement

#### Scenario: Card ACK reminder becomes executable work
- **WHEN** Router is waiting for any role to ACK a card or card bundle and the ACK reminder interval is due
- **THEN** the Controller action ledger contains a `send_wait_target_reminder` row naming the target role, expected return path, Router-authored reminder text, and receipt contract

#### Scenario: Reminder receipt updates wait metadata only
- **WHEN** Controller receipts a `send_wait_target_reminder` row with the matching reminder text hash and sealed body boundary confirmation
- **THEN** Router records `last_wait_reminder_at` on the active wait and, for ACK waits, marks the matching pending return as reminded without satisfying the original ACK or result-return wait

#### Scenario: New executable work wakes standby
- **WHEN** a new executable Controller action becomes ready while Controller is in standby
- **THEN** standby returns `controller_action_ready`, and Controller returns to top-to-bottom work-board processing

### Requirement: Pure Waits Do Not Count As Active Controller Work
FlowPilot MUST NOT count passive waits as active ordinary Controller work.

#### Scenario: Active work count excludes passive waits
- **WHEN** only passive waits are present in Router status
- **THEN** the Controller action ledger active ordinary work count is zero, and foreground non-exit is enforced by standby rather than by a waiting work row

#### Scenario: Historical waiting rows do not block new executable work
- **WHEN** a historical waiting row exists from an older run state and Router exposes new executable Controller work
- **THEN** the new executable work is visible and processable, and the historical wait does not remain the current blocking action
