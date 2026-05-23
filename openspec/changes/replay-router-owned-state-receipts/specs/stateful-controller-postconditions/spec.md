## ADDED Requirements

### Requirement: Router-owned state loader receipts replay Router handlers
The Router SHALL treat registered Router-owned state loader receipts as replay
requests for the registered Router action handler, not as standalone proof that
the Router-owned postcondition is satisfied.

#### Scenario: Registered state loader receipt replays Router handler
- **WHEN** Controller records a valid `done` receipt for a registered
  Router-owned state loader such as `load_resume_state`
- **THEN** Router MUST apply the registered Router action handler for that
  action type before marking the action reconciled
- **AND** Router MUST mark the stateful action reconciled only after the
  declared Router-owned postcondition flag is satisfied

#### Scenario: Unregistered state loader receipt remains unsupported
- **WHEN** Controller records a valid `done` receipt for a stateful loader
  action that writes Router-owned state but is not registered as replayable
- **THEN** Router MUST NOT treat the receipt as proof of the postcondition
- **AND** Router MUST route the action through the existing unsupported or
  missing-postcondition blocker path

### Requirement: Stateful receipt audits include Router-owned state replay
FlowGuard source audits SHALL reject Router-owned state loader actions that
write Router-owned flags without a corresponding registered replay path.

#### Scenario: State loader writes Router flag without replay registration
- **WHEN** a `load_*_state` action handler writes a Router-owned flag
- **AND** that action type is absent from the Router-owned state replay
  registry
- **THEN** the focused Controller receipt FlowGuard check MUST fail with a
  missing replay registration finding

#### Scenario: State loader replay registration is present
- **WHEN** a `load_*_state` action handler writes a Router-owned flag
- **AND** that action type is present in the Router-owned state replay registry
- **THEN** the focused Controller receipt FlowGuard source audit MUST accept
  the state loader replay contract
