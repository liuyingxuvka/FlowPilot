# startup-controller-core-ordering Specification

## Purpose
Define Controller-core ordering for the current startup path after removal of
historical scheduled-continuation and fixed role-slot startup actions.

## Requirements
### Requirement: Controller core follows current startup intake
FlowPilot startup SHALL expose `load_controller_core` only after native startup
intake has been confirmed, current startup fields have been validated, and
deterministic user-intake bootstrap artifacts have been materialized.

#### Scenario: Controller core is loaded from current startup state
- **WHEN** a formal startup invocation confirms the native startup intake UI
- **AND** the native startup UI records the background-collaboration switch as
  `background_collaboration_authorized=true`
- **THEN** Router exposes `load_controller_core` as Controller-ledger work
- **AND** Router MUST NOT expose historical continuation automation or fixed
  role-slot startup actions in the Controller action ledger.

#### Scenario: Reconciled Controller core unlocks current startup review
- **WHEN** Controller records a done receipt for `load_controller_core`
- **AND** Router reconciles `controller_core_loaded`
- **THEN** Router may expose the startup banner, startup fact review, and PM
  startup activation according to current startup evidence only.

### Requirement: Background collaboration gates work beyond startup
FlowPilot SHALL require current background or parallel role capability evidence
before startup review, PM startup activation, role work, or route work can
proceed beyond the startup gates. A user-disabled background-collaboration
startup option SHALL block startup rather than asking Router to try a
foreground-only route.

#### Scenario: Current background capability is available
- **WHEN** Controller core has been loaded
- **AND** current background or parallel role capability can be evidenced
- **THEN** Router proceeds through current startup fact review and PM startup
  activation.

#### Scenario: Current background capability is unavailable
- **WHEN** Controller core has been loaded
- **AND** current background or parallel role capability cannot be evidenced
- **THEN** Router records a structured stop or control blocker
- **AND** Router MUST NOT continue through unsupported non-background
  continuity, historical continuation automation, fixed role-slot bootstrap, or
  historical role evidence.

#### Scenario: User disables background collaboration in startup UI
- **WHEN** the native startup UI records
  `background_collaboration_authorized=false`
- **THEN** Router blocks startup with `background_collaboration_required`
- **AND** Router MUST NOT expose `load_controller_core`.

### Requirement: Startup banner remains user-visible Controller work
The startup banner SHALL remain user-visible and require Controller receipt
evidence, but it MUST be Controller-ledger work after Controller core is loaded.

#### Scenario: Startup banner records user-dialog confirmation after core
- **WHEN** Controller core has been loaded and Router exposes
  `emit_startup_banner`
- **THEN** Controller displays the exact startup banner text to the user dialog
  and records the required display confirmation receipt.
