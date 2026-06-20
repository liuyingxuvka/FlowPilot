## ADDED Requirements

### Requirement: Registered formal artifacts receive executable feedback
FlowPilot SHALL produce executable current-contract feedback for every
registered formal artifact failure.

#### Scenario: Registered file is missing
- **WHEN** runtime requires a registered formal artifact and the file is missing
- **THEN** runtime MUST reject the result and name the artifact id plus current
  packet-owned target root or path.

#### Scenario: Registered file has invalid content
- **WHEN** runtime requires a registered formal artifact and the file is not
  readable in its registered format
- **THEN** runtime MUST reject the result and name the artifact id and expected
  format.

#### Scenario: Registered file misses required internal field
- **WHEN** runtime requires a registered formal artifact and a registered
  internal field is missing or invalid
- **THEN** runtime MUST reject the result and name the artifact field path plus
  allowed value or type.

#### Scenario: Result body cannot substitute for registered file
- **WHEN** runtime requires both a result body and a registered formal artifact
- **AND** the role submits only a valid result body
- **THEN** runtime MUST reject the result and state that body-only repair is
  insufficient.
