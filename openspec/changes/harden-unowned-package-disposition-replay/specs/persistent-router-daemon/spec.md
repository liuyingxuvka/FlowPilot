## ADDED Requirements

### Requirement: Daemon survives stale unowned package replay

The persistent Router daemon SHALL NOT enter `daemon_error` solely because a
durable role-output row replays an older different-body PM package disposition
after a newer canonical package disposition has already been committed.

#### Scenario: Older role-output row follows newer foreground commit

- **GIVEN** a foreground Router path commits a newer PM package disposition
  body for a semantic package identity
- **AND** daemon role-output reconciliation later sees an older durable row for
  the same semantic identity with a different body hash
- **WHEN** the daemon tick reconciles role-output evidence
- **THEN** the daemon SHALL quarantine or audit the stale row
- **AND** the daemon SHALL remain live
- **AND** the daemon SHALL continue from the current canonical state.

#### Scenario: Daemon replay does not append stale package success

- **GIVEN** daemon reconciliation classifies a role-output row as stale unowned
  package replay
- **WHEN** the daemon saves run state after the tick
- **THEN** the stale row SHALL NOT be appended as a successful package
  disposition event
- **AND** it SHALL NOT close waits or progress gates as if the stale body were
  current PM output.
