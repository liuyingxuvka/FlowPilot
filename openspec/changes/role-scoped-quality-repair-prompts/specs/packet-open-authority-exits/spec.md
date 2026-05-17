## MODIFIED Requirements

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
