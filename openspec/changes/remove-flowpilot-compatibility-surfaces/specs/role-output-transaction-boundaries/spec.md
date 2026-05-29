## ADDED Requirements

### Requirement: Role Output Contracts Have No Legacy Aliases
FlowPilot role output contracts SHALL use current output type names and current
envelope fields only.

#### Scenario: Current role output is submitted
- **WHEN** a role submits a current role output envelope with a current output
  type
- **THEN** FlowPilot validates and routes it through the current contract
  registry

#### Scenario: Legacy output alias is submitted
- **WHEN** a role submits a legacy output alias or compatibility report shape
- **THEN** FlowPilot rejects the output as unsupported
- **AND** FlowPilot SHALL NOT map it to a current output type
