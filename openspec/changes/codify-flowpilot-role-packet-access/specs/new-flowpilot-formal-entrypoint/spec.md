## MODIFIED Requirements

### Requirement: Current Work-Packet Protocol

Current FlowPilot work packets SHALL use dynamic role leases, ACK, formal packet open, and matching result submission as the authority path.

#### Scenario: Assigned role completes a packet

- **WHEN** Router exposes a `lease_agent` next action for a packet
- **AND** the host records `flowpilot_new.py lease-agent`
- **AND** the runtime returns generated role handoff text
- **AND** the assigned role records `flowpilot_new.py ack`
- **AND** the assigned role opens the packet with `flowpilot_new.py open-packet`
- **AND** the matching lease records `flowpilot_new.py submit-result`
- **THEN** the packet completion MAY advance through current runtime checks
- **AND** the runtime MUST NOT require or persist a `controller_relay` field.

#### Scenario: Role waits for ACK body exposure

- **WHEN** a current packet has a valid current-run lease assignment and ACK
- **THEN** waiting for body text in the ACK response MUST be treated as an obsolete or unsafe protocol expectation
- **AND** the generated handoff MUST direct the role to `open-packet`.
