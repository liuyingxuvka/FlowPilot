## MODIFIED Requirements

### Requirement: Deterministic setup is not Controller work
FlowPilot SHALL NOT schedule deterministic setup actions as Controller action
ledger rows after the seed has completed. This includes placeholder filling,
mailbox initialization, raw user-request recording, user-intake scaffold
creation, and startup answer recording that was already completed by the native
startup intake seed.

#### Scenario: Scheduler excludes deterministic setup rows
- **WHEN** the bootstrap seed has completed successfully
- **THEN** the Router scheduler and Controller action ledgers do not contain
  rows for deterministic file setup actions

#### Scenario: Completed startup answer seed excludes answer row
- **WHEN** the startup intake seed has recorded startup answers for the current
  run
- **THEN** the Router scheduler and Controller action ledgers do not require a
  later `record_startup_answers` row for the same answers.
