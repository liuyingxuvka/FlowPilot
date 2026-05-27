## MODIFIED Requirements

### Requirement: Router reclaims valid postcondition evidence before blocking
The Router SHALL check for valid Router-owned postcondition artifacts before escalating a missing-postcondition stateful receipt as a blocker.

#### Scenario: Reconciled receipt has valid evidence but stale flag
- **WHEN** a stateful Controller action has a done receipt, valid Router-owned evidence, and an action or scheduler record that already claims reconciliation
- **AND** the corresponding Router-owned flag is false
- **THEN** Router MUST treat the state as postcondition drift, replay the registered postcondition idempotently, and sync the Router-owned flag
- **AND** the row MUST remain non-duplicable while that reconciliation is in progress

#### Scenario: Replayed evidence is invalid
- **WHEN** an already-reconciled stateful Controller action cannot validate its registered durable evidence during replay
- **THEN** Router MUST mark the postcondition drift as unresolved and route it through bounded Controller repair or control-blocker handling
- **AND** Router MUST NOT issue the same action again as a normal startup or node action while the drift is unresolved

### Requirement: Stateful done receipts require durable evidence
The Router SHALL NOT clear, mark done, or advance from a stateful Controller receipt until the declared Router-visible postcondition evidence exists and has been validated.

#### Scenario: Idempotent stateful replay is safe
- **WHEN** Router observes the same valid done receipt and durable evidence on multiple daemon ticks
- **THEN** replaying the registered postcondition MUST leave the same Router-owned flag true and MUST NOT create duplicate Controller actions, duplicate packet deliveries, or duplicate role-visible side effects
