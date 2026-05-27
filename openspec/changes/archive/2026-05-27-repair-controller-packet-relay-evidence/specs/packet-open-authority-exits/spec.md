## ADDED Requirements

### Requirement: Path-only packet handoff never authorizes packet open
FlowPilot SHALL reject packet open attempts that rely only on Controller chat text, displayed paths, or a Controller receipt when the envelope lacks a valid Controller relay signature.

#### Scenario: Worker receives path without relay signature
- **WHEN** Worker opens an addressed packet through `flowpilot_runtime.py open-packet` and the envelope lacks `controller_relay`
- **THEN** the runtime MUST reject the open with a missing Controller relay error
- **AND** the runtime MUST NOT write a successful packet-open receipt

#### Scenario: Worker opens after runtime relay
- **WHEN** Controller has relayed the addressed packet through the runtime relay command and the packet body hash still matches the envelope
- **THEN** Worker `open-packet` MUST accept the packet and write the normal packet-open session receipt
