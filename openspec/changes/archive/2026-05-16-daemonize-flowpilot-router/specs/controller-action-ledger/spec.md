## ADDED Requirements

### Requirement: Controller action ledger
FlowPilot SHALL use a durable Controller action ledger as the canonical channel
from Router daemon to Controller executor.

#### Scenario: Router issues Controller work
- **WHEN** Router needs Controller to relay a card, deliver a bundle, display text, update visible plan, create automation, spawn roles, close roles, or perform another host action
- **THEN** Router MUST create a Controller action entry with action id, action type, dependencies, allowed reads, allowed writes, authority boundaries, required receipt path, and initial status `pending`

#### Scenario: Controller action ledger is a checklist
- **WHEN** more than one Controller action is pending
- **THEN** Controller MUST treat the ledger as a checklist and clear all dependency-satisfied pending actions rather than waiting for a single latest action only

### Requirement: Controller executor one-second checklist loop
The Controller executor SHALL check the Controller action ledger once per second
while attached to an active Router daemon.

#### Scenario: Pending action is ready
- **WHEN** a pending Controller action has all dependencies satisfied
- **THEN** Controller MUST execute the action, write a receipt, and rescan the ledger for additional ready work

#### Scenario: No ready action exists
- **WHEN** no pending Controller action is ready and the run is still active
- **THEN** Controller MUST continue checking the ledger on the fixed one-second interval unless Router marks a terminal, user, or host boundary

### Requirement: One receipt per Controller action
Controller SHALL write one durable receipt for each attempted Controller action.

#### Scenario: Action completes successfully
- **WHEN** Controller completes a Router-authored action
- **THEN** Controller MUST write the required receipt path with action id, performed action type, completion status, timestamp, and host evidence allowed by the action contract

#### Scenario: Action cannot be completed
- **WHEN** Controller cannot complete a Router-authored action
- **THEN** Controller MUST write a blocked receipt with the concrete blocker instead of silently leaving the action pending or inventing a route decision

### Requirement: Action status ownership
FlowPilot SHALL enforce separate ownership for Controller action status changes.

#### Scenario: Router creates or cancels action
- **WHEN** Router creates, retries, supersedes, or cancels a Controller action
- **THEN** Router MAY write ledger states `pending`, `retry_requested`, `superseded`, or `cancelled`

#### Scenario: Controller attempts action
- **WHEN** Controller starts or finishes a Controller action
- **THEN** Controller MAY report `in_progress`, `done`, or `blocked` only through the action receipt path

#### Scenario: Router reconciles receipt
- **WHEN** Router sees a valid Controller receipt
- **THEN** Router MUST reconcile the action ledger from the receipt and decide the next Router state transition

### Requirement: Controller does not final at ordinary Router waits
Controller SHALL NOT end its foreground work merely because Router is waiting
for ordinary role ACKs, bundle ACKs, packet returns, role reports, or result
envelopes while Router daemon mode is active.

#### Scenario: Router waits for role evidence
- **WHEN** Router daemon is active and the current Router wait is an ordinary card, bundle, packet, report, result, or Controller receipt wait
- **THEN** Controller MUST remain attached to the action ledger loop and MUST NOT treat the ordinary wait as a final answer or terminal stop

#### Scenario: Router reaches true boundary
- **WHEN** Router writes a Controller action or daemon status that explicitly requires user input, host intervention, terminal summary, or run stop/cancel
- **THEN** Controller MAY stop foreground execution only after completing the Router-authored boundary action and receipt

### Requirement: Controller remains envelope-only
The Controller action ledger SHALL preserve existing Controller visibility and
sealed-body boundaries.

#### Scenario: Relay packet or result
- **WHEN** a Controller action relays a card, bundle, packet, report, or result envelope
- **THEN** Controller MUST relay only Router-authorized metadata and MUST NOT read sealed packet, result, report, or card bodies

#### Scenario: Display user-visible text
- **WHEN** a Controller action requires user-dialog display
- **THEN** Controller MUST display exactly the Router-provided display text and write the required display receipt without adding hidden evidence or sealed content
