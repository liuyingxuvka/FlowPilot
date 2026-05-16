## ADDED Requirements

### Requirement: Router uses one pre-dispatch recipient gate

Router SHALL evaluate role-facing dispatch actions through a single
pre-dispatch recipient gate before exposing them as Controller work.

#### Scenario: Formal work packet checks target role before exposure

- **WHEN** Router is about to expose a formal work-packet relay action to a
  target role
- **THEN** Router evaluates the target role through the pre-dispatch recipient
  gate
- **AND** the action is exposed only when the gate passes.

#### Scenario: System-card bundle remains grouped

- **WHEN** Router builds a same-role system-card bundle
- **THEN** the gate treats the bundle as one grouped delivery
- **AND** it does not reject the bundle merely because multiple cards target
  the same role.

#### Scenario: System card can guide the current active obligation

- **GIVEN** the packet ledger shows `project_manager` holds the active
  `user_intake` packet
- **AND** no prior card ACK or passive wait for `project_manager` is unresolved
- **WHEN** Router is about to expose `pm.material_scan`
- **THEN** the active `user_intake` holder record alone does not block that
  same-obligation instruction card.

#### Scenario: User intake blocks independent PM dispatch until first output

- **GIVEN** Controller has relayed `user_intake` to `project_manager`
- **AND** PM has not yet returned
  `pm_issues_material_and_capability_scan_packets`
- **WHEN** Router is about to expose another independent dispatch to
  `project_manager`
- **THEN** Router exposes or preserves a wait for the `user_intake` first
  output instead of the independent dispatch.

#### Scenario: User intake first output frees PM for later dispatch

- **GIVEN** PM returned `pm_issues_material_and_capability_scan_packets`
- **WHEN** Router evaluates later independent PM dispatches
- **THEN** the old `user_intake` holder record does not by itself keep PM busy.

#### Scenario: System-card work wait blocks follow-up dispatch

- **GIVEN** a system card has been delivered and Router is waiting for
  `project_manager` to return the card's required decision or packet request
- **WHEN** Router is about to expose a new independent dispatch to
  `project_manager`
- **THEN** Router exposes or preserves the active wait instead of the new
  dispatch.

#### Scenario: ACK-only card is prompt material, not a work package

- **GIVEN** Router is about to expose a system card that requires only runtime
  open/read receipt/ACK
- **WHEN** the card has no decision, report, packet, result, blocker, or next
  instruction output obligation
- **THEN** the gate classifies it as an ACK-only prompt/material package
- **AND** it does not count as a new output-bearing work package.

#### Scenario: Output-bearing event card is work context

- **GIVEN** PM already has a pending output obligation such as
  `pm_records_model_miss_triage_decision`
- **WHEN** Router is about to expose an unrelated PM card that asks for another
  decision or artifact
- **THEN** Router waits for the pending PM output instead of exposing the new
  work package.
- **WHEN** Router is about to expose `pm.event.reviewer_blocked` as context for
  that same pending PM decision
- **THEN** the gate may expose it as same-output work context
- **AND** PM still must ACK the event card before submitting the decision.

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

### Requirement: Existing dispatch legality checks remain enforced

The pre-dispatch recipient gate SHALL preserve existing dispatch legality
requirements for target identity, packet legality, sealed body boundaries,
same-batch duplicate role rejection, and active-holder authority.

#### Scenario: Duplicate target in one packet batch

- **WHEN** PM registers a packet batch containing two independent open packets
  for the same target role
- **THEN** Router rejects the batch before relay.

#### Scenario: Illegal packet envelope is still rejected

- **WHEN** a packet envelope has the wrong target role, missing hash identity,
  missing output contract, unsealed body, or Controller-readable body access
- **THEN** Router or packet runtime rejects the dispatch even if the target
  role is otherwise idle.

### Requirement: Blocked dispatch names the wait source

When the gate blocks a dispatch because the recipient is busy, Router SHALL
include controller-visible metadata naming the blocked dispatch, target role,
busy source, and wait reason.

#### Scenario: Busy metadata is visible without sealed bodies

- **WHEN** a candidate dispatch is blocked by an unfinished prior packet
- **THEN** the replacement wait action includes the target role, packet id when
  available, source ledger path, and blocked action type
- **AND** it does not expose sealed packet or result body content.
