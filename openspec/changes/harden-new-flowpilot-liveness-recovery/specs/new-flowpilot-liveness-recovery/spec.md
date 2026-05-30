## ADDED Requirements

### Requirement: Packet waits use a liveness recovery ladder
The new FlowPilot runtime SHALL classify packet waits through a liveness recovery ladder before replacing a live responsibility lease.

#### Scenario: Result wait remains patrol before threshold
- **WHEN** a packet has an active acknowledged lease, no accepted result, and no liveness threshold is due
- **THEN** the foreground duty MUST remain `wait_patrol`
- **AND** the runtime MUST NOT create or assign a replacement lease for that packet.

#### Scenario: Result wait reaches liveness check before replacement
- **WHEN** a result/report wait reaches the configured liveness-check threshold
- **THEN** the runtime MUST expose a liveness-check or reminder duty before replacement
- **AND** replacement MUST remain blocked until current no-output, inactive, missing, cancelled, or timeout evidence exists.

#### Scenario: Progress keeps current lease active
- **WHEN** the active lease records current-run progress for its assigned packet
- **THEN** the runtime MUST treat the wait as still live for the current patrol cycle
- **AND** progress MUST NOT satisfy the packet result obligation.

### Requirement: Accepted packets cannot be reassigned
The new FlowPilot runtime SHALL reject assignment, ACK, or replacement actions that would regress a packet with an accepted result.

#### Scenario: Assign accepted packet is rejected
- **WHEN** a packet has `accepted_result_id`
- **THEN** `lease-agent` MUST reject assigning a new lease to that packet
- **AND** the packet status MUST remain `accepted`.

#### Scenario: ACK cannot reopen accepted packet
- **WHEN** a packet has `accepted_result_id`
- **AND** a later ACK is submitted against any lease
- **THEN** the runtime MUST reject the ACK or leave the packet accepted
- **AND** it MUST NOT change the packet status to `acknowledged`.

### Requirement: Accepted-result replacement race is repaired deterministically
The new FlowPilot runtime SHALL resolve a race where an original result was accepted before or during replacement by preserving the accepted result and closing the mistaken replacement lease.

#### Scenario: Original result wins race
- **WHEN** packet `P` has an accepted result from original lease `L1`
- **AND** replacement lease `L2` is active on the same packet
- **THEN** repair MUST keep `P.accepted_result_id`
- **AND** repair MUST close or supersede `L2` with an auditable reason
- **AND** the next action MUST derive from the packet after `P`, not wait for `L2`.

### Requirement: Public progress command records liveness only
The new FlowPilot entrypoint SHALL expose a progress command that records current-run active lease progress without completing the packet.

#### Scenario: Progress command updates guard but not packet completion
- **WHEN** `progress --lease-id L --packet-id P --status S` is called for the active lease assigned to packet `P`
- **THEN** the lease progress count MUST increase
- **AND** status output MUST still show the packet waiting for a result unless a result is submitted.

#### Scenario: Progress command rejects wrong packet
- **WHEN** progress is submitted for a lease that is not assigned to the packet
- **THEN** the runtime MUST reject the command
- **AND** no progress count MUST be written.
