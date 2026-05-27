## ADDED Requirements

### Requirement: Material packet reissue commits one current generation
FlowPilot SHALL commit material-scan `packet_reissue` repair transactions through the existing repair transaction path as one current material generation across material index, active packet batch, packet ledger projection, and repair transaction metadata.

#### Scenario: Packet reissue supersedes old generation
- **WHEN** PM commits a `packet_reissue` repair transaction for material scan dispatch
- **THEN** Router MUST write a current `packet_generation_id` on the material index and every new material packet record
- **AND** Router MUST supersede prior material-scan packet records so they cannot satisfy current material-scan waits
- **AND** Router MUST update the active material-scan packet batch to reference only current-generation packet ids

#### Scenario: Recheck success belongs to current generation
- **WHEN** Router finalizes a successful material-scan repair recheck
- **THEN** the repair transaction outcome MUST reference the current `packet_generation_id`
- **AND** Router MUST NOT complete the repair transaction from an event or artifact that references a superseded material generation

### Requirement: Operation replay synthesizes fresh Controller work
FlowPilot SHALL use `operation_replay` only to synthesize a fresh Controller action from replay intent and current run state.

#### Scenario: Replayed operation has fresh identity
- **WHEN** Router queues an `operation_replay` action from a recorded Controller action
- **THEN** the new Controller action MUST have its own action id and scheduler idempotency key
- **AND** the old action id may appear only as audit metadata such as `replay_of_controller_action_id`

#### Scenario: Material operation replay uses current generation
- **WHEN** the replayed operation touches material-scan packet or result relay state
- **THEN** Router MUST derive allowed reads, allowed writes, packet ids, and batch identity from the current material generation
- **AND** Router MUST reject the replay if it cannot prove the operation targets the current generation.
