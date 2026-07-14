## MODIFIED Requirements

### Requirement: PM inability uses existing PM exits

FlowPilot SHALL route PM inability to proceed through existing PM repair or stop contracts, not through a generic blocker addressed back to PM.

#### Scenario: PM needs startup repair

- **WHEN** PM cannot safely complete startup intake or activation because the delivered startup evidence requires a legal repair target
- **THEN** PM submits pm_startup_repair_request so Router records pm_requests_startup_repair.

#### Scenario: PM reaches no legal startup repair path

- **WHEN** PM cannot safely continue and no existing role, system event, packet, or contract can legally carry the repair
- **THEN** PM submits pm_startup_protocol_dead_end so Router records pm_declares_startup_protocol_dead_end.

#### Scenario: PM receives Router control blocker

- **WHEN** Router delivers a control blocker for PM disposition
- **THEN** PM uses the existing pm_control_blocker_repair_decision contract and selects one current supported plan kind: operation_replay, controller_repair_work_packet, role_reissue, router_internal_reconcile, await_existing_event, route_mutation, or terminal_stop.
- **AND** PM MUST NOT submit retired packet_reissue or replacement-packet fields.

### Requirement: Packet result author evidence remains replayable
FlowPilot SHALL require packet result authority checks to preserve replayable author identity for current research, current-node, PM role-work, review, and FlowGuard result families.

#### Scenario: Result author matches current role binding
- **WHEN** Router accepts a current packet result for its declared next recipient
- **THEN** the result envelope or packet ledger evidence MUST prove the completed role and replayable agent identity for the current packet holder
- **AND** Router MUST record that authority without writing false success fields when the identity is unknown.

#### Scenario: Role-name agent id is repaired through the current result path
- **WHEN** a current result uses a role key where an agent id is required
- **THEN** Router MUST reject that result before it satisfies packet result authority
- **AND** the addressed role MUST resubmit through the existing current packet/result path with the correct active-holder identity.

### Requirement: PM package disposition is formal packet-release evidence
FlowPilot SHALL require registry-backed PM package disposition evidence before research, PM role-work, or current-node packet results can be released to Reviewer gates.

#### Scenario: Reviewer release waits for formal PM disposition
- **WHEN** Worker packet results have returned to PM
- **THEN** Router MUST NOT release a Reviewer formal gate package until PM records a registry-backed package result disposition.

#### Scenario: Packet evidence cannot bypass PM disposition contract
- **WHEN** packet ledger evidence exists but the PM disposition is missing, manually shaped, or not bound to the expected contract
- **THEN** Router MUST keep Reviewer release blocked and report the missing formal PM disposition boundary.
