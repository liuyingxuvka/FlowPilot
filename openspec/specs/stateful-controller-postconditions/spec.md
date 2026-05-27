# stateful-controller-postconditions Specification

## Purpose
TBD - created by archiving change require-stateful-controller-postconditions. Update Purpose after archive.
## Requirements
### Requirement: Stateful Controller actions declare postconditions
The Router SHALL distinguish Controller actions that require Router-visible
postcondition evidence from Controller actions that are complete with a receipt
alone.

#### Scenario: Startup boundary action is stateful
- **WHEN** the Router issues `confirm_controller_core_boundary`
- **THEN** the action record MUST declare the required boundary confirmation
  artifact and synced Router flags as postconditions

#### Scenario: Generic Controller action remains receipt-only
- **WHEN** the Router issues a Controller action with no stateful postcondition
- **THEN** the Router MAY reconcile that action with a valid Controller receipt
  alone

### Requirement: Stateful done receipts require durable evidence
The Router SHALL NOT clear, mark done, or advance from a stateful Controller receipt until the declared Router-visible postcondition evidence exists and has been validated.

#### Scenario: Idempotent stateful replay is safe
- **WHEN** Router observes the same valid done receipt and durable evidence on multiple daemon ticks
- **THEN** replaying the registered postcondition MUST leave the same Router-owned flag true and MUST NOT create duplicate Controller actions, duplicate packet deliveries, or duplicate role-visible side effects

### Requirement: Router reclaims valid postcondition evidence before blocking
The Router SHALL check for valid Router-owned postcondition artifacts before escalating a missing-postcondition stateful receipt as a blocker.

#### Scenario: Reconciled receipt has valid evidence but stale flag
- **WHEN** a stateful Controller action has a done receipt, valid Router-owned evidence, and an action or scheduler record that already claims reconciliation
- **AND** the corresponding Router-owned flag is false
- **THEN** Router MUST treat the state as postcondition drift, replay the registered postcondition idempotently, and sync the Router-owned flag
- **AND** the row MUST remain non-duplicable while that reconciliation is in progress

#### Scenario: Replayed evidence is invalid
- **WHEN** an already-reconciled stateful Controller action cannot validate its registered durable evidence during replay
- **THEN** Router MUST mark the postcondition drift as unresolved and route it through bounded Controller repair or control-blocker handling
- **AND** Router MUST NOT issue the same action again as a normal startup or node action while the drift is unresolved

### Requirement: Missing Controller deliverables use bounded repair rows
The Router SHALL give Controller a bounded chance to complete missing
deliverables before escalating a stateful receipt to PM/control-blocker repair.

#### Scenario: First missing deliverable creates repair row
- **WHEN** a stateful Controller action has a `done` receipt and no valid
  required deliverable
- **THEN** the original action MUST be marked incomplete or repair-pending and a
  `complete_missing_controller_deliverable` row MUST be issued to Controller

#### Scenario: Repair succeeds
- **WHEN** a Controller repair row produces a valid required deliverable
- **THEN** the Router MUST mark the repair row done, mark the original action
  resolved by repair, sync the Router-owned flags, and continue

#### Scenario: Repair budget exhausted
- **WHEN** the original stateful Controller action has already used two
  deliverable repair attempts and the required deliverable is still missing or
  invalid
- **THEN** the Router MUST create a control blocker that names the original
  action, the missing deliverable, and the exhausted repair attempts

### Requirement: Controller boundary confirmation is artifact-backed
The Router SHALL treat Controller boundary confirmation as complete only when
the boundary confirmation artifact exists and the corresponding Router flags are
synced from that artifact.

#### Scenario: Role confirmed without artifact
- **WHEN** `controller_role_confirmed` is true but
  `startup/controller_boundary_confirmation.json` is missing
- **THEN** FlowGuard and runtime reconciliation MUST reject the state as
  incomplete

### Requirement: Stateful relay postconditions reconcile from evidence folds
FlowPilot SHALL apply registered packet/result relay evidence folds before treating a Controller `done` receipt as an unsupported stateful postcondition.

#### Scenario: Relay receipt is supported by registered evidence
- **WHEN** Controller records a `done` receipt for an evidence-backed relay action
- **AND** Router-visible evidence satisfies the registered fold for that action
- **THEN** Router MUST set the corresponding postcondition flag
- **AND** Router MUST reconcile the Controller receipt as successful
- **AND** Router MUST NOT emit `unsupported_stateful_controller_receipt`

#### Scenario: Relay receipt lacks required evidence
- **WHEN** Controller records a `done` receipt for an evidence-backed relay action
- **AND** Router-visible evidence does not satisfy the registered fold for that action
- **THEN** Router MUST leave the postcondition flag false
- **AND** Router MUST use the existing bounded retry or repair path

### Requirement: Stateful receipt folding remains idempotent
FlowPilot SHALL make registered relay receipt folds idempotent and SHALL NOT rerun ordinary relay side effects while reconciling a Controller receipt.

#### Scenario: Receipt is processed more than once
- **WHEN** Router observes the same `done` receipt and the same relay evidence on more than one scheduler tick
- **THEN** Router MUST keep the postcondition flag true
- **AND** Router MUST NOT duplicate packet relay history, active-holder leases, result relay rows, or batch counters

### Requirement: Break-glass patches require validation disposition
FlowPilot SHALL close break-glass patch records through the existing break-glass lifecycle after validation evidence is available.

#### Scenario: Patch validation finalizes disposition
- **WHEN** a break-glass patch record has validation evidence that has been run or superseded by a permanent FlowPilot fix
- **THEN** the patch MUST record `final_disposition`
- **AND** the related incident MUST either close or name the remaining blocker

#### Scenario: Pending patch blocks clean control-plane claim
- **WHEN** a break-glass patch remains temporary and lacks final disposition after validation is required
- **THEN** FlowGuard and runtime audit MUST continue to report the control plane as not clean.

### Requirement: Packet relay receipts require runtime relay evidence
The Router SHALL NOT reconcile a Controller packet or result relay `done` receipt until every addressed envelope has verified Controller relay evidence in the envelope and matching packet ledger holder/status evidence.

#### Scenario: Done receipt without relay signature stays incomplete
- **WHEN** Controller records a `done` receipt for a packet/result relay action but an addressed envelope lacks a valid `controller_relay`
- **THEN** Router MUST NOT set the relay postcondition flag
- **AND** Router MUST mark the original Controller action as incomplete, retry-pending, or repair-pending rather than reconciled

#### Scenario: Done receipt with verified relay evidence closes
- **WHEN** Controller records a `done` receipt for a packet/result relay action and every addressed envelope has valid Controller relay evidence plus matching packet ledger holder/status evidence
- **THEN** Router MUST reconcile the receipt, set the declared relay postcondition, and avoid reissuing the same relay action

### Requirement: Active-holder relay postconditions include lease evidence
For packet relay actions that declare an active-holder fast lane, the Router SHALL require valid active-holder lease evidence after runtime relay whenever a live target agent id is available.

#### Scenario: Relay signature exists but required lease is missing
- **WHEN** a packet relay action declares active-holder fast-lane lease issuance and the target live agent id is known, but the packet has no valid active-holder lease
- **THEN** Router MUST keep the relay postcondition incomplete or repair-pending
- **AND** Router MUST expose the missing lease as Controller/Router mechanical evidence, not Worker completion evidence

### Requirement: Router-owned state loader receipts replay Router handlers
The Router SHALL treat registered Router-owned state loader receipts as replay
requests for the registered Router action handler, not as standalone proof that
the Router-owned postcondition is satisfied.

#### Scenario: Registered state loader receipt replays Router handler
- **WHEN** Controller records a valid `done` receipt for a registered
  Router-owned state loader such as `load_resume_state`
- **THEN** Router MUST apply the registered Router action handler for that
  action type before marking the action reconciled
- **AND** Router MUST mark the stateful action reconciled only after the
  declared Router-owned postcondition flag is satisfied

#### Scenario: Unregistered state loader receipt remains unsupported
- **WHEN** Controller records a valid `done` receipt for a stateful loader
  action that writes Router-owned state but is not registered as replayable
- **THEN** Router MUST NOT treat the receipt as proof of the postcondition
- **AND** Router MUST route the action through the existing unsupported or
  missing-postcondition blocker path

### Requirement: Stateful receipt audits include Router-owned state replay
FlowGuard source audits SHALL reject Router-owned state loader actions that
write Router-owned flags without a corresponding registered replay path.

#### Scenario: State loader writes Router flag without replay registration
- **WHEN** a `load_*_state` action handler writes a Router-owned flag
- **AND** that action type is absent from the Router-owned state replay
  registry
- **THEN** the focused Controller receipt FlowGuard check MUST fail with a
  missing replay registration finding

#### Scenario: State loader replay registration is present
- **WHEN** a `load_*_state` action handler writes a Router-owned flag
- **AND** that action type is present in the Router-owned state replay registry
- **THEN** the focused Controller receipt FlowGuard source audit MUST accept
  the state loader replay contract
