# controller-break-glass-repair Specification

## Purpose
TBD - created by archiving change controller-break-glass-repair. Update Purpose after archive.
## Requirements
### Requirement: Controller break-glass is limited to FlowPilot control-plane failure
FlowPilot SHALL provide a Controller break-glass repair lane only for
development-mode recovery from FlowPilot control-plane failures where the
normal PM, control-blocker, packet, Router, or ledger path cannot produce a
legal next action.

#### Scenario: Control-plane deadlock can open break-glass
- **WHEN** Controller has current evidence that Router status, Controller action
  ledger, control-blocker routing, packet routing, or prompt/contract/event
  authority is contradictory, looping, or unable to produce a legal next action
- **THEN** Controller may open a break-glass incident after recording the
  failed normal-lane checks

#### Scenario: Ordinary project defect cannot open break-glass
- **WHEN** the problem is a target-project bug, worker defect, reviewer quality
  finding, test failure, or route/acceptance disagreement and normal PM repair
  remains available
- **THEN** Controller MUST NOT use break-glass and MUST continue through the
  normal FlowPilot repair path

### Requirement: Break-glass playbook is a manifest-listed Controller system card
FlowPilot SHALL ship a detailed Controller break-glass playbook at
`skills/flowpilot/assets/runtime_kit/cards/system/controller_break_glass_repair.md`
and register it in the runtime kit manifest for Controller.

#### Scenario: Controller can find the playbook
- **WHEN** Controller sees a repeated break-glass reminder during a run
- **THEN** the reminder names the playbook path and the manifest includes a
  `controller.break_glass_repair` card entry for that path

#### Scenario: Playbook defines allowed and forbidden actions
- **WHEN** Controller reads the playbook
- **THEN** it states allowed diagnostic/temporary compensation actions and
  forbids target-project work, sealed-body access, gate approval, route
  mutation, acceptance changes, publishing, deployment, and secret handling

### Requirement: Break-glass incidents and patches are run-scoped and auditable
FlowPilot SHALL record each break-glass use under
`.flowpilot/runs/<run-id>/controller_break_glass/` with an incident record and,
when temporary files or compensation are used, a patch record.

#### Scenario: Incident records trigger proof
- **WHEN** Controller opens break-glass
- **THEN** the incident record includes trigger evidence, normal repair lanes
  checked, suspected FlowPilot control-plane defect, allowed reads, allowed
  writes, forbidden actions, validation plan, and exit criteria

#### Scenario: Temporary patch records rollback
- **WHEN** Controller uses a temporary patch or compensation during break-glass
- **THEN** the patch record includes touched paths, reason, validation evidence,
  rollback notes, final disposition, and whether a permanent FlowPilot root fix
  remains needed

### Requirement: Break-glass cannot create normal route evidence or completion
FlowPilot SHALL prevent break-glass artifacts from counting as normal route
gate evidence, node completion, route mutation approval, PM approval, reviewer
approval, or terminal closure by themselves.

#### Scenario: Break-glass returns to normal flow
- **WHEN** a break-glass incident restores the control channel
- **THEN** Controller must return to normal Router/Controller flow, and route
  evidence must still pass through the existing authorized gates

#### Scenario: Final reporting exposes break-glass use
- **WHEN** terminal closure or user reporting is prepared after any break-glass
  incident in the current run
- **THEN** the final FlowPilot skill improvement report or closure summary names
  the incident, temporary compensation, validation, and permanent-fix
  disposition
