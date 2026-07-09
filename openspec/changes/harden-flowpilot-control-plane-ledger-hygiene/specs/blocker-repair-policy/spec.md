## ADDED Requirements

### Requirement: Repair-chain derived packets preserve blocker identity
FlowPilot SHALL carry the existing repair blocker identity through every
runtime-derived packet in the same repair family, using the existing
`repair_blocker_id`, envelope repair identity, and body blocker fields.

#### Scenario: PM FlowGuard acceptance derives from repair gate
- **WHEN** a PM decision gate has `blocker_id=blocker-N`
- **AND** runtime issues the gate's `pm_flowguard_acceptance` packet
- **THEN** the packet and envelope MUST carry `repair_blocker_id=blocker-N`
- **AND** the handoff/body blocker field MUST not be empty or a different
  blocker id

#### Scenario: Review packet derives from PM FlowGuard acceptance
- **WHEN** runtime issues the Reviewer packet for a PM FlowGuard acceptance
  packet that carries `repair_blocker_id=blocker-N`
- **THEN** the Reviewer packet MUST inherit the same `repair_blocker_id`
- **AND** runtime MUST reject same-family attempts that omit or mismatch the
  identity instead of rebinding by guesswork
