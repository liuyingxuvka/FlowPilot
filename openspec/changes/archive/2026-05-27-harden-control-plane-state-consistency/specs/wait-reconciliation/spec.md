## MODIFIED Requirements

### Requirement: Wait reminders are deduplicated by durable wait identity

Router SHALL materialize wait target reminders from stable durable wait identity and persisted cooldown state.

#### Scenario: Pending wait projection loses last reminder
- **WHEN** a wait reminder receipt already recorded a reminder for a stable wait identity
- **AND** a stale pending-action projection omits `last_wait_reminder_at`
- **THEN** Router MUST recover reminder state from durable reminder history or scheduler/controller action rows
- **AND** Router MUST NOT create a duplicate reminder before the cooldown expires
