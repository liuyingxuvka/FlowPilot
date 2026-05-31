## MODIFIED Requirements

### Requirement: New Entrypoint End-To-End Closure

The new FlowPilot SHALL be able to progress from startup intake to final
backward closure through current-run packet, FlowGuard, review, and validation
evidence using the current lease, ACK, and result submission protocol.

#### Scenario: Rehearsal end-to-end run

- **WHEN** a deterministic fake-host rehearsal supplies a valid result,
  targeted FlowGuard evidence, independent review, and validation evidence
- **THEN** final closure MUST complete
- **AND** the public status MUST still hide sealed bodies
- **AND** no `controller_relay` field or Controller relay signature may be
  required for packet completion.

### Requirement: Current Work-Packet Protocol

Current FlowPilot work packets SHALL use dynamic role leases, ACK, and matching
result submission as the authority path.

#### Scenario: Assigned role completes a packet

- **WHEN** Router exposes a `lease_agent` next action for a packet
- **AND** the host records `flowpilot_new.py lease-agent`
- **AND** the assigned role records `flowpilot_new.py ack`
- **AND** the matching lease records `flowpilot_new.py submit-result`
- **THEN** the packet completion MAY advance through current runtime checks
- **AND** the runtime MUST NOT require or persist a `controller_relay` field.

#### Scenario: A role waits for Controller relay

- **WHEN** a current packet has a valid current-run lease assignment and ACK
- **THEN** waiting for an extra Controller relay signature MUST be treated as an
  obsolete protocol expectation
- **AND** role cards MUST direct the role back to the current lease/ACK/result
  path.
