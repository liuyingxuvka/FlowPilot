# blocker-repair-policy Specification

## Purpose
TBD - created by archiving change unify-blocker-repair-policy. Update Purpose after archive.
## Requirements
### Requirement: Blocker policy rows drive first-handler routing
FlowPilot SHALL maintain a run-visible blocker repair policy table whose rows
map blocker families to a first handler, direct retry budget, escalation target,
PM recovery options, return policy, and hard-stop conditions.

#### Scenario: mechanical blocker goes to first handler
- **WHEN** Router materializes a mechanical control-plane blocker whose policy row has `first_handler=responsible_role`
- **THEN** the next Controller action delivers the sealed repair packet to that responsible role and includes the policy row id and retry budget.

#### Scenario: semantic blocker goes to PM
- **WHEN** Router materializes a blocker whose policy row has `first_handler=project_manager`
- **THEN** the next Controller action delivers the blocker to PM with the allowed PM recovery options and return policy.

### Requirement: Direct retries escalate to PM
FlowPilot SHALL track direct repair attempts for blockers that are not first
handled by PM and SHALL escalate to PM when the same blocker family exceeds its
direct retry budget.

#### Scenario: retry within budget
- **WHEN** a responsible role reissues a mechanical control-plane output and the same family has not exceeded its direct retry budget
- **THEN** Router may keep the first handler as the responsible role for the next repair attempt.

#### Scenario: retry budget exhausted
- **WHEN** the same blocker family is rejected more times than the policy row's direct retry budget allows
- **THEN** Router escalates the active blocker to PM instead of delivering another direct same-role reissue.

### Requirement: PM recovery decisions must name a return path
FlowPilot SHALL require PM repair decisions for escalated blockers to choose a
recovery option and name either a gate to re-run or a terminal stop.

#### Scenario: PM repairs without passing the blocked gate directly
- **WHEN** PM records a recovery decision for a blocker
- **THEN** the decision names a recovery option such as same-gate repair, rollback, supplemental node, repair node, route mutation, evidence quarantine, allowed waiver, protocol dead-end, or user stop, and does not mark the blocked gate passed by PM text alone.

#### Scenario: PM route mutation invalidates old evidence
- **WHEN** PM chooses route mutation or supplemental route work to recover from a blocker
- **THEN** affected prior evidence is marked stale, superseded, quarantined, or context-only before the replacement route gate can pass.

### Requirement: Hard-stop conditions cannot be waived silently
FlowPilot SHALL prevent PM waiver or bypass decisions from resolving policy rows
whose hard-stop conditions require user stop, protocol dead-end, or route
repair.

#### Scenario: protocol contamination hard stop
- **WHEN** a blocker policy row identifies controller body access, private role-to-role relay, or contaminated evidence as a hard-stop condition
- **THEN** PM cannot resolve the blocker with an ordinary waiver and must record protocol recovery, evidence quarantine plus rework, protocol dead-end, or user stop.

### Requirement: Self-interrogation blockers use PM recovery policy
FlowPilot SHALL classify missing, malformed, stale, dirty, or unresolved
self-interrogation records as PM-handled blocker policy rows.

#### Scenario: missing self-interrogation record
- **WHEN** a protected gate requires a clean self-interrogation record and the record is missing
- **THEN** Router materializes a blocker whose first handler is PM and whose PM recovery options include re-run interrogation, record disposition, convert findings to repair work, allowed waiver, route mutation, or user stop.

#### Scenario: dirty self-interrogation record blocks original gate
- **WHEN** a self-interrogation record contains unresolved hard/current findings
- **THEN** the original protected gate remains blocked until PM records an allowed recovery and Router rechecks the named return gate.

### Requirement: PM recovery option is not execution authority
FlowPilot SHALL keep `recovery_option` and `repair_action` as PM policy context
and human-readable explanation, while `repair_transaction.plan_kind` controls
Router execution.

#### Scenario: Same recovery option can choose different executable plans
- **WHEN** PM selects a policy recovery option such as same-gate repair
- **THEN** PM must also select an executable `repair_transaction.plan_kind`, and Router executes the plan kind rather than inferring behavior from the recovery option.

#### Scenario: Repair action text does not commit route progress
- **WHEN** PM writes human-readable repair action text
- **THEN** Router does not treat that text as a queued repair action, a passed gate, or an event producer unless the repair transaction contains a validated executable plan.

### Requirement: PM guidance maps failures to executable repair plans
FlowPilot SHALL instruct PM when to choose each executable repair plan kind for
control-blocker recovery.

#### Scenario: PM selects operation replay for repeatable operations
- **WHEN** the blocked work can be safely repeated from a recorded operation
- **THEN** PM uses `operation_replay` and names the recorded operation instead of requesting an open-ended redo.

#### Scenario: PM selects Controller repair packet for bounded AI repair
- **WHEN** the fix requires Controller to perform limited repair work within current authority
- **THEN** PM uses `controller_repair_work_packet` and supplies bounded reads, writes, forbidden actions, and success evidence.

#### Scenario: PM selects route mutation only for structural changes
- **WHEN** the repair requires adding, removing, or changing route nodes, gates, or acceptance boundaries
- **THEN** PM uses `route_mutation` rather than using ordinary replay or reissue.

### Requirement: Normal repair remains default before break-glass
FlowPilot SHALL keep PM/control-blocker/packet repair as the default recovery
path and SHALL allow Controller break-glass only after evidence shows the normal
control repair lane itself is unavailable, contradictory, looping, or unable to
produce a legal next action.

#### Scenario: Available PM repair blocks break-glass
- **WHEN** a control blocker can be delivered to the correct first handler or PM
  and a legal PM repair transaction can be recorded
- **THEN** Controller MUST NOT use break-glass and MUST follow the normal
  blocker repair policy

#### Scenario: Broken normal lane can trigger break-glass
- **WHEN** the control blocker or PM repair path is itself the failing mechanism,
  such as missing contract authority, impossible event authority, unavailable
  packet routing, or contradictory Router action state
- **THEN** Controller may open a break-glass incident instead of routing through
  the broken normal lane

#### Scenario: Break-glass does not resolve blocker by itself
- **WHEN** break-glass temporarily compensates for a FlowPilot control-plane
  defect
- **THEN** existing blockers, route gates, and repair transactions remain
  unresolved until the normal authorized flow can process or supersede them

### Requirement: PM same-gate repair selects an executable producer path
FlowPilot SHALL require PM same-gate repair decisions to select an executable repair transaction path that can produce the named return event.

#### Scenario: Same-gate repair text is not enough
- **WHEN** PM selects `same_gate_repair` and describes a worker reissue in `repair_action`
- **THEN** Router MUST treat that text as policy explanation only
- **AND** Router MUST require `repair_transaction.plan_kind` and plan-specific fields that create or reference the follow-up event producer.

#### Scenario: Incomplete PM repair decision stays on PM
- **WHEN** PM submits a same-gate repair decision whose executable transaction cannot produce the named `rerun_target`
- **THEN** Router MUST reject the PM repair decision mechanically
- **AND** Router MUST keep the active blocker targeted at PM for a corrected repair decision rather than moving the wait to workers.

#### Scenario: PM can choose terminal or follow-up blocker instead of rework
- **WHEN** PM determines that no safe producer can be created for the same gate
- **THEN** PM MAY choose an explicit terminal stop, protocol blocker, follow-up blocker, route mutation, or another supported executable plan
- **AND** Router MUST record that outcome through the existing blocker repair policy instead of creating an empty wait.

### Requirement: Runtime Write-Lock Failures Are Mechanical Before Semantic

FlowPilot SHALL classify runtime JSON write-lock failures as mechanical runtime
settlement issues before routing them to PM semantic repair.

#### Scenario: Controller action file has an active runtime write lock

- **WHEN** Router encounters `RouterLedgerWriteInProgress` while reading,
  writing, or summarizing a Controller action JSON file
- **THEN** FlowPilot first records runtime write-lock wait or takeover evidence
- **AND** it SHALL NOT create a PM semantic repair blocker until bounded runtime
  settlement has failed.

#### Scenario: Self-owned stale write lock can be mechanically recovered

- **WHEN** runtime settlement proves the write lock is stale and owned by the
  current daemon
- **AND** the target JSON and temp-artifact checks are safe
- **THEN** FlowPilot recovers it as mechanical runtime settlement
- **AND** it SHALL NOT route the condition to PM semantic repair.

#### Scenario: Runtime settlement fails after bounded recovery

- **WHEN** a runtime write-lock condition remains unresolved after bounded
  wait/takeover recovery
- **THEN** FlowPilot may materialize a control-plane blocker
- **AND** the blocker SHALL identify the failure as mechanical runtime ledger
  settlement rather than reviewer, PM, or business-task content failure.

### Requirement: PM escalation is reserved after relay mechanical repair boundary
FlowPilot SHALL escalate missing relay evidence to PM/control-blocker handling only when the missing evidence is not mechanically repairable by Controller or the Controller mechanical repair budget is exhausted.

#### Scenario: Invalid packet state escalates
- **WHEN** a relay receipt cannot be reconciled because the envelope is missing, corrupted, addressed to an invalid role, contaminated, or fails relay readiness checks
- **THEN** Router MAY materialize the appropriate control blocker or PM repair decision path instead of scheduling Controller mechanical relay repair

#### Scenario: Repeated Controller relay repair failure escalates
- **WHEN** Controller relay repair has been attempted up to the configured direct repair budget and the relay evidence is still missing or invalid
- **THEN** Router MUST escalate with a blocker payload that names the original action, packet ids, missing relay evidence, repair attempts used, and the exhausted budget
