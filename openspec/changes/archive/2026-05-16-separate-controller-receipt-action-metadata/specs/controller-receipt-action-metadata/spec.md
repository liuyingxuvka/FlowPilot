## ADDED Requirements

### Requirement: Controller ledger rows expose receipt completion
FlowPilot SHALL project Router actions into Controller action ledger records with a Controller-visible completion contract that uses `controller-receipt`, not the normal Router `apply` path.

#### Scenario: Daemon row action metadata is receipt-oriented
- **WHEN** Router writes a daemon-scheduled Controller action record under `runtime/controller_actions/*.json`
- **THEN** the persisted action metadata SHALL include `controller_completion_command: "controller-receipt"`
- **AND** the persisted action metadata SHALL include `controller_completion_mode: "controller_action_ledger_receipt"`
- **AND** the persisted action metadata SHALL NOT expose `apply_required: true` as the Controller row completion path

#### Scenario: Next-step contract is receipt-oriented for Controller rows
- **WHEN** a Controller action record includes a `next_step_contract`
- **THEN** that contract SHALL identify the Controller row completion path as `controller-receipt`
- **AND** `next_step_contract.apply_required` SHALL be false for the Controller row projection

### Requirement: Original Router apply intent remains explicit
FlowPilot SHALL preserve original Router pending-action apply intent under names that cannot be mistaken for the Controller row completion path.

#### Scenario: Original apply requirement is retained for diagnostics
- **WHEN** a Router action that originally required apply is projected into a Controller action record
- **THEN** the Controller action metadata SHALL retain that original fact as `router_pending_apply_required: true`
- **AND** the next-step contract SHALL retain that original fact as `router_pending_apply_required: true`

#### Scenario: Direct pending action still uses apply
- **WHEN** Router returns a direct pending action that is not being consumed as a Controller action ledger row
- **THEN** the action MAY continue to expose `apply_required: true`
- **AND** the action MAY continue to instruct the host to apply the pending action with the required payload

### Requirement: Controller-visible wording matches receipt completion
FlowPilot SHALL ensure Controller-visible instructions for ledger rows use receipt language instead of apply language.

#### Scenario: Display confirmation rows request receipt payloads
- **WHEN** a Controller ledger row requires user-dialog display confirmation
- **THEN** its Controller-visible rule SHALL tell Controller to display the text and write a Controller receipt with display confirmation
- **AND** it SHALL NOT tell Controller to apply the action

#### Scenario: Host setup rows request receipt payloads
- **WHEN** a Controller ledger row starts roles, creates a heartbeat automation, writes a terminal summary, or updates a display surface
- **THEN** its Controller-visible wording SHALL tell Controller to write a Controller receipt with the required evidence payload
- **AND** it SHALL NOT use "before applying" or "apply only" as the ledger-row completion instruction
