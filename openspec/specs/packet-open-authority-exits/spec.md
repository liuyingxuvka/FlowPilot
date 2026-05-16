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
