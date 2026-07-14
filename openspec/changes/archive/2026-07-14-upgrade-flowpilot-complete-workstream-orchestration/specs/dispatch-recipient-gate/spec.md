## MODIFIED Requirements

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
- **WHEN** Router is about to expose `pm.product_architecture`
- **THEN** the active `user_intake` holder record alone does not block that
  same-obligation instruction card.

#### Scenario: User intake blocks independent PM dispatch until first output

- **GIVEN** Controller has relayed `user_intake` to `project_manager`
- **AND** PM has not yet returned `pm_writes_product_function_architecture`
- **WHEN** Router is about to expose another independent dispatch to
  `project_manager`
- **THEN** Router exposes or preserves a wait for the `user_intake` first
  output instead of the independent dispatch.

#### Scenario: User intake first output frees PM for later dispatch

- **GIVEN** PM returned `pm_writes_product_function_architecture`
- **WHEN** Router evaluates later independent PM dispatches
- **THEN** the old `user_intake` holder record does not by itself keep PM busy.

#### Scenario: System-card work wait blocks follow-up dispatch

- **GIVEN** a system card has been delivered and Router is waiting for
  `project_manager` to return the card's required decision or packet request
- **WHEN** Router is about to expose a new independent dispatch to
  `project_manager`
- **THEN** Router exposes or preserves the active wait instead of the new
  dispatch.

#### Scenario: ACK-only card is prompt context, not a work package

- **GIVEN** Router is about to expose a system card that requires only runtime
  open/read receipt/ACK
- **WHEN** the card has no decision, report, packet, result, blocker, or next
  instruction output obligation
- **THEN** the gate classifies it as an ACK-only prompt package
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
