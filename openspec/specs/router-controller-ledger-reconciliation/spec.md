# router-controller-ledger-reconciliation Specification

## Purpose
TBD - created by archiving change reconcile-controller-router-ledgers. Update Purpose after archive.
## Requirements
### Requirement: Controller receipts are not workflow completion
FlowPilot SHALL treat Controller action receipts as Controller-local evidence only. A Controller receipt MUST NOT by itself mark a target role output, Router-owned durable artifact, or route gate complete.

#### Scenario: Controller delivers work to another role
- **WHEN** Controller records a done receipt for an action whose purpose is to deliver work to PM, Reviewer, an officer, or a worker
- **THEN** Router records the Controller delivery as done and records the target role work as waiting until a valid role output or Router-authorized event arrives

#### Scenario: Controller writes a Router-owned artifact
- **WHEN** Controller records a done receipt for an action that writes Router-owned durable evidence
- **THEN** Router verifies the registered artifact and proof before marking the Router-owned postcondition complete

### Requirement: Router ownership ledger is authoritative for workflow state
FlowPilot SHALL maintain a Router-owned ledger for workflow ownership, waiting, durable artifact reclaim, and blocker decisions. Controller MUST NOT write final workflow completion fields in that ledger.

#### Scenario: Router reconciles a Controller receipt
- **WHEN** Router observes a new Controller receipt
- **THEN** Router updates its ownership ledger according to the action class before selecting the next action

#### Scenario: Controller ledger and Router ledger disagree
- **WHEN** the Controller ledger says an action is done but Router-owned evidence has not yet been reclaimed
- **THEN** Router keeps the workflow item in a reclaim-pending or waiting state instead of treating the Controller receipt as final completion

#### Scenario: Controller cannot read Router workflow ledger
- **WHEN** Router writes daemon status for Controller
- **THEN** Controller can see the Controller action ledger and safe recovery facts, but not the Router ownership ledger entries or workflow-state table

### Requirement: Router reconciles before choosing next action or blocker
FlowPilot SHALL run a reconciliation barrier before every daemon next-action decision, manual next-action decision, and control-blocker creation.

#### Scenario: Valid startup display receipt exists before next action
- **WHEN** Controller has a done receipt for `write_display_surface_status`, the startup display artifacts validate for the current run, and `startup_display_status_written` is false
- **THEN** Router MUST reclaim the display postcondition, set `startup_display_status_written=true`, mark matching action and scheduler rows reconciled, and compute the next action from the updated state
- **AND** Router MUST NOT enqueue another ordinary `write_display_surface_status` row for the same scope

#### Scenario: Already-reconciled stateful row has stale flag
- **WHEN** a Controller action or scheduler row is already Router-reconciled and names a registered stateful postcondition whose Router-owned flag is false
- **THEN** Router MUST replay or reclaim that postcondition during reconciliation before next-action selection
- **AND** if the postcondition cannot be validated, Router MUST create bounded repair/blocker evidence instead of treating the row as complete or issuing a duplicate ordinary command

#### Scenario: Receipt folding precedes startup intake release
- **WHEN** startup `user_intake` release depends on startup activation and startup activation depends on pre-review reconciliation
- **THEN** Router MUST fold all startup-local Controller receipt postconditions into authoritative run state before deciding whether startup activation remains blocked

### Requirement: Missing ACK recovery checks Controller delivery first
FlowPilot SHALL check Controller delivery facts before reminding a target role about a missing system-card ACK.

#### Scenario: Controller delivery not confirmed
- **WHEN** a system-card ACK is missing and the matching Controller delivery action is pending, blocked, skipped, missing a valid committed artifact, or otherwise not confirmed done
- **THEN** Router returns a Controller delivery confirmation or reissue recovery action and MUST NOT remind the target role yet

#### Scenario: Controller delivery confirmed
- **WHEN** a system-card ACK is missing and the matching Controller delivery action is confirmed done with the original committed envelope or bundle still valid
- **THEN** Router may remind the target role to open and ACK the original committed card or bundle, without issuing a duplicate system card

### Requirement: Reconciliation stays lightweight
FlowPilot SHALL keep recurring daemon reconciliation scoped to the current run's known ledger entries and registered artifact paths.

#### Scenario: One-second daemon tick
- **WHEN** the Router daemon wakes for its one-second tick
- **THEN** it reads current-run Controller receipts, Router ownership ledger entries, pending action metadata, and registered artifact/proof paths without performing a broad repository scan

### Requirement: Controller ledger reconciliation folds evidence before repair decisions
FlowPilot SHALL reconcile Controller action ledger rows by folding registered Router-visible relay evidence before scheduling retries, PM repair decisions, or control blockers for missing postconditions.

#### Scenario: Done receipt has stale aggregate flag but valid evidence
- **WHEN** the Controller ledger row is `done`
- **AND** the Router-owned aggregate postcondition flag is false
- **AND** packet or result relay evidence proves the registered postcondition
- **THEN** Router MUST update the aggregate flag from evidence
- **AND** Router MUST NOT ask PM to repair the already-proven relay action

#### Scenario: Evidence contradicts the receipt
- **WHEN** the Controller ledger row is `done`
- **AND** the registered evidence fold finds missing, invalid, or contradictory relay records
- **THEN** Router MUST NOT treat the Controller receipt alone as proof
- **AND** Router MUST preserve the existing retry and repair escalation behavior

### Requirement: Controller ledger reconciliation records fold outcomes
FlowPilot SHALL expose whether a relay receipt was reconciled by a registered evidence fold, by an already-true flag, or by the existing non-relay stateful handler.

#### Scenario: Evidence fold repairs stale state
- **WHEN** a registered evidence fold changes a Router-owned flag from false to true
- **THEN** Router SHOULD include an evidence-fold outcome reason in the receipt reconciliation result or traceable Controller row update

### Requirement: Router reconciles registered state-loader receipts before blocker routing
FlowPilot SHALL attempt registered Router-owned state replay during Controller
receipt reconciliation before classifying the receipt as an unsupported
stateful Controller postcondition.

#### Scenario: Receipt corresponds to registered Router-owned state replay
- **WHEN** Router observes a Controller `done` receipt for a registered
  Router-owned state loader action
- **THEN** Router MUST invoke the registered Router state replay path
- **AND** Router MUST record the reconciliation source as Router-owned state
  replay rather than Controller-local completion

#### Scenario: Replay does not satisfy the postcondition
- **WHEN** Router invokes a registered Router-owned state replay path from a
  Controller receipt
- **AND** the declared Router-owned postcondition remains false
- **THEN** Router MUST keep the action incomplete or blocked
- **AND** Router MUST NOT advance next-action selection from the receipt alone

### Requirement: Controller receipts remain ownership-scoped
FlowPilot SHALL keep Controller receipts scoped to the ownership class of the
action being reconciled.

#### Scenario: Evidence-backed Controller action uses evidence fold
- **WHEN** the receipt action owns Controller-produced Router-visible evidence
- **THEN** Router MUST use the registered evidence fold for that evidence
  class

#### Scenario: Router-owned state action uses state replay
- **WHEN** the receipt action owns Router state loading
- **THEN** Router MUST use the registered Router-owned state replay path and
  MUST NOT use a generic evidence-fold or receipt-only completion path

### Requirement: Controller-Router Reconciliation Shares Closure Decisions
Router-controller reconciliation SHALL use the shared closure kernel when
projecting Controller-visible action rows and Router-executable obligations into
blocking or nonblocking workflow state.

#### Scenario: Controller-visible closure matches Router obligation closure
- **WHEN** a Controller action row and Router obligation row refer to the same
  obligation identity and the closure kernel classifies the obligation as
  nonblocking
- **THEN** Router reconciliation MUST NOT re-open the same obligation through a
  stale pending action, scheduler row, or passive wait projection

#### Scenario: Identity mismatch cannot close another obligation
- **WHEN** a Controller row has a closed status but its identity does not match
  the Router obligation being reconciled
- **THEN** the closure kernel classification for that Router obligation remains
  blocking or repair-required
