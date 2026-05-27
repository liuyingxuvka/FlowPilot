## ADDED Requirements

### Requirement: Resolved external-event waits invalidate matching pending action
Router SHALL invalidate a `pending_action` projection when its referenced Controller action row or Router scheduler row is durably resolved.

#### Scenario: Controller and scheduler rows are resolved
- **WHEN** `router_state.pending_action` references an `await_role_decision` action whose Controller action row is `done` or whose Router scheduler row is `reconciled`
- **THEN** Router MUST clear or ignore that pending action before daemon status, current-work selection, reminder creation, or next-action computation

#### Scenario: Resolved wait has no Router event yet
- **WHEN** a wait row is resolved but Router state does not yet contain the event or flag that explains the resolution
- **THEN** Router MUST run durable event reconciliation before selecting new work and MUST NOT use the stale pending action as the current owner

#### Scenario: Reconciled wait would trigger reminder
- **WHEN** a wait row has already been reconciled from an external event
- **THEN** Router MUST NOT create a role reminder for that wait, even if `pending_action.last_wait_reminder_at` is absent or stale
