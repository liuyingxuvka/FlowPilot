## ADDED Requirements

### Requirement: Runtime role surfaces are host-neutral
FlowPilot SHALL describe live background role work as host-supported isolated addressable role surfaces, not as a required Codex-specific thread, subagent, or product feature.

#### Scenario: Host provides several role surfaces
- **WHEN** the runtime requests a live role binding and the user allowed background collaboration
- **THEN** the controller uses a current host-supported isolated addressable role surface for only the requested responsibility
- **AND** records the actual host surface and addressable role id in runtime evidence

#### Scenario: Host product differs
- **WHEN** FlowPilot runs in a non-Codex AI host with an equivalent isolated addressable role mechanism
- **THEN** the current startup and role-binding instructions remain valid without renaming fields or adding compatibility mappings

### Requirement: Startup authorization does not select implementation
FlowPilot SHALL keep startup background collaboration as one authorization choice and MUST NOT ask the user to choose between threads, subagents, workers, sessions, or other host-specific implementations.

#### Scenario: User allows background collaboration
- **WHEN** the user enables the startup background collaboration option
- **THEN** FlowPilot records `background_collaboration_authorized=true` for
  runtime-requested background role work
- **AND** defers the concrete implementation choice to the current host-supported role surface selection rule

#### Scenario: User declines background collaboration
- **WHEN** the user disables the startup background collaboration option
- **THEN** FlowPilot records that required background collaboration is disabled
- **AND** FlowPilot stops formal startup without single-agent continuity,
  compatibility translation, or live role-binding claims
