## ADDED Requirements

### Requirement: Derived FlowGuard reissue packets preserve material reads
FlowPilot SHALL preserve required authorized result reads when runtime derives a current-contract FlowGuard reissue packet from a blocked FlowGuard check packet that still targets the same subject packet and result.

#### Scenario: Reissue inherits required subject result body
- **WHEN** a `flowguard_check` packet has `authorized_result_reads` with `required_before_submit: true`
- **AND** its submitted result is mechanically rejected by the current packet/result contract
- **THEN** the runtime-generated reissue packet MUST include the same required result ids in `envelope.authorized_result_reads`
- **AND** `current_handoff_contract.input_material_manifest.required_authorized_reads_before_submit` MUST include those result ids
- **AND** `current_handoff_contract.input_material_manifest.required_authorized_read_count` MUST match the inherited required read count.

#### Scenario: Reissue without inherited read blocks broad pass
- **WHEN** a derived FlowGuard reissue packet keeps the same `subject_id`, `target_result_id`, `repair_blocker_id`, and packet kind as the blocked packet
- **AND** the blocked packet had required authorized result reads
- **THEN** a reissue packet with an empty required-read manifest is a current-contract failure
- **AND** it MUST be covered by FlowGuard model and runtime regression evidence before the repair class is claimed green.

### Requirement: Derived packet submit requires inherited body open receipts
FlowPilot SHALL reject a derived packet result when any inherited required authorized result body has not been opened by the assigned role in the current lease.

#### Scenario: Reissued FlowGuard result submitted before inherited body is opened
- **WHEN** a FlowGuard operator receives a current-contract reissue packet with inherited required authorized result reads
- **AND** the operator opens only the packet body
- **THEN** `submit-result` MUST reject or block the result with the missing inherited result body ids
- **AND** the reissue packet MUST remain unaccepted.

#### Scenario: Reissued FlowGuard result passes after inherited body is opened
- **WHEN** the operator opens the reissue packet body and every inherited required authorized result body
- **AND** the result satisfies the current FlowGuard semantic recheck contract
- **THEN** `submit-result` MAY accept the FlowGuard reissue result and continue to the next current runtime gate.
