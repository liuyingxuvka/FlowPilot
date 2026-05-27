## ADDED Requirements

### Requirement: Stale saves preserve authoritative package disposition state

FlowPilot SHALL preserve authoritative PM package disposition state during
stale run-state save merges. When a daemon or foreground path saves an older
in-memory run state after a newer PM package disposition has been committed on
disk, the stale-save merge SHALL preserve the newer authoritative package
disposition and matching idempotency evidence.

#### Scenario: Stale daemon state cannot restore older package disposition

- **GIVEN** in-memory daemon state contains an older PM package disposition
  event for a semantic package identity
- **AND** current disk state contains a newer canonical disposition body for
  that same semantic package identity
- **WHEN** Router performs a stale run-state save merge
- **THEN** the merged state SHALL keep the newer canonical package body
- **AND** stale older package-disposition event/history rows SHALL NOT become
  the current authority
- **AND** idempotency evidence SHALL remain aligned with the newer body.
