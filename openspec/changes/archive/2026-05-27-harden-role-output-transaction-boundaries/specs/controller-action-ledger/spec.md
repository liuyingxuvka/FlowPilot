## ADDED Requirements

### Requirement: Blocker-related waits use blocker-scoped identities
FlowPilot SHALL include blocker-scoped identity fields in Controller action ids and scheduler idempotency keys for any action that carries control-blocker identity.

#### Scenario: Await-role-decision rows for different blockers are distinct
- **WHEN** Router creates two `await_role_decision` actions for different control blockers
- **THEN** the actions MUST have distinct deterministic ids and scheduler idempotency keys

#### Scenario: Blocker repair rows keep current idempotency
- **WHEN** Router repeats the same control-blocker repair or wait for the same blocker
- **THEN** the action identity MUST remain stable across retries
