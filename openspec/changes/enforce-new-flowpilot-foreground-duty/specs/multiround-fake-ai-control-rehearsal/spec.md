## ADDED Requirements

### Requirement: Fake rehearsals cover foreground stop boundary
FlowPilot fake AI rehearsals SHALL cover the live foreground boundary where an
internal router driver can continue but the foreground Controller might
incorrectly stop.

#### Scenario: Scoped closure cannot end rehearsal
- **WHEN** a fake rehearsal accepts a scoped closure and the runtime has an
  open later packet
- **THEN** the rehearsal MUST assert that final-return preflight fails
- **AND** it MUST continue through the later packet or enter an explicit
  wait-patrol duty.

#### Scenario: Wait patrol is rehearsed as work
- **WHEN** a fake rehearsal reaches a live wait with no immediate result
- **THEN** the rehearsal MUST record a `wait_patrol` duty as active foreground
  work
- **AND** it MUST reject any completion claim based on passive waiting.

#### Scenario: Terminal rehearsal proves stop authority
- **WHEN** a fake rehearsal reaches terminal closure
- **THEN** it MUST assert `controller_stop_allowed=true`,
  `foreground_duty.action=terminal_return`, and final-return preflight allowed
- **AND** it MUST preserve the boundary that fake AI packages do not prove live
  AI semantic quality.
