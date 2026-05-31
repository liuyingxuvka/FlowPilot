## MODIFIED Requirements

### Requirement: FlowGuard packets use the single FlowGuard operator responsibility

FlowPilot SHALL issue FlowGuard-related packet work only to the explicit current `flowguard_operator` responsibility and SHALL NOT use old Process/FlowGuard operator packet owners.

#### Scenario: Process-model packet
- **WHEN** a packet requires process, route, validation-freshness, or development workflow FlowGuard work
- **THEN** the packet owner is `flowguard_operator`
- **AND** tests and evidence policies use that exact current responsibility.

#### Scenario: Product-model packet
- **WHEN** a packet requires product-function, product behavior, or modelability FlowGuard work
- **THEN** the packet owner is `flowguard_operator`
- **AND** tests and evidence policies use that exact current responsibility.
