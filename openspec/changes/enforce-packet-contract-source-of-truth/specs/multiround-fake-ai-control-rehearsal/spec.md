## ADDED Requirements

### Requirement: Multi-round fake AI rehearsals preserve packet-contract parity
FlowPilot multi-round fake AI rehearsals SHALL classify each fake result body
against the current packet-result contract before using it as successful
control-plane evidence.

#### Scenario: Successful fake result uses declared fields only
- **WHEN** a multi-round fake AI row submits a successful result body
- **THEN** every top-level field in that body MUST be declared by the packet
  contract for that packet family

#### Scenario: Bad fake result proves rejection not success
- **WHEN** a multi-round fake AI row submits old fields, wrappers, missing
  fields, fallback evidence, or hidden overproduced fields
- **THEN** the row MUST assert mechanical rejection and legal recovery through
  the current packet path
