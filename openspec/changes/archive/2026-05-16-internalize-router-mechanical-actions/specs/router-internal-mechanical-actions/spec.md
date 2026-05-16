## ADDED Requirements

### Requirement: Router consumes only local mechanical actions internally

FlowPilot SHALL classify local Router bookkeeping actions before writing a
Controller action row. Actions classified as Router-internal SHALL be completed
by Router with Router-owned evidence and SHALL NOT be written as Controller
work rows.

#### Scenario: Local check bypasses Controller row
- **WHEN** the next action is a Router-owned local ledger or manifest check
- **THEN** Router SHALL record local evidence for the check
- **AND** Router SHALL NOT create a Controller action row for that check

#### Scenario: Internal proof writer bypasses Controller row
- **WHEN** the next action is a Router-owned local proof writer and all
  prerequisites are satisfied
- **THEN** Router SHALL write the proof and update Router state
- **AND** Router SHALL NOT require Controller to apply the proof writer

### Requirement: Controller work packages remain Controller-visible

FlowPilot SHALL keep host-boundary, role-interaction, system-card relay, and
formal packet/result handoff actions as Controller work packages. Router SHALL
NOT internally complete these actions merely because it can read or prepare
their local metadata.

#### Scenario: Host-boundary action stays visible
- **WHEN** the next action requires host automation, role spawn, or role
  recovery
- **THEN** Router SHALL write or preserve a Controller work row
- **AND** Router SHALL NOT mark the action done without host/Controller proof

#### Scenario: Role-facing delivery stays visible
- **WHEN** the next action delivers a system card, work packet, result envelope,
  or other role-facing message
- **THEN** Router SHALL preserve the Controller-controlled work-package path
- **AND** Router SHALL NOT bypass Controller to contact the target role

### Requirement: Router-internal work is idempotent and evidence-backed

FlowPilot SHALL make Router-internal work idempotent. Repeated Router ticks or
foreground re-entry SHALL NOT duplicate local side effects, repeat Controller
rows, or convert a local failure into a done receipt.

#### Scenario: Repeated internal check is stable
- **WHEN** Router consumes the same local check across repeated ticks
- **THEN** the check SHALL have one current Router evidence record
- **AND** no duplicate Controller rows SHALL be created

#### Scenario: Internal failure blocks instead of succeeding
- **WHEN** Router-internal work cannot prove its postcondition
- **THEN** Router SHALL leave an explicit wait or blocker record
- **AND** Router SHALL NOT mark the action as done

### Requirement: Startup user intake is Router-owned until PM ACK release

FlowPilot SHALL create startup `user_intake` as Router-owned startup material.
Controller SHALL NOT be the temporary holder or delivery source for the startup
packet. After the PM system-card bundle ACK is mechanically settled, Router
SHALL release the startup packet to PM exactly once and record the release in
the packet ledger.

#### Scenario: Startup intake begins with Router
- **WHEN** deterministic startup creates the `user_intake` packet
- **THEN** the packet ledger SHALL record Router as the active holder
- **AND** the packet SHALL remain sealed from Controller
- **AND** Router SHALL record that PM is the eventual target role

#### Scenario: PM bundle ACK releases startup intake
- **WHEN** the PM system-card bundle ACK is present and valid
- **THEN** Router SHALL normalize the ACK to a resolved return
- **AND** Router SHALL reconcile the matching wait/check Controller and
  scheduler rows
- **AND** Router SHALL release the Router-owned `user_intake` packet to PM
  without creating a `deliver_mail` Controller work row

#### Scenario: Repeated ACK settlement is stable
- **WHEN** Router runs the return settlement pass again after startup
  `user_intake` has already been released
- **THEN** no duplicate mail ledger row, release history entry, Controller row,
  or holder transition SHALL be created

### Requirement: Body and display boundaries are preserved

FlowPilot SHALL preserve sealed-body and user-display boundaries when moving
local work into Router. Router-internal actions SHALL NOT read sealed bodies,
and local display projection SHALL NOT count as user-dialog display
confirmation.

#### Scenario: Sealed body remains unread
- **WHEN** Router consumes a local mechanical action
- **THEN** Router SHALL use only ledgers, envelopes, hashes, and allowed state
- **AND** Router SHALL NOT read sealed packet, result, report, or user-intake
  bodies

#### Scenario: Display projection is not user confirmation
- **WHEN** Router writes display projection files or route snapshots
- **THEN** Router SHALL record only local projection evidence
- **AND** user-dialog display confirmation SHALL remain a separate Controller,
  host, or user boundary
