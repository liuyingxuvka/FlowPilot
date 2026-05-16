## ADDED Requirements

### Requirement: Monitor exposes current work owner
FlowPilot SHALL expose a single `current_work` monitor projection that identifies the actor currently responsible for advancing the run and the task that actor is expected to perform.

#### Scenario: Pending action owns current work
- **WHEN** the run has a pending action with a concrete actor, target role, or wait target
- **THEN** daemon status and current status summary include `current_work` naming that owner and a concise task label derived from the action

#### Scenario: Packet holder owns current work after pending action is cleared
- **WHEN** `run_state.pending_action` is null and the packet ledger shows an active packet held by a role
- **THEN** daemon status and current status summary include `current_work.owner_kind` as `role`, `current_work.owner_key` as the packet holder, and `current_work.source` as `packet_ledger`

#### Scenario: Passive reconciliation owns current work after pending action is cleared
- **WHEN** `run_state.pending_action` is null and an unresolved passive wait or scheduler wait still owns reconciliation work
- **THEN** daemon status and current status summary include `current_work` naming the responsible internal owner and a task label that describes the reconciliation work

#### Scenario: Router or Controller owns internal work
- **WHEN** no role packet holder is active and Router or Controller internal work is the next responsibility
- **THEN** `current_work` identifies `router` or `controller` as the owner instead of leaving the monitor's primary owner blank

### Requirement: Current work owner does not replace wait diagnostics
FlowPilot SHALL preserve existing `current_wait` and `waiting_for_role` fields for compatibility while using `current_work` as the primary monitor responsibility projection.

#### Scenario: Legacy wait field remains null but current work is known
- **WHEN** the legacy wait projection has no `waiting_for_role` and another runtime source identifies the active responsibility owner
- **THEN** `waiting_for_role` remains compatible with the legacy projection and `current_work` names the active responsibility owner

#### Scenario: Ownership does not complete work
- **WHEN** `current_work` names a role, Router, Controller, or user
- **THEN** FlowPilot does not treat that ownership projection as ACK evidence, role output, PM approval, route advancement, or wait satisfaction

### Requirement: Current work owner is stable enough for Controller checks
FlowPilot SHALL include enough machine-readable metadata in `current_work` for Controller to decide whether to watch, remind, escalate, or continue internal processing.

#### Scenario: Role owner supports liveness checks
- **WHEN** `current_work.owner_kind` is `role`
- **THEN** `current_work` includes the owner key, source, source path when available, and any related packet id or wait action id needed to correlate liveness/reminder checks

#### Scenario: Internal owner avoids external role reminder
- **WHEN** `current_work.owner_kind` is `router` or `controller`
- **THEN** Controller treats the status as internal progress or internal reconciliation rather than an external role reminder target
