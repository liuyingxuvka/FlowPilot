## ADDED Requirements

### Requirement: Runtime generates role packet handoff

FlowPilot SHALL generate Controller-safe packet handoff text for every current-run role lease instead of relying on Controller to hand-write packet authority instructions.

#### Scenario: Handoff includes the complete current packet path

- **WHEN** Controller records a `flowpilot_new.py lease-agent` assignment for any supported packet responsibility
- **THEN** the runtime response MUST include safe handoff text for that role
- **AND** the handoff MUST include the exact ACK command, exact `open-packet` command, and exact `submit-result` command for the current run, packet, and lease.

#### Scenario: Handoff is safe for Controller to paste

- **WHEN** the runtime renders handoff text
- **THEN** it MUST NOT include sealed packet body text or sealed result body text
- **AND** it MUST state that the role may open only the assigned packet through the runtime command
- **AND** it MUST state that sealed content must not be exposed in chat.

#### Scenario: Handoff is responsibility-generic

- **WHEN** the assigned responsibility is PM, worker, research worker, reviewer, FlowGuard operator, or UI QA
- **THEN** the generated handoff MUST name that responsibility
- **AND** it MUST NOT use PM-only wording except when the responsibility is PM.

### Requirement: Role opens only its current packet

FlowPilot SHALL expose a formal current-run `open-packet` command that returns the sealed packet body only to the assigned active role after ACK.

#### Scenario: Assigned ACKed role opens packet

- **GIVEN** a packet is assigned to a live lease
- **AND** the lease responsibility matches the packet responsibility
- **AND** the lease has ACKed that packet
- **WHEN** the role runs `flowpilot_new.py open-packet --lease-id <lease> --packet-id <packet>`
- **THEN** the command MUST return the sealed packet body and safe packet metadata
- **AND** the runtime MUST record a sealed packet body open event.

#### Scenario: ACK response still does not carry the body

- **WHEN** the role records `flowpilot_new.py ack`
- **THEN** the ACK response MUST remain body-free
- **AND** the role MUST be able to use the separate `open-packet` command rather than waiting for body text in ACK output.

#### Scenario: Wrong or stale access is rejected

- **WHEN** a caller uses the wrong lease, inactive lease, unacknowledged lease, mismatched responsibility, accepted packet, or tampered body hash
- **THEN** `open-packet` MUST reject the request
- **AND** it MUST NOT return sealed body content.

### Requirement: Historical missing-handoff failure is a regression gate

FlowPilot SHALL treat the live failure where PM ACKed but stopped because runtime did not expose body text as a known control-plane regression.

#### Scenario: Narrow ad hoc Controller prompt is detected

- **WHEN** a role handoff says packet material may be read only if the ACK/runtime response exposes it
- **THEN** the regression gate MUST reject that handoff as unsafe
- **AND** it MUST require the generated handoff or formal `open-packet` command path.
