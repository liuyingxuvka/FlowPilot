## ADDED Requirements

### Requirement: ACK And Output Singleton Evidence Stay Separate
FlowPilot SHALL include ACK wait settlement and durable output completion as separate singleton evidence surfaces.

#### Scenario: ACK replay cannot duplicate output completion
- **WHEN** the same valid ACK is observed more than once for a packet or card wait
- **THEN** FlowPilot treats the ACK as idempotent receipt settlement and does not create or close a second semantic output authority

#### Scenario: ACK-only completion is a singleton hazard
- **WHEN** a required role output is completed only because its ACK wait settled
- **THEN** the singleton checker reports an ACK-only closure hazard
