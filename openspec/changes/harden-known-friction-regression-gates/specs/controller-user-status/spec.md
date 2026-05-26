## ADDED Requirements

### Requirement: Current status reflects latest control-plane facts
Controller user status SHALL derive current progress and wait wording from the
latest reconciled run state, repair transaction, active blocker, ACK ledger,
and lifecycle facts.

#### Scenario: PM repair decision is already committed
- **WHEN** a PM repair transaction has been committed and the fresh repair
  generation is registered
- **THEN** user-visible current status MUST NOT say FlowPilot is still waiting
  for PM to decide the same blocker.

#### Scenario: ACK has been resolved
- **WHEN** a required ACK has a valid receipt and the target semantic work is
  still pending
- **THEN** user-visible current status MUST state that the receipt is resolved
  and that the remaining wait is for semantic work, not for the same ACK.

#### Scenario: Run is stopped
- **WHEN** a user stop has been recorded for the current run
- **THEN** user-visible current status MUST report the run as stopped or
  terminal and MUST NOT present it as an active route.
