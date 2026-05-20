## ADDED Requirements

### Requirement: Controller action identity is one Router obligation

FlowPilot SHALL identify each Controller-visible action by the Router obligation it represents.

#### Scenario: Two control blockers have the same target role
- **WHEN** two `handle_control_blocker` actions have different `blocker_id` or `blocker_artifact_path`
- **THEN** Router MUST produce different idempotency keys and Controller action IDs
- **AND** a scheduler row for one blocker MUST NOT be reused for the other blocker

#### Scenario: Existing action row has a different identity
- **WHEN** a Controller action file already exists for an action ID
- **AND** the stored action identity differs from the new action identity
- **THEN** Router MUST NOT overwrite the stored action payload with the new action
- **AND** Router MUST surface the identity collision as a repairable control-plane error

### Requirement: Stateful Controller receipts apply Router-visible effects

FlowPilot SHALL treat `done` receipts for stateful Controller work as incomplete until Router can apply or reclaim the declared postcondition.

#### Scenario: Controller delivers a control blocker
- **WHEN** Controller records a `done` receipt for `handle_control_blocker`
- **THEN** Router MUST update the control blocker artifact delivery fields
- **AND** Router MUST update the control blocker delivery ledger
- **AND** Router MUST set the matching Router-visible delivery postcondition

#### Scenario: Stateful receipt lacks evidence
- **WHEN** Controller records `done` for a stateful action
- **AND** Router cannot apply or reclaim the declared postcondition
- **THEN** Router MUST NOT reconcile the scheduler row as complete
- **AND** Router MUST schedule repair or emit a control blocker according to the existing receipt-repair policy
