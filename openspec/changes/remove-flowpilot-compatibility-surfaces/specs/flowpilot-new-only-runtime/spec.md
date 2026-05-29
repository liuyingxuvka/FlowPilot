## ADDED Requirements

### Requirement: Current Runtime Contracts Are The Only Accepted Contracts
FlowPilot SHALL accept only current startup, event, transaction, prompt, and
run-layout contracts as active runtime inputs.

#### Scenario: Current input is accepted
- **WHEN** a FlowPilot invocation uses the current `start` entrypoint, current
  startup intake envelope, current Router-provided event names, and current
  transaction families
- **THEN** FlowPilot processes the invocation through the current control plane

#### Scenario: Legacy input is rejected
- **WHEN** a FlowPilot invocation supplies an old command alias, old startup
  payload shape, legacy event alias, deprecated transaction kind, or old layout
  artifact as an active runtime input
- **THEN** FlowPilot rejects the input as unsupported or unknown
- **AND** FlowPilot SHALL NOT migrate, canonicalize, or silently adapt that
  input into current authority-bearing state

### Requirement: Compatibility Evidence Is Not Runtime Authority
FlowPilot SHALL treat any remaining historical compatibility material as
archived evidence only, not as a runtime contract, install requirement, or role
instruction.

#### Scenario: Historical evidence remains in the repository
- **WHEN** a historical legacy-to-current mapping or equivalence note remains
  in documentation
- **THEN** that material is clearly outside active runtime and install gates
- **AND** no active prompt, card, schema, or validator requires roles to follow
  it

### Requirement: Prior Authority Quarantine Remains Current Safety State
FlowPilot SHALL preserve quarantine protection for prior, superseded, stale, or
non-current authority while removing old compatibility naming and acceptance.

#### Scenario: Prior authority appears during a current run
- **WHEN** prior run state, prior agent identity, or stale evidence is observed
  during current FlowPilot processing
- **THEN** FlowPilot keeps it quarantined or superseded
- **AND** FlowPilot SHALL NOT treat it as a legacy compatibility input to
  import into current authority
