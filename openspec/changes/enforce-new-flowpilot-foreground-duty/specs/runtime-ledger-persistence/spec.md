## ADDED Requirements

### Requirement: New-runtime duty snapshots persist with the ledger
New FlowPilot runtime ledger persistence SHALL write foreground duty snapshots
and final-return preflight evidence atomically with the current ledger-derived
lifecycle guard state.

#### Scenario: Status write includes foreground duty
- **WHEN** the new runtime writes status for a nonterminal run
- **THEN** the persisted status projection MUST include the current
  `foreground_duty`
- **AND** the run ledger MUST include enough duty snapshot metadata to rederive
  the same final-return preflight from files.

#### Scenario: Patrol write preserves wait history
- **WHEN** the new runtime records a wait patrol duty
- **THEN** the ledger MUST preserve the patrol subject, reason, delay seconds,
  event count, and repeated-action key
- **AND** the write MUST remain metadata-only and not expose sealed packet or
  result bodies.

#### Scenario: Final preflight is current-state evidence
- **WHEN** the foreground Controller asks whether it can return terminal output
- **THEN** the answer MUST be derived from the current ledger, lifecycle guard,
  and duty snapshot
- **AND** stale status projection files MUST NOT be sufficient stop evidence.
