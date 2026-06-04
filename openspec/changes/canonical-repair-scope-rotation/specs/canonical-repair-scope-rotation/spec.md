# canonical-repair-scope-rotation Specification

## Requirements

### Requirement: Runtime exposes one current PM repair menu

FlowPilot MUST accept exactly these PM repair decisions:
`repair_current_scope`, `repair_parent_scope`, `redesign_route`,
`waive_with_authority`, and `stop_for_user`.

#### Scenario: PM receives the current menu

- **WHEN** Runtime issues a `pm_repair_decision` packet
- **THEN** the packet body MUST list exactly the five current decisions
- **AND** it MUST require a top-level JSON object containing `decision` and
  `reason`
- **AND** it MUST NOT advertise old decision names.

#### Scenario: Old decision names are rejected

- **WHEN** PM submits `same_node_repair`, `sender_reissue`,
  `collect_more_evidence`, `mutate_route`, or `quarantine_evidence`
- **THEN** Runtime MUST reject the PM result as a repair decision payload
  contract failure
- **AND** Runtime MUST NOT translate the value into a current decision.

### Requirement: Nonterminal repair requires a fresh executable packet

For `repair_current_scope`, `repair_parent_scope`, and `redesign_route`,
Runtime MUST create or identify a fresh current executable packet before the
blocker can enter `repair_packet_open`.

#### Scenario: Fresh packet is missing

- **WHEN** a nonterminal repair decision completes without a nonempty
  `fresh_packet_id`
- **THEN** Runtime MUST raise a control-plane error
- **AND** the blocker MUST NOT be marked `repair_packet_open`.

#### Scenario: Fresh packet is not current and open

- **WHEN** `fresh_packet_id` points to a missing, superseded, quarantined,
  accepted, stale-route, or otherwise noncurrent packet
- **THEN** Runtime MUST reject the repair transition
- **AND** the blocker MUST remain unresolved.

### Requirement: Current-scope repair replaces the current node

`repair_current_scope` MUST supersede the current route node as active
authority, create a replacement repair node, and issue the replacement node's
next required packet.

#### Scenario: Ordinary node repair

- **GIVEN** a blocker on a current route node
- **WHEN** PM chooses `repair_current_scope`
- **THEN** Runtime MUST create a replacement repair node
- **AND** the old node MUST be marked superseded
- **AND** a fresh packet for the replacement node MUST be open
- **AND** the blocker MUST reference that fresh packet.

### Requirement: Parent-scope repair replaces the nearest parent scope

`repair_parent_scope` MUST replace the nearest explicit parent route node and
remove that parent and its descendants from current routing authority.

#### Scenario: Child issue bubbles to parent

- **GIVEN** a blocker on a child route node with an explicit parent
- **WHEN** PM chooses `repair_parent_scope`
- **THEN** Runtime MUST supersede the parent and its descendants
- **AND** Runtime MUST create a replacement parent repair node
- **AND** Runtime MUST issue a fresh executable packet for the replacement
  parent repair node.

#### Scenario: No explicit parent exists

- **GIVEN** a blocker on a flat route node with no explicit parent
- **WHEN** PM chooses `repair_parent_scope`
- **THEN** Runtime MUST reject the decision
- **AND** Runtime MUST NOT guess a parent scope.

### Requirement: Route redesign is gated by a strict route plan

`redesign_route` MUST be treated as a high-risk PM decision. Runtime MUST stage
the effect, require FlowGuard/reviewer approval, and activate only a strict
current route plan.

#### Scenario: PM redesigns route

- **WHEN** PM chooses `redesign_route`
- **THEN** Runtime MUST stage a route-redesign effect
- **AND** FlowGuard and Reviewer MUST inspect the current route plan
- **AND** Runtime MUST activate the new route only after the gate closes.

#### Scenario: Redesign has no route plan

- **WHEN** a route-redesign gate attempts to apply without a strict route plan
- **THEN** Runtime MUST reject activation
- **AND** the old route MUST remain active.

### Requirement: Terminal decisions do not create repair packets

`waive_with_authority` and `stop_for_user` MUST be terminal decisions.

#### Scenario: Authorized waiver

- **WHEN** PM chooses `waive_with_authority` with an authority reference
- **THEN** Runtime MUST mark the blocker waived
- **AND** Runtime MUST NOT create a repair packet.

#### Scenario: Waiver without authority

- **WHEN** PM chooses `waive_with_authority` without an authority reference
- **THEN** Runtime MUST reject the PM result
- **AND** Runtime MUST NOT mark the blocker waived.

#### Scenario: Stop for user

- **WHEN** PM chooses `stop_for_user`
- **THEN** Runtime MUST mark the blocker stopped
- **AND** Runtime MUST NOT create a repair packet.
