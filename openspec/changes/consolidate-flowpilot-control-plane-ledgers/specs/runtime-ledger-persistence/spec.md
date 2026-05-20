## ADDED Requirements

### Requirement: Atomic write verification uses transient-lock semantics
Runtime ledger persistence SHALL apply transient write-lock semantics to atomic
write verification and read-back, not only to the replace operation.

#### Scenario: Replace succeeds but verification is denied
- **WHEN** a runtime JSON write replaces a daemon-critical ledger successfully
- **AND** the immediate verification read receives a transient access-denied
  error
- **THEN** the write helper reports a retryable write-in-progress outcome
- **AND** the caller MUST NOT classify the ledger as corrupt or the daemon as
  failed from that transient denial alone.
