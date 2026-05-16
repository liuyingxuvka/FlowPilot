# flowpilot-invocation-intent-isolation Specification

## Purpose
TBD - created by archiving change separate-new-invocation-from-resume. Update Purpose after archive.
## Requirements
### Requirement: Fresh Startup Creates A New Run

FlowPilot SHALL treat a fresh formal startup request as a new invocation that
creates a new run, regardless of existing `.flowpilot/current.json` state or
other active runs.

#### Scenario: Current pointer names a running run

- **GIVEN** `.flowpilot/current.json` names run A with status `running`
- **WHEN** the user asks to start FlowPilot without explicit resume intent
- **THEN** FlowPilot creates run B as a new run
- **AND** FlowPilot does not attach to run A.

#### Scenario: Multiple runs are already active

- **GIVEN** run A and run B are both active FlowPilot runs
- **WHEN** the user asks to start FlowPilot without explicit resume intent
- **THEN** FlowPilot creates run C as a new independent run
- **AND** run A and run B remain independent parallel runs.

### Requirement: Fresh Startup Does Not Mutate Existing Runs

FlowPilot SHALL NOT stop, cancel, supersede, merge, import, deliver cards to,
or write Controller receipts for an existing run merely because fresh startup
discovers that run.

#### Scenario: Fresh startup discovers a parallel run

- **GIVEN** run A is a parallel active run
- **WHEN** fresh startup creates run B
- **THEN** startup writes authority-bearing state only under run B
- **AND** run A is not changed by run B startup.

### Requirement: Resume Requires Explicit Intent

FlowPilot SHALL use an existing run as the foreground target only when the user
explicitly asks to resume, continue, inspect, stop, or otherwise target an
existing FlowPilot run.

#### Scenario: User explicitly resumes a selected run

- **GIVEN** run A exists
- **WHEN** the user explicitly asks to resume run A
- **THEN** FlowPilot may attach to run A through the resume path
- **AND** FlowPilot does not create a fresh run merely to resume run A.

#### Scenario: Resume target is ambiguous

- **GIVEN** multiple existing runs could match a resume request
- **WHEN** the user asks to resume without a concrete target
- **THEN** FlowPilot blocks for target selection or presents available targets
- **AND** FlowPilot does not silently choose `.flowpilot/current.json`.

### Requirement: Current Pointer Is Not Startup Intent

FlowPilot SHALL treat `.flowpilot/current.json` as UI focus or a default target
only after the invocation intent is already known.

#### Scenario: Fresh startup reads project metadata

- **GIVEN** `.flowpilot/current.json` points to an existing run
- **WHEN** FlowPilot handles a fresh startup request
- **THEN** the current pointer is not used as evidence of resume intent
- **AND** the current pointer may be updated only after the new run is created.
