## ADDED Requirements

### Requirement: Blocker Classes Have Fixed Handling Routes

FlowPilot SHALL map every supported `blocker_class` to one fixed
`next_action`. That mapping SHALL select the next handling route, not
preselect PM's repair branch. Substantive PM-owned blockers SHALL route to the
current PM repair-decision packet, where PM chooses one finite structured
repair decision. PM repair SHALL consume the blocker context and repair packet
contract instead of freeform role repair prose.

#### Scenario: FlowGuard model blocker reaches PM
- **WHEN** FlowGuard submits `flowguard_model_block`
- **THEN** the fixed next action SHALL route to the PM repair-decision packet
  with the FlowGuard report context

#### Scenario: Parent composition blocker reaches PM
- **WHEN** parent replay submits `parent_composition_block`
- **THEN** the fixed next action SHALL route to the PM repair-decision packet
  with parent/child composition context, without preselecting PM's repair
  branch

### Requirement: PM Repair Uses Branch-Specific Payloads Only

PM repair decisions SHALL include only common repair fields plus the payload
for the chosen branch. Runtime SHALL reject unrelated branch payloads in a
repair packet.

#### Scenario: Terminal supplemental repair branch
- **WHEN** PM continues repair for a terminal closure blocker
- **THEN** the chosen continuing PM repair branch SHALL include the current
  `supplemental_repair_contract`, and unrelated branch payload fields SHALL be
  invalid in that packet

### Requirement: Repair Packets Carry Required Current Evidence Context

Each fixed blocker handling route SHALL define the required current source
context that the PM repair decision or repair packet carries. The required
context SHALL include the
blocking report id, opened-body receipt id where a sealed body informed the
repair, target packet/result/node ids, required evidence refs or missing
evidence kinds, owner role, and return gate.

#### Scenario: FlowGuard model blocker repair
- **WHEN** PM repairs a `flowguard_model_block`
- **THEN** the repair packet SHALL carry the FlowGuard result id, FlowGuard
  evidence path, opened-body receipt for the FlowGuard report, PM absorption
  decision, selected repair target, and return gate

#### Scenario: Waiver required repair
- **WHEN** PM chooses `waive_with_authority`
- **THEN** the PM repair decision SHALL carry the blocker id, subject ids,
  requested waiver scope, authority reference, reason, affected acceptance item
  ids, and return gate

### Requirement: Repeated Repairs Preserve Repair Lineage

Every repeated repair attempt SHALL carry the previous repair packet context
forward. A repeated repair packet SHALL include the original blocker id, prior
repair packet id, prior repair result id, prior evidence refs, failed recheck
report id, reason the prior attempt did not close, current blocking report id,
new repair payload, and return gate.

#### Scenario: Repeated repair includes prior attempt
- **WHEN** PM opens a second repair for the same blocker lineage
- **THEN** Runtime SHALL require the second repair packet to include prior
  repair ids, prior evidence refs, failed recheck id, and the new repair delta

#### Scenario: Repeated repair drops lineage
- **WHEN** PM opens a repeated repair without prior repair context
- **THEN** Runtime SHALL reject the packet instead of treating the new repair
  as a fresh unrelated blocker
