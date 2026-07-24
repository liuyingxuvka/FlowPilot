## ADDED Requirements

### Requirement: Stable receipt reconciliation is semantically idempotent
Router SHALL classify a receipt whose content hash and applied scheduler/action
effect already match current state as already current.  Re-observing it SHALL
NOT refresh semantic timestamps, rewrite action or scheduler ledgers, or append
deferred-fold, reminder, passive-wait, or reconciliation history.

#### Scenario: Repeated current receipt
- **WHEN** the same valid current Controller receipt is reconciled ten thousand times
- **THEN** exactly one action effect and one scheduler effect remain authoritative
- **AND** all subsequent reconciliations report no semantic change

#### Scenario: Receipt content changes under the same action
- **WHEN** a receipt identity is reused with a different unsupported content hash
- **THEN** Router rejects or blocks the conflicting receipt
- **AND** it does not overwrite the current action effect or create a second successful path

### Requirement: Observation counters are not semantic authority
Action `seen_count`, action `last_seen_at`, copied wait-reminder histories, and
the daemon's per-tick history SHALL NOT be current runtime authority.  Current
receipt/action/wait state SHALL be derived from the existing owner records and
compact last-reminder identity/count fields only where required.

#### Scenario: Passive wait remains unchanged
- **WHEN** daemon observation confirms the same passive wait without changing its target, status, reminder identity, or return event
- **THEN** no action, wait, return-event, controller-ledger, or history file is rewritten
