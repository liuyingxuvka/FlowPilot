## MODIFIED Requirements

### Requirement: Busy recipient blocks new independent dispatch

Router SHALL NOT expose a new independent dispatch to a target role while that
same role still owns unfinished prior work in the current run.

#### Scenario: Prior packet still held by same role

- **GIVEN** the packet ledger shows `worker_a` still holds an unfinished packet
- **WHEN** Router is about to expose another independent packet relay to
  `worker_a`
- **THEN** Router does not expose the new relay action
- **AND** Router exposes or preserves a wait for the prior unfinished packet.

#### Scenario: Prior ACK still missing

- **GIVEN** the pending return ledger has an unresolved required ACK for
  `human_like_reviewer`
- **WHEN** Router is about to expose a formal work packet to
  `human_like_reviewer`
- **THEN** Router exposes the ACK wait instead of the new work packet.

#### Scenario: Returned role-work result frees original worker

- **GIVEN** `worker_b` has returned its PM role-work result
- **AND** PM has not yet absorbed, cancelled, or superseded that result
- **WHEN** Router is about to expose a new worker packet to `worker_b`
- **THEN** the prior returned result does not by itself make `worker_b` busy
- **AND** PM remains the busy role for the pending disposition.

#### Scenario: ACK-only stale passive wait does not keep role busy

- **GIVEN** a Controller passive wait row watches an ACK-only system-card return
- **AND** the matching return ledger evidence is already resolved
- **WHEN** Router evaluates a later independent dispatch to the same role
- **THEN** Router reconciles the stale ACK wait through existing action-ledger and scheduler-row paths
- **AND** the stale ACK wait alone does not keep the role busy.

#### Scenario: Output-bearing card ACK does not clear work busy

- **GIVEN** a role ACKed a system card classified as `output_bearing_work_package`
- **AND** the card's required report, result, decision, or packet-spec event is not recorded
- **WHEN** Router evaluates a later independent dispatch to the same role
- **THEN** Router still treats the role as busy for the unfinished output-bearing work.

#### Scenario: Output-bearing report clears work busy

- **GIVEN** a role had an output-bearing work package wait
- **AND** the matching report, result, decision, or packet-spec event has been recorded
- **WHEN** Router evaluates a later independent dispatch to the same role
- **THEN** Router reconciles the satisfied wait rows and does not keep the role busy from that completed work.
