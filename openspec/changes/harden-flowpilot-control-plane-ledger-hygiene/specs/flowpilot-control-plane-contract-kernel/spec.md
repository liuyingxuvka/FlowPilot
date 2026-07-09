## ADDED Requirements

### Requirement: Accepted result pointers only reference formally accepted results
FlowPilot SHALL treat `packet.accepted_result_id` as valid only when it points
to an existing result whose formal ledger state is accepted, whose
`accepted` flag is true, and whose formal review and system validation evidence
do not contradict acceptance.

#### Scenario: Review-blocked result invalidates accepted pointer
- **WHEN** a packet has `accepted_result_id` set to a result whose
  `status` is `review_blocked`
- **THEN** runtime MUST treat the packet ledger as mechanically dirty
- **AND** closure, terminal return, assignment repair, route acceptance, and
  backward replay evidence MUST NOT count that pointer as accepted evidence

#### Scenario: Missing result invalidates accepted pointer
- **WHEN** a packet has `accepted_result_id` set to a result id not present in
  the ledger
- **THEN** runtime MUST block the consumer that attempted to use the pointer
- **AND** runtime MUST NOT silently clear, replace, or infer another accepted
  result

### Requirement: Assignment repair cannot resurrect dirty accepted packets
FlowPilot SHALL let accepted-packet assignment repair repair only assignment or
lease metadata for a packet whose accepted result pointer is still formally
valid.

#### Scenario: Assignment repair sees review-blocked accepted result
- **WHEN** `repair_accepted_packet_assignment` is asked to repair a packet
  whose `accepted_result_id` points to a `review_blocked` result
- **THEN** runtime MUST reject the repair as a control-plane invariant failure
- **AND** runtime MUST NOT set the packet status back to `accepted`

### Requirement: PM FlowGuard absorption waits for review before acceptance
FlowPilot SHALL NOT write `packet.accepted_result_id` for
`pm_flowguard_acceptance` results whose PM body only says `decision=accept`
until the existing Reviewer and system validation gates have accepted that
result.

#### Scenario: PM absorption submits accept decision
- **WHEN** PM submits a mechanically valid `pm_flowguard_acceptance` result
  with `decision=accept`
- **THEN** runtime MUST record the result and issue the required Reviewer
  packet
- **AND** runtime MUST leave the PM FlowGuard acceptance packet without a
  formal `accepted_result_id` until the formal acceptance path commits it
