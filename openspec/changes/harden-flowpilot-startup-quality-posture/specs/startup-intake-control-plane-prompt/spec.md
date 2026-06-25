## ADDED Requirements

### Requirement: Startup PM release preserves high-quality current-run posture
FlowPilot SHALL make the startup PM intake prompt and decision template carry a
normal high-quality current-run work posture into the first PM product and route
artifacts without adding new runtime fields.

#### Scenario: Startup release enters PM product work
- **WHEN** Runtime/Router mechanical startup passes and PM receives the sealed
  `user_intake` packet
- **THEN** the PM startup guidance MUST state that the next PM work is normal
  high-quality current-run project work
- **AND** the guidance MUST require concrete user outcome, highest reasonable
  product target, acceptance evidence, and proof-oriented planning to carry
  forward.

#### Scenario: Sparse startup request does not lower quality floor
- **WHEN** the user starts FlowPilot with a short request or sparse project
  description
- **THEN** PM startup guidance MUST NOT allow the sparse wording to reduce the
  later product architecture, route, node acceptance, or packet quality floor.

#### Scenario: Startup decision uses existing notes field
- **WHEN** PM records the startup intake decision
- **THEN** the reusable decision template MUST express the high-quality startup
  release posture inside existing decision fields
- **AND** the template MUST NOT introduce a new startup quality field.
