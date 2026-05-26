## ADDED Requirements

### Requirement: Role reissue waits require concrete producers
FlowPilot SHALL NOT commit a `role_reissue` repair transaction that waits for a role-produced event unless the transaction can prove that a concrete producer exists or will be created for that awaited event.

#### Scenario: Role reissue without producer is rejected
- **WHEN** PM submits a control-blocker repair decision with `repair_transaction.plan_kind=role_reissue`
- **AND** the selected `rerun_target` is a role-produced event
- **AND** the repair transaction does not create replacement packets, replay a current operation, reference an existing producer, or provide a bounded work packet that can emit the event
- **THEN** Router MUST reject the repair decision before writing a committed repair transaction
- **AND** Router MUST leave the original control blocker active for a corrected PM decision.

#### Scenario: Material self-check rework uses packet reissue or replay
- **WHEN** worker material-scan results are returned but their result envelopes show failed contract self-checks
- **AND** PM selects same-gate repair so workers must produce corrected `worker_scan_results_returned` evidence
- **THEN** Router MUST require a concrete `packet_reissue`, a current-generation `operation_replay`, a bounded `controller_repair_work_packet`, or an explicit blocker/terminal outcome
- **AND** Router MUST NOT expose a bare wait for `worker_scan_results_returned`.

#### Scenario: Valid packet reissue remains executable
- **WHEN** PM submits a material-scan `packet_reissue` repair transaction with replacement packet specs
- **THEN** Router MUST commit the new packet generation and expose the material packet relay path before waiting for worker results.
