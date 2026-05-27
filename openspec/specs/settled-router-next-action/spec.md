# settled-router-next-action Specification

## Purpose
TBD - created by archiving change settle-control-plane-before-next-action. Update Purpose after archive.
## Requirements
### Requirement: Router settles control-plane evidence before next action
Router SHALL reconcile durable Controller receipts, Controller action rows,
Router scheduler rows, startup bootloader postconditions, active control
blockers, and stale queued blocker-delivery rows before it returns a
Controller-visible next action.

#### Scenario: Reconciled startup action clears stale blocker before PM delivery
- **WHEN** a startup Controller action has an active control blocker but the same action's scheduler row and postcondition are later reconciled
- **THEN** Router resolves the blocker, supersedes any pending `handle_control_blocker` row for that blocker, and does not return PM repair work for that resolved blocker

#### Scenario: Settlement still returns only one action
- **WHEN** settlement updates one or more ledgers during a Router tick
- **THEN** Router persists the settlement changes and returns at most one next Controller-visible action

### Requirement: Same-origin blocker resolution is durable and auditable
Router SHALL resolve a control blocker only when the reconciled evidence matches
the blocker's originating Controller action id, scheduler row id, or startup
bootloader postcondition fallback.

#### Scenario: Exact identity resolves same-origin blocker
- **WHEN** a blocker records a Controller action id or scheduler row id and that same row reconciles
- **THEN** Router records `resolution_status` on the blocker artifact and moves it from active blockers to resolved blockers

#### Scenario: Startup fallback requires satisfied postcondition
- **WHEN** an older startup blocker lacks exact row identity but its originating action type matches a startup bootloader action
- **THEN** Router resolves it only if the corresponding startup postcondition is already satisfied

### Requirement: PM repair remains after settlement only for real unresolved blockers
Router SHALL queue or return PM repair work only after settlement proves that the
active blocker is still unresolved and its direct mechanical repair budget or
same-role reissue path is exhausted.

#### Scenario: Missing startup postcondition uses mechanical repair first
- **WHEN** a startup bootloader Controller receipt is done but the required postcondition is still missing
- **THEN** Router keeps the issue on the mechanical Controller repair/reissue path until that budget is exhausted

#### Scenario: Exhausted mechanical repair can escalate
- **WHEN** the mechanical repair budget for the same blocker is exhausted and the postcondition remains missing
- **THEN** Router may return a PM repair action with the original policy row and exhausted-budget evidence

### Requirement: Result relay next action follows the result recipient
Router SHALL derive result-relay next-action text from the result envelope's expected recipient. PM-bound results SHALL direct Controller to PM disposition; Reviewer-bound results SHALL direct Controller to Reviewer delivery.

#### Scenario: PM-bound result produces PM disposition notice
- **WHEN** a PM-issued packet result has `next_recipient: project_manager`
- **THEN** Router SHALL expose a Controller-visible notice equivalent to `deliver_result_to_pm_for_disposition`
- **AND** Router SHALL NOT expose that result as a direct Reviewer review action.

#### Scenario: Reviewer-bound result keeps Reviewer delivery notice
- **WHEN** a result contract explicitly has `next_recipient: human_like_reviewer`
- **THEN** Router SHALL expose a Reviewer delivery notice only after packet-ledger and recipient checks pass.
