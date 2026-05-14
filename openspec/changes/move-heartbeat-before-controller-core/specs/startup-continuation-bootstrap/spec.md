## ADDED Requirements

### Requirement: Startup heartbeat precedes Controller core
When the startup intake selects scheduled continuation, FlowPilot SHALL create
and record the run-bound heartbeat host automation before `load_controller_core`
is applied.

#### Scenario: Scheduled continuation startup
- **WHEN** startup answers request scheduled continuation and role slots have been started
- **THEN** the next host boundary is `create_heartbeat_automation` with bootloader/startup ownership before `load_controller_core`

#### Scenario: Controller core cannot precede requested heartbeat
- **WHEN** scheduled continuation is requested and no valid heartbeat host receipt has been recorded
- **THEN** the router MUST NOT expose or apply `load_controller_core`

### Requirement: Manual resume skips heartbeat bootstrap
When the startup intake selects manual continuation, FlowPilot SHALL skip the
startup heartbeat host action and may continue to Controller core handoff.

#### Scenario: Manual continuation startup
- **WHEN** startup answers select manual resume rather than scheduled continuation
- **THEN** the router emits `load_controller_core` without requiring `create_heartbeat_automation`

### Requirement: Controller core consumes established continuation
After `load_controller_core`, Controller SHALL treat startup continuation as an
already-established authority or manual-resume mode, not as first-time startup
heartbeat setup.

#### Scenario: Controller startup fact review
- **WHEN** Controller enters the startup fact-review sequence
- **THEN** the run has either a valid heartbeat binding or a recorded manual-resume continuation mode
