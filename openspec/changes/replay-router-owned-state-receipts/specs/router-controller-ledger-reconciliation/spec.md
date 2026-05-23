## ADDED Requirements

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
