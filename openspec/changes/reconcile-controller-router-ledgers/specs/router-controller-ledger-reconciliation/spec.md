## ADDED Requirements

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

### Requirement: Router reconciles before choosing next action or blocker
FlowPilot SHALL run a reconciliation barrier before every daemon next-action decision, manual next-action decision, and control-blocker creation.

#### Scenario: Valid startup mechanical audit exists before blocker decision
- **WHEN** Controller has a done receipt for `write_startup_mechanical_audit`, the startup audit exists, and the Router-owned proof validates for the current run
- **THEN** Router marks `startup_mechanical_audit_written` true, records the reclaim in the Router ownership ledger, clears the pending Controller action, and continues without creating `controller_action_receipt_missing_stateful_postcondition`

#### Scenario: Unsupported stateful host action remains incomplete
- **WHEN** Controller has a done receipt for a stateful host action that has no registered durable reclaim path and its postcondition remains false
- **THEN** Router creates the existing stateful postcondition blocker

### Requirement: Reconciliation stays lightweight
FlowPilot SHALL keep recurring daemon reconciliation scoped to the current run's known ledger entries and registered artifact paths.

#### Scenario: One-second daemon tick
- **WHEN** the Router daemon wakes for its one-second tick
- **THEN** it reads current-run Controller receipts, Router ownership ledger entries, pending action metadata, and registered artifact/proof paths without performing a broad repository scan
