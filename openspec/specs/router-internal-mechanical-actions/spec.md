# router-internal-mechanical-actions Specification

## Purpose
TBD - created by archiving change internalize-router-mechanical-actions. Update Purpose after archive.
## Requirements
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

### Requirement: Missing relay evidence is mechanically repairable by Controller
When a packet/result relay receipt is missing runtime relay evidence but the envelope is otherwise valid and relayable, Router SHALL create a Controller-owned mechanical repair/replay path before escalating to PM.

#### Scenario: Missing relay signature has valid envelope
- **WHEN** Router reconciles a relay `done` receipt and finds `packet_dispatch_evidence_missing` only because `controller_relay` is absent from an otherwise relayable envelope
- **THEN** Router MUST issue or preserve Controller work to perform the runtime relay operation
- **AND** Router MUST NOT immediately materialize a PM-handled control blocker for that omission

#### Scenario: Relay repair succeeds
- **WHEN** the Controller mechanical repair writes valid runtime relay evidence for the missing envelope
- **THEN** Router MUST reconcile the original relay postcondition and supersede or resolve the repair row without requiring a PM repair decision

### Requirement: Router materializes ready internal postconditions before role waits
FlowPilot SHALL classify deterministic Router-owned postconditions separately
from role-provided external events and SHALL materialize them before exposing a
passive Controller or role wait.

#### Scenario: Capability evidence inputs are ready
- **WHEN** child-skill manifest review has passed
- **AND** PM has approved the child-skill manifest for route use
- **AND** the capability source artifacts are present and valid
- **AND** `capability_evidence_synced` is not yet recorded
- **THEN** Router MUST write Router-owned capability sync evidence
- **AND** Router MUST sync the matching event/flag
- **AND** Router MUST recompute the next action from the updated state
- **AND** Router MUST NOT create an `await_role_decision` row for
  `capability_evidence_synced`

#### Scenario: Capability evidence inputs are not ready
- **WHEN** the prerequisite flags imply a Router-owned internal postcondition
  is due
- **AND** the source artifacts required to materialize that postcondition are
  absent or invalid
- **THEN** Router MUST expose a local control-plane blocker or repair action
  that names the missing evidence
- **AND** Router MUST NOT represent the missing Router artifact as a Controller
  decision wait

### Requirement: Internal postcondition materialization is idempotent
FlowPilot SHALL make Router-owned internal postcondition materialization safe
across repeated daemon ticks, foreground re-entry, and manual event replay.

#### Scenario: Capability sync evidence already exists
- **WHEN** Router repeats reconciliation after capability sync evidence already
  exists
- **THEN** Router MUST preserve one authoritative sync artifact
- **AND** Router MUST keep the event/flag synced
- **AND** Router MUST NOT create duplicate wait rows or duplicate sync records

### Requirement: Router mechanical proof has a narrow replacement scope
Router-owned proof SHALL replace Reviewer rechecking only for mechanical envelope, ledger, role-target, hash, and Controller body-boundary facts. Reviewer SHALL remain responsible for semantic package review, source sufficiency, result quality, acceptance risk, and independent challenge.

#### Scenario: Reviewer trusts Router-computable checks
- **WHEN** Router has recorded proof for packet target role, envelope hash, result hash, relay ledger state, and Controller sealed-body exclusion
- **THEN** Reviewer cards MAY cite that proof instead of manually rechecking those mechanical facts
- **AND** Reviewer cards MUST still require direct review of the formal package content and task-specific quality risks.

#### Scenario: Router proof cannot approve semantic work
- **WHEN** Router mechanical proof is complete but PM formal package content has not been reviewed
- **THEN** Reviewer SHALL NOT pass the quality, material, research, or node-completion gate from Router proof alone.
