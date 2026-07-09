## ADDED Requirements

### Requirement: Fake-AI coverage includes control-plane ledger hygiene axes
FlowPilot SHALL include finite fake-AI/D-card Cartesian coverage for the
observed control-plane ledger hygiene miss family.

#### Scenario: Cartesian matrix is generated
- **WHEN** the synthetic agent coverage matrix is generated for this change
- **THEN** it MUST include axes for result status, accepted pointer state,
  repair identity state, packet family, blocker state, break-glass state,
  reviewer authorization state, and closure phase
- **AND** every generated cell MUST declare the expected runtime action,
  including allow, reject, reissue, record blocker, block closure, or block
  terminal return

#### Scenario: Tampered AI package is outside normal generation path
- **WHEN** a fake-AI package represents a state that runtime should not
  normally generate, such as a missing repair id on a same-family derived
  packet
- **THEN** the matrix MUST still include the cell as a tampered/hostile input
  case
- **AND** runtime MUST reject or block it through the current contract instead
  of accepting it through fallback
