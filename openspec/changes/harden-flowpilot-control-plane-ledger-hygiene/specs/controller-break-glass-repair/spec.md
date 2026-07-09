## ADDED Requirements

### Requirement: Open break-glass artifacts block clean completion
FlowPilot SHALL treat open break-glass incidents and pending temporary patches
as terminal ledger hygiene blockers until their existing disposition fields are
closed, quarantined, or otherwise resolved by the break-glass contract.

#### Scenario: Incident remains open at closure
- **WHEN** final closure is attempted while a current-run
  `controller_break_glass/incidents/*.json` record has `status=open`
- **THEN** runtime MUST block clean closure and terminal return
- **AND** runtime MUST report the incident id as a closure blocker

#### Scenario: Temporary patch still needs permanent fix
- **WHEN** final closure is attempted while a current-run break-glass patch has
  `temporary=true`, `permanent_fix_needed=true`, and validation is pending or
  missing
- **THEN** runtime MUST block clean closure and terminal return
- **AND** runtime MUST NOT treat continued main-flow execution as incident
  closure
