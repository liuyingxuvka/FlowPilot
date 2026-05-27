## ADDED Requirements

### Requirement: Daemon role-output replay preserves repair-owned package conflicts

The Router daemon SHALL reconcile role-output ledger entries through the same
scoped package-disposition conflict classifier used by direct event intake, and
SHALL NOT enter `daemon_error` solely because a stale same-package
different-body conflict is already owned by a control blocker or PM repair
transaction.

#### Scenario: Stale package conflict is replayed after blocker delivery

- **GIVEN** Router state contains a recorded PM package disposition
- **AND** durable role-output storage contains a different-body disposition for
  the same semantic package identity
- **AND** an active control blocker has already been delivered for that
  conflict
- **WHEN** the daemon replays direct role-output events before work selection
- **THEN** the daemon SHALL classify the replay as repair-owned stale conflict
  evidence
- **AND** the daemon SHALL remain live
- **AND** current work selection SHALL continue to show the legal repair wait.

#### Scenario: Stale package conflict is replayed after PM repair decision

- **GIVEN** a PM repair transaction has committed a legal follow-up wait for a
  same-package different-body conflict
- **WHEN** the daemon replays the old conflicting role-output row
- **THEN** the daemon SHALL preserve the committed follow-up wait
- **AND** the daemon SHALL NOT replace it with `daemon_error`.

#### Scenario: Unknown package replay corruption remains blocking

- **GIVEN** a role-output ledger entry cannot be matched to an existing
  recorded package, control blocker, repair transaction, terminal quarantine,
  or valid new package generation
- **WHEN** the daemon tries to reconcile it
- **THEN** Router SHALL surface a conservative control-plane blocker or
  recoverable wait
- **AND** Router SHALL NOT silently accept the entry as success.
