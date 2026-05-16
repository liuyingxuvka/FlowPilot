# mail-delivery-receipt-folding Specification

## Purpose
TBD - created by archiving change fold-mail-delivery-receipts. Update Purpose after archive.
## Requirements
### Requirement: Mail delivery receipts fold into Router and packet ledgers
FlowPilot SHALL reconcile a completed Controller `deliver_mail` receipt by
folding the mail delivery into Router state and packet/mail ledger before
marking the corresponding postcondition reconciled.

#### Scenario: Controller receipt delivers user intake
- **WHEN** Controller records a done receipt for `deliver_mail` of `user_intake`
  to `project_manager`
- **THEN** Router SHALL set the `user_intake_delivered_to_pm` flag
- **AND** Router SHALL append or reuse a matching `packet_ledger.mail` delivery
  record
- **AND** Router SHALL release the `user_intake` packet to `project_manager`
  through the packet runtime's controller relay path before accepting the
  receipt as reconciled
- **AND** the Controller action row and Router scheduler row SHALL reconcile
  only after those durable ledgers agree.

### Requirement: Mail delivery folding is idempotent
FlowPilot SHALL make mail-delivery receipt reconciliation idempotent for the
same run, mail id, target role, and Controller action.

#### Scenario: repeated daemon receipt reconciliation
- **WHEN** the daemon observes the same completed `deliver_mail` receipt more
  than once
- **THEN** Router SHALL keep one logical mail delivery record
- **AND** Router SHALL NOT duplicate mail delivery counters, ledger entries,
  holder history, or controller relay history.

### Requirement: Unsupported mail delivery receipts stay blocked
FlowPilot SHALL keep a `deliver_mail` receipt on the explicit mechanical
control-blocker path when Router cannot prove the corresponding ledger fold.

#### Scenario: mail delivery fold cannot be proven
- **WHEN** Controller records a done `deliver_mail` receipt but Router cannot
  fold the packet/mail ledger, Router flag, and packet runtime relay signature
- **THEN** Router SHALL NOT mark the postcondition reconciled
- **AND** Router SHALL surface or preserve a
  `controller_action_receipt_missing_router_postcondition` blocker.

### Requirement: PM repair decisions become repair transactions
FlowPilot SHALL consume a PM repair decision for a mail-delivery control
blocker into a repair transaction or reissue plan before continuing the same
role wait.

#### Scenario: PM selects same-gate repair
- **WHEN** PM records a same-gate repair decision for a `deliver_mail`
  control blocker
- **THEN** Router SHALL record the decision as consumed
- **AND** Router SHALL create or activate a repair transaction or reissue plan
  for the blocked mail-delivery gate
- **AND** Router SHALL NOT continue waiting as if the PM decision were absent.
