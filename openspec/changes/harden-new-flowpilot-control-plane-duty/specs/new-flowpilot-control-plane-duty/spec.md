## ADDED Requirements

### Requirement: New runtime classifies control-plane actions before foreground exposure
The new FlowPilot runtime SHALL classify each current `RuntimeAction` before foreground Controller handling so internal mechanical work, role dispatch, role wait, recovery, user-required, and terminal states are not confused.

#### Scenario: Internal action is not reported as stuck
- **WHEN** the next action is a safe router-internal mechanical action such as creating the next node packet
- **THEN** the runtime MUST classify it as router-internal work
- **AND** the lifecycle guard MUST NOT classify the state as `control_plane_stuck` merely because the same internal action was observed.

#### Scenario: Role wait remains a formal wait duty
- **WHEN** a packet is ACKed and waiting for a result
- **THEN** the runtime MUST classify the state as role wait
- **AND** foreground duty MUST expose a timed `wait_patrol` rather than allowing the Controller to stop.

### Requirement: New runtime folds safe internal mechanical work to a wait boundary
The new FlowPilot runtime SHALL provide a bounded process loop that applies only allowlisted router-internal mechanical actions and stops before role dispatch, role wait, user input, recovery requiring external evidence, or terminal return.

#### Scenario: Node task packet is created before foreground dispatch
- **WHEN** recursive route execution has an incomplete frontier node and no open node task packet
- **THEN** `run-until-wait` MUST create the node task packet
- **AND** the returned next action MUST be role dispatch or role wait for that packet, not the internal packet-creation action.

#### Scenario: Fold loop is bounded
- **WHEN** internal mechanical actions keep producing new internal mechanical actions
- **THEN** the loop MUST stop with an explicit control-plane error after the configured maximum steps
- **AND** it MUST report the folded actions already applied.

### Requirement: PM repair lifecycle decisions are structured
PM repair decisions SHALL be accepted only from structured decision fields, not from incidental free-text rationale words.

#### Scenario: Structured same-node repair survives adversarial rationale
- **WHEN** a PM repair result body contains `decision=same_node_repair` and rationale text containing words such as `blocked`, `blocker`, or `stop for user`
- **THEN** the runtime MUST record the decision as `same_node_repair`
- **AND** it MUST NOT map those rationale words to `stop_for_user`.

#### Scenario: Missing structured decision is blocked
- **WHEN** a PM repair result body contains rationale text but no structured decision field
- **THEN** the runtime MUST reject or block the PM repair result as a payload contract error
- **AND** it MUST NOT guess a lifecycle decision from words such as `block`, `blocked`, `repair`, or `stop`.

### Requirement: Blocker lifecycle has a single source of truth
The new FlowPilot runtime SHALL keep semantic blocker lifecycle state consistent with the PM repair decision applied to it.

#### Scenario: Stop for user prevents repair continuation
- **WHEN** PM selects `stop_for_user` for a blocker
- **THEN** the blocker MUST be stopped
- **AND** the runtime MUST NOT issue new repair packets for that same blocker until a user resume or explicit repair authority changes the lifecycle.

#### Scenario: Same-node repair is not stopped
- **WHEN** PM selects `same_node_repair`
- **THEN** the blocker MUST remain repairing or awaiting recheck
- **AND** the target packet MUST NOT be marked `pm_stopped`.

### Requirement: Status is read-only for guard history
The new FlowPilot `status` command SHALL render current projection data without mutating lifecycle guard history, foreground duty history, event lists, repeated-action counts, or blocker state.

#### Scenario: Repeated status calls do not create stuck evidence
- **WHEN** `status` is called repeatedly without any stateful command or role output in between
- **THEN** lifecycle guard history length MUST remain unchanged
- **AND** repeated-action counts MUST NOT increase from the status calls.

#### Scenario: Patrol remains explicit refresh
- **WHEN** `patrol` is called
- **THEN** the runtime MAY refresh lifecycle guard and foreground duty state
- **AND** any wait/stuck/recovery state change MUST be attributed to the patrol trigger rather than status projection.
