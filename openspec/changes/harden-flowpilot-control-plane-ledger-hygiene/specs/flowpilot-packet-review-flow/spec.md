## ADDED Requirements

### Requirement: Review block cannot coexist with accepted packet state
FlowPilot SHALL reject or block any state transition that would leave a packet
formally accepted while the target result is formally review-blocked or
rejected.

#### Scenario: Reviewer blocks a result that packet already marks accepted
- **WHEN** `review_result` receives a block decision for a result currently
  named by the subject packet's `accepted_result_id`
- **THEN** runtime MUST classify the ledger as a control-plane invariant
  failure
- **AND** runtime MUST NOT leave the packet in `accepted` state with that
  result pointer

### Requirement: Final Reviewer packets receive sealed result authorization
FlowPilot SHALL issue final review and backward replay Reviewer packets with
the required sealed result-body reads in `authorized_result_reads`.

#### Scenario: Final route-node reviewer task is issued
- **WHEN** runtime issues a route-node task whose responsibility is Reviewer
  and whose node is a final review, closure audit, or backward replay node
- **THEN** runtime MUST include current route, startup, acceptance, node,
  FlowGuard, review, and validation result-body reads that the Reviewer needs
  to inspect the final claim
- **AND** the packet MUST NOT rely on unauthorized sibling sealed-body access

#### Scenario: Terminal backward replay packet is issued
- **WHEN** runtime issues a terminal backward replay Reviewer packet
- **THEN** runtime MUST include an authorized evidence bundle for the current
  terminal replay scope
- **AND** missing authorized result material MUST be a blocker rather than an
  implicit Reviewer duty to read sealed bodies without authorization
