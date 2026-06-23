## ADDED Requirements

### Requirement: Checker packets reject same-agent target result checks
FlowPilot SHALL prevent an agent that produced a target result from checking
that same result through Reviewer review packets or FlowGuard post-result check
packets.

#### Scenario: Reviewer cannot review own target result
- **WHEN** a `review` packet targets a result whose `producer_agent_id` equals
  the candidate Reviewer agent id
- **THEN** runtime role assignment MUST reject or replace that Reviewer
  assignment
- **AND** result submission through an already-open same-agent Reviewer lease
  MUST be mechanically blocked.

#### Scenario: FlowGuard operator cannot check own target result
- **WHEN** a `flowguard_check` packet targets a result whose
  `producer_agent_id` equals the candidate FlowGuard operator agent id
- **THEN** runtime role assignment MUST reject or replace that FlowGuard
  operator assignment
- **AND** result submission through an already-open same-agent FlowGuard
  operator lease MUST be mechanically blocked.

#### Scenario: Same role can check a different producer result
- **WHEN** a Reviewer or FlowGuard operator previously checked one packet
- **AND** a later checker packet targets a result produced by a different agent
- **THEN** FlowPilot MAY reuse that Reviewer or FlowGuard operator
- **AND** the self-check rule MUST NOT force a new agent solely because the
  responsibility name is reused.

### Requirement: Parent backward replay closes after FlowGuard pass without a second Reviewer packet
FlowPilot SHALL treat a passing FlowGuard post-result check for a
`parent_backward_replay` task result as the last checker gate before parent
replay closure and PM disposition.

#### Scenario: Parent replay passes FlowGuard and closes parent replay
- **WHEN** a `task` packet with `route_scope=parent_backward_replay` has a
  submitted result
- **AND** its required `flowguard_check` packet passes for that result
- **THEN** FlowPilot MUST accept the parent backward replay result
- **AND** FlowPilot MUST record parent backward replay closure for the target
  parent node
- **AND** FlowPilot MUST open the existing PM disposition path for that parent
  replay.

#### Scenario: Parent replay does not open second Reviewer packet after FlowGuard pass
- **WHEN** the passing `flowguard_check` subject is a
  `parent_backward_replay` task result
- **THEN** FlowPilot MUST NOT create a follow-up `review` packet for that same
  parent backward replay result.

#### Scenario: Ordinary task results keep the existing review chain
- **WHEN** the passing `flowguard_check` subject is not a
  `parent_backward_replay` task result
- **THEN** FlowPilot MUST continue to release the ordinary Reviewer packet
  required by the existing packet review flow.
