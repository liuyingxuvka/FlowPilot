## ADDED Requirements

### Requirement: Fresh Invocation Has No Compatibility Alias
FlowPilot fresh invocation SHALL be entered through the current `start` command
only.

#### Scenario: Start creates a fresh run
- **WHEN** the user requests a fresh FlowPilot invocation with the current
  `start` command
- **THEN** FlowPilot creates a new run according to the current invocation
  isolation contract

#### Scenario: Old new-invocation alias is supplied
- **WHEN** the user or automation supplies `next --new-invocation` or
  `run-until-wait --new-invocation`
- **THEN** FlowPilot rejects the command as unsupported
- **AND** FlowPilot SHALL NOT create, resume, or mutate a run through that alias
