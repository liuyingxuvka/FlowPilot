## MODIFIED Requirements

### Requirement: Daemon reconciles direct role-output events before work selection
The Router daemon SHALL fold every authorized direct role-output event from durable role-output storage into canonical Router events, flags, and registered side-effect projections before returning an existing pending action or computing new work.

#### Scenario: Ordinary research result event exists only in role output ledger
- **WHEN** a valid ordinary research Worker result declares `worker_research_report_returned`, the matching Controller action row is done, and the matching Router scheduler row is reconciled, but Router state lacks the research-result event and flag
- **THEN** Router MUST record the canonical event, expose the existing PM research-result disposition path, and MUST NOT continue projecting the old Worker wait.

#### Scenario: Generic direct role event is replayed
- **WHEN** a valid direct role-output event was already folded into Router state and the same durable role-output evidence is seen again
- **THEN** Router MUST treat the replay as idempotent and MUST NOT record a duplicate event or duplicate side effect.

#### Scenario: Invalid or unauthorized direct role event exists
- **WHEN** a role-output ledger entry is missing runtime validation, declares an event that is not expected for the active wait, or violates the role-output contract
- **THEN** Router MUST NOT fold it into canonical Router events and MUST surface a control-plane blocker or conservative waiting state.
