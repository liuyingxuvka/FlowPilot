## ADDED Requirements

### Requirement: Canonical package authority owns stale unowned replay

FlowPilot SHALL let the current canonical PM package disposition artifact own
role-output replay authority for the same semantic package identity. When that
artifact already records the current body, Router SHALL treat replay of an
older different-body disposition as stale replay evidence rather than a fresh
accepted package disposition.

#### Scenario: Newer package body is already canonical

- **GIVEN** Router has a canonical PM package disposition artifact for a
  router event, batch id, packet ids, and packet generation id
- **AND** durable role-output storage contains an older PM disposition for the
  same semantic package identity with a different body hash
- **WHEN** Router reconciles the durable role-output row
- **THEN** Router SHALL NOT accept the older body as the package disposition
- **AND** Router SHALL preserve the canonical disposition body and hash
- **AND** Router SHALL record explicit stale replay quarantine or audit
  evidence.

#### Scenario: Direct different-body intake remains a hard conflict

- **GIVEN** a PM package disposition has already been recorded for a semantic
  package identity
- **WHEN** a new direct PM disposition for the same semantic identity has a
  different body hash and no authorized repair or reissue path owns it
- **THEN** Router SHALL reject, block, or quarantine the conflict
- **AND** Router SHALL NOT silently treat the new body as idempotent success.

### Requirement: Canonical package and idempotency body stay aligned

Router SHALL keep the canonical PM package disposition artifact and scoped
external-event idempotency record aligned to the same current body when stale
role-output replay or stale daemon state is reconciled.

#### Scenario: Stale replay cannot split package authority

- **GIVEN** the canonical package artifact points to a newer body hash
- **AND** daemon reconciliation sees an older role-output row for the same
  semantic package identity
- **WHEN** Router completes reconciliation
- **THEN** the idempotency record for that event SHALL NOT be moved to the
  older replay body
- **AND** no later event-history entry SHALL represent the older body as the
  current package disposition.
