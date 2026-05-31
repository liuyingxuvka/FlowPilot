## MODIFIED Requirements

### Requirement: Historical friction surfaces are hard regression gates

FlowPilot SHALL maintain a known-friction regression gate for historical control-plane failures that have already occurred or materially recurred.

#### Scenario: Missing runtime-delivered role instructions row is registered

- **WHEN** the known-friction gate is evaluated
- **THEN** it MUST include the failure where a live role ACKed but stopped because the runtime did not expose role instructions or packet body text
- **AND** the expected safe behavior MUST require generated role handoff plus formal `open-packet` evidence.
