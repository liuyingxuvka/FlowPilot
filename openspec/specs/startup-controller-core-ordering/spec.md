# startup-controller-core-ordering Specification

## Purpose
TBD - created by archiving change load-controller-core-before-startup-obligations. Update Purpose after archive.
## Requirements
### Requirement: Controller Core Precedes Controller-Ledger Startup Obligations
FlowPilot startup SHALL expose `load_controller_core` as the first
Controller-ledger startup row after native startup intake has been confirmed
and deterministic user-intake bootstrap artifacts have been materialized.
Startup obligations that require Controller ledger handling, including
`emit_startup_banner`, `create_heartbeat_automation`, and `start_role_slots`,
MUST NOT be exposed until the `load_controller_core` postcondition has been
reconciled by Router.

#### Scenario: Controller core is loaded before startup obligations
- **WHEN** a formal startup invocation confirms the native startup intake UI
- **THEN** Router exposes `load_controller_core` before exposing
  `emit_startup_banner`, `create_heartbeat_automation`, or `start_role_slots`
  in the Controller action ledger

#### Scenario: Reconciled Controller core unlocks startup obligations
- **WHEN** Controller records a done receipt for `load_controller_core` and
  Router reconciles `controller_core_loaded`
- **THEN** Router may expose the startup banner, heartbeat, and role-slot rows
  according to the selected startup answers

### Requirement: Continuation Binding Gates Work Beyond Startup
When scheduled continuation is selected, FlowPilot SHALL require the current
run's heartbeat host binding before startup review, PM startup activation, role
work, or route work can proceed. Manual-resume startup MUST NOT create a
heartbeat automation.

#### Scenario: Scheduled continuation waits before route work
- **WHEN** scheduled continuation is selected and Controller core has been
  loaded
- **THEN** Router requires `create_heartbeat_automation` to be completed and
  reconciled before startup review, PM activation, or route work proceeds

#### Scenario: Manual resume skips heartbeat automation
- **WHEN** startup answers select manual resume instead of scheduled
  continuation
- **THEN** Router does not expose `create_heartbeat_automation` and may
  continue startup with manual-resume lifecycle evidence

### Requirement: Startup Banner Remains User-Visible Controller Work
The startup banner SHALL remain user-visible and require Controller receipt
evidence, but it MUST be Controller-ledger work after Controller core is loaded,
not a pre-Controller-core action.

#### Scenario: Startup banner records user-dialog confirmation after core
- **WHEN** Controller core has been loaded and Router exposes
  `emit_startup_banner`
- **THEN** Controller displays the exact startup banner text to the user dialog
  and records the required display confirmation receipt
