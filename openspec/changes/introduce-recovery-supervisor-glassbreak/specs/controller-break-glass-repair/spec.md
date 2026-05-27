## MODIFIED Requirements

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

#### Scenario: Severe control-plane failure enters Recovery Supervisor mode
- **WHEN** a break-glass incident cannot be closed by restoring a legal next
  action through the existing narrow Controller lane
- **THEN** FlowPilot MUST open a recovery transaction and suspend ordinary
  Controller progression while the temporary Recovery Supervisor identity
  performs the modeled recovery workflow

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

#### Scenario: Recovery transaction records same-family repair
- **WHEN** Recovery Supervisor mode opens
- **THEN** FlowPilot MUST record a recovery transaction that names linked
  blockers, defect families, normal lanes checked, FlowGuard obligations,
  same-family repair evidence, and Controller reinjection exit criteria

### Requirement: Break-glass cannot create normal route evidence or completion
FlowPilot SHALL prevent break-glass artifacts from counting as normal route
gate evidence, node completion, route mutation approval, PM approval, reviewer
approval, or terminal closure by themselves.

#### Scenario: Break-glass returns to normal flow
- **WHEN** a break-glass incident restores the control channel
- **THEN** Controller must return to normal Router/Controller flow, and route
  evidence must still pass through the existing authorized gates

#### Scenario: Recovery Supervisor must reinject Controller before resume
- **WHEN** a recovery transaction is ready to close
- **THEN** FlowPilot MUST record a fresh Controller reinjection proof and MUST
  NOT resume normal route work from the old Controller generation

#### Scenario: Final reporting exposes break-glass use
- **WHEN** terminal closure or user reporting is prepared after any break-glass
  incident in the current run
- **THEN** the final FlowPilot skill improvement report or closure summary names
  the incident, temporary compensation, validation, and permanent-fix
  disposition

## ADDED Requirements

### Requirement: Recovery Supervisor body access is scoped and audited
FlowPilot SHALL allow sealed-body access during break-glass only through a
Recovery Supervisor body-access grant that is linked to an open recovery
transaction, explicit body path, unavailable or contradictory role lanes, and a
post-recovery review obligation.

#### Scenario: Metadata is sufficient
- **WHEN** the control-plane failure can be diagnosed from Router status,
  Controller ledger, blocker metadata, schemas, contracts, manifests, hashes,
  or role liveness records
- **THEN** Recovery Supervisor MUST NOT open a body-access grant

#### Scenario: Body access is unavoidable
- **WHEN** PM, Reviewer, and Officer lanes are unavailable or contradictory
- **AND** the recovery transaction cannot classify the defect family from
  metadata alone
- **THEN** Recovery Supervisor may record one scoped body-access grant for the
  named body path and MUST mark the access for later authorized-role review

### Requirement: Historical control-plane blockers feed family repair without reactivation
FlowPilot SHALL classify historical control-plane blockers as current repair,
regression evidence, quarantine, or weak evidence before using them in a
Recovery Supervisor closure claim.

#### Scenario: Current blocker is open
- **WHEN** a blocker is current and open for the active recovery transaction
- **THEN** Recovery Supervisor MUST repair, supersede, or explicitly quarantine
  it before closing recovery

#### Scenario: Historical blocker is already resolved
- **WHEN** a historical blocker is not current for the active recovery
  transaction
- **THEN** FlowPilot MUST NOT reactivate it as live work by default and MUST use
  it only as regression or weak-evidence input for the defect-family gate
