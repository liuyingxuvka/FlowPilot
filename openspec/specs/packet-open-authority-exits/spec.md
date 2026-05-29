# packet-open-authority-exits Specification

## Purpose
TBD - created by archiving change harden-packet-open-authority-exits. Update Purpose after archive.
## Requirements
### Requirement: Verified packet open authorizes addressed-role work
FlowPilot SHALL treat a successful `open-packet` runtime session as sufficient authority for the addressed role to work the opened packet inside its role and packet boundary.

#### Scenario: PM opens startup intake packet
- **GIVEN** Router has released a `user_intake` packet to `project_manager`
- **WHEN** PM opens it through `flowpilot_runtime.py open-packet` and the runtime verifies target role, relay or startup release, and body hash
- **THEN** the runtime records that the successful open authorizes PM to work the packet
- **AND** PM MUST NOT wait for an additional corrected Controller relay before deciding or returning a formal existing PM output.

#### Scenario: Ordinary role opens work packet
- **GIVEN** Router has relayed a PM-authored work packet to a worker, reviewer, or officer
- **WHEN** the addressed role opens it through the packet runtime and relay/hash checks pass
- **THEN** the role has authority to work only that packet
- **AND** the role MUST submit the expected result or an existing formal blocker/PM-suggestion output instead of waiting in chat.
- **AND** direct defect repair is allowed only when the role and packet grant bounded execution/write authority.

### Requirement: PM inability uses existing PM exits

FlowPilot SHALL route PM inability to proceed through existing PM repair or stop contracts, not through a generic blocker addressed back to PM.

#### Scenario: PM needs startup repair

- **WHEN** PM cannot safely complete startup intake or activation because the delivered startup evidence requires a legal repair target
- **THEN** PM submits `pm_startup_repair_request` so Router records `pm_requests_startup_repair`.

#### Scenario: PM reaches no legal startup repair path

- **WHEN** PM cannot safely continue and no existing role, system event, packet, or contract can legally carry the repair
- **THEN** PM submits `pm_startup_protocol_dead_end` so Router records `pm_declares_startup_protocol_dead_end`.

#### Scenario: PM receives Router control blocker

- **WHEN** Router delivers a control blocker for PM disposition
- **THEN** PM uses the existing `pm_control_blocker_repair_decision` contract and selects an allowed existing plan kind such as `packet_reissue`, `role_reissue`, `router_internal_reconcile`, `route_mutation`, or `terminal_stop`.

### Requirement: Ordinary role blockers remain decision inputs

FlowPilot SHALL preserve ordinary role blockers as formal decision inputs for PM or Router, while forbidding silent no-output waits.

#### Scenario: Worker cannot complete opened packet

- **WHEN** a worker successfully opens a packet but finds a true packet-scoped blocker
- **THEN** the worker returns the existing formal blocker or packet result-with-blocker required by the current packet contract
- **AND** PM/Router owns the repair or disposition decision.

#### Scenario: Reviewer or officer cannot complete opened packet

- **WHEN** a reviewer or officer successfully opens an authorized packet but cannot complete the assigned check
- **THEN** the role returns the existing formal blocker or PM-suggestion output required by the current card/packet contract
- **AND** the role MUST NOT wait for extra prompts or decide PM-owned route repair itself.

### Requirement: Packet result author evidence remains replayable
FlowPilot SHALL require packet result authority checks to preserve replayable author identity for current-generation material-scan results.

#### Scenario: Result author matches current role binding
- **WHEN** Router accepts material-scan worker results for PM disposition
- **THEN** the result envelope or packet ledger evidence MUST prove the completed role and replayable agent identity for the current packet holder
- **AND** Router MUST record that authority without writing false success fields when the identity is unknown

#### Scenario: Role-name agent id is repaired through existing reissue path
- **WHEN** a material-scan result uses a role key where an agent id is required
- **THEN** Router MUST route the correction through the existing control-plane reissue or packet repair path
- **AND** Router MUST NOT let that result satisfy current-generation packet result authority until corrected.

### Requirement: PM package disposition is formal packet-release evidence
FlowPilot SHALL require registry-backed PM package disposition evidence before material, research, or current-node packet results can be released to reviewer gates.

#### Scenario: Reviewer release waits for formal PM disposition
- **WHEN** worker packet results have returned to PM
- **THEN** Router MUST NOT release a reviewer formal gate package until PM records a registry-backed package result disposition

#### Scenario: Packet evidence cannot bypass PM disposition contract
- **WHEN** packet ledger evidence exists but the PM disposition is missing, manually shaped, or not bound to the expected contract
- **THEN** Router MUST keep reviewer release blocked and report the missing formal PM disposition boundary

### Requirement: Path-only packet handoff never authorizes packet open
FlowPilot SHALL reject packet open attempts that rely only on Controller chat text, displayed paths, or a Controller receipt when the envelope lacks a valid Controller relay signature.

#### Scenario: Worker receives path without relay signature
- **WHEN** Worker opens an addressed packet through `flowpilot_runtime.py open-packet` and the envelope lacks `controller_relay`
- **THEN** the runtime MUST reject the open with a missing Controller relay error
- **AND** the runtime MUST NOT write a successful packet-open receipt

#### Scenario: Worker opens after runtime relay
- **WHEN** Controller has relayed the addressed packet through the runtime relay command and the packet body hash still matches the envelope
- **THEN** Worker `open-packet` MUST accept the packet and write the normal packet-open session receipt

### Requirement: Neutral relay names do not expand body access authority
FlowPilot SHALL allow recipient-neutral relay helper names while preserving the addressed-role body access rules. A renamed relay check MUST NOT let PM, Reviewer, Controller, Worker, or Officer open a body outside the role and stage authorized by the packet or result contract.

#### Scenario: PM opens only PM-bound result
- **WHEN** a result is relayed to `project_manager` for disposition
- **THEN** PM may open the result body only through the packet runtime authorization path for that result
- **AND** Reviewer SHALL NOT gain raw result body access from the PM-bound relay.

#### Scenario: Reviewer-named relay does not grant current authority
- **WHEN** a PM-bound result is checked through any reviewer-named relay surface
- **THEN** current authority still comes only from the recipient, ledger, hash, and body-boundary rules
- **AND** the reviewer-named surface SHALL NOT imply Reviewer approval, Reviewer body access, or PM disposition completion.
