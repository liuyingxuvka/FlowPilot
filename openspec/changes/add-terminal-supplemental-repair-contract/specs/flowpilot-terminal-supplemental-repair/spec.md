## ADDED Requirements

### Requirement: PM Authors Terminal Supplemental Repair Contracts
FlowPilot SHALL preserve the original frozen contract and SHALL require PM to
author a separate terminal supplemental repair contract when terminal Reviewer
gap review finds blocking work required to satisfy the original user goal at
high standard.

#### Scenario: Latent original-goal gap becomes supplemental contract item
- **WHEN** terminal Reviewer reports a blocking gap that is necessary to
  satisfy the original user goal at high standard
- **THEN** PM MUST create a terminal supplemental repair contract with a repair
  item for that gap
- **AND** runtime MUST NOT modify the original frozen contract.

#### Scenario: PM omits required terminal repair item
- **WHEN** terminal Reviewer reports a blocking original-goal gap
- **AND** PM submits a supplemental repair contract without a repair item for
  that gap or an explicit terminal stop
- **THEN** runtime MUST mechanically block the supplemental contract result.

### Requirement: Supplemental Repair Items Project To Repair Nodes
FlowPilot SHALL project every active supplemental repair item to a repair node
or repair subnode before repair execution can begin.

#### Scenario: Repair item has no owner node
- **WHEN** a supplemental repair contract contains an active repair item
- **AND** no current repair node or repair subnode owns that item
- **THEN** FlowGuard route coverage MUST block repair execution.

#### Scenario: Repair node lacks supplemental projection
- **WHEN** PM adds a terminal repair node for supplemental work
- **AND** the node omits `supplemental_contract_id` or `repair_item_ids`
- **THEN** Reviewer node-plan review MUST block the node before Worker
  dispatch.

### Requirement: Supplemental Repair Nodes Reuse Existing Gates
FlowPilot SHALL run supplemental repair nodes through the same current
FlowPilot gates as ordinary repair work.

#### Scenario: Repair node skips process review
- **WHEN** a supplemental repair node is created
- **AND** no current FlowGuard process/reachability report covers the node and
  its repair items
- **THEN** runtime MUST NOT dispatch Worker execution for that node.

#### Scenario: Repair node skips Reviewer plan review
- **WHEN** a supplemental repair node has not passed Reviewer repair-plan or
  node acceptance review
- **THEN** runtime MUST NOT dispatch Worker execution for that node.

### Requirement: Runtime Enforces Three Terminal Repair Rounds
FlowPilot SHALL allow at most three terminal supplemental repair rounds. The
third round is a final attempt and MUST end in clean closure or hard terminal
stop.

#### Scenario: First or second round still has blocking gaps
- **WHEN** terminal closure remains blocked after supplemental repair round one
  or two
- **THEN** runtime MAY request a structured terminal Reviewer gap recheck
- **AND** PM MAY submit the next supplemental repair contract round.

#### Scenario: Third round still has blocking gaps
- **WHEN** terminal closure remains blocked after supplemental repair round
  three
- **THEN** runtime MUST record `repair_rounds_exhausted`
- **AND** runtime MUST NOT dispatch another terminal Reviewer gap review or PM
  supplemental repair contract packet.

#### Scenario: Exhausted state receives new repair request
- **WHEN** terminal supplemental repair status is `exhausted`
- **AND** a new supplemental repair packet or route mutation is requested for
  the same terminal repair sequence
- **THEN** runtime MUST reject the request as terminal.
