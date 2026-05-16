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
The Router SHALL NOT clear, mark done, or advance from a stateful Controller
receipt until the declared Router-visible postcondition evidence exists and has
been validated.

#### Scenario: Receipt arrives without evidence
- **WHEN** a stateful Controller action has a `done` receipt but the declared
  durable evidence is missing
- **THEN** the Router MUST mark the action incomplete, create a bounded
  Controller repair row for the missing deliverable, and MUST NOT advance
  startup or route work from that receipt alone

#### Scenario: Receipt and evidence both exist
- **WHEN** a stateful Controller action has a valid `done` receipt and the
  declared durable evidence validates
- **THEN** the Router MUST clear the action, sync the Router-owned flags, and
  compute the next action from the updated state

### Requirement: Router reclaims valid postcondition evidence before blocking
The Router SHALL check for valid Router-owned postcondition artifacts before
escalating a missing-postcondition stateful receipt as a blocker.

#### Scenario: Artifact exists but flag is stale
- **WHEN** a valid Router-owned postcondition artifact exists but the matching
  Router flag has not been synced
- **THEN** the Router MUST reclaim the artifact, sync the flag, and continue
  reconciliation without creating a PM repair blocker

#### Scenario: Artifact is absent or invalid
- **WHEN** a stateful Controller receipt is present but the declared artifact is
  absent or invalid
- **THEN** the Router MUST first create a Controller repair row that identifies
  the action type and missing postcondition evidence

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
